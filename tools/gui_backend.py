"""JSON-lines backend for the native macOS patcher. Never reads account profiles."""
import argparse
import datetime
import errno
import fcntl
import hashlib
import json
import mmap
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'tools/sumerki'))
from build_patch import build, read_header
from prepare_copy import dictionary_digest, SENTINEL

SUPPORTED = ('26.1111.21308', '27194')
DEFAULT_STATE = Path.home()/'Library/Application Support/ChatGPT Themes'

class PatcherError(Exception):
    pass

def emit(event, **data):
    print(json.dumps({'event':event, **data}, ensure_ascii=False), flush=True)

def progress(message, percent):
    emit('progress', message=message, percent=percent)

def run(*args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise PatcherError((result.stderr or result.stdout or 'Команда завершилась с ошибкой').strip()[-2500:])
    return result

def app_info(app):
    if not app.is_dir() or app.suffix != '.app':
        raise PatcherError('Выберите установленное приложение ChatGPT.app.')
    try:
        info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
    except (OSError, ValueError) as e:
        raise PatcherError('Не удалось прочитать сведения о приложении.') from e
    if info.get('CFBundleIdentifier') != 'com.openai.codex':
        raise PatcherError('Это приложение не является поддерживаемым клиентом ChatGPT.')
    return info

def record_path(state, app):
    return state/hashlib.sha256(str(app).encode()).hexdigest()[:16]/'manifest.json'

def read_record(path):
    if not path.exists():
        return None
    try:
        value=json.loads(path.read_text())
        if value.get('schema') != 1:
            raise ValueError('schema')
        return value
    except (ValueError,OSError) as e:
        raise PatcherError('Повреждена запись резервной копии. Автоматическая замена остановлена.') from e

def inspect(app, state):
    info=app_info(app)
    record=read_record(record_path(state,app))
    return {'app':str(app),'version':info.get('CFBundleShortVersionString','?'),
            'build':info.get('CFBundleVersion','?'),
            'supported':(info.get('CFBundleShortVersionString'),info.get('CFBundleVersion'))==SUPPORTED,
            'managed':record is not None,
            'canRestore':bool(record and Path(record['baseline']).is_dir()),
            'backup':record['baseline'] if record else None}

def assert_closed(app, info):
    executable=app/'Contents/MacOS'/info.get('CFBundleExecutable','ChatGPT')
    result=subprocess.run(['/usr/sbin/lsof','-t',str(executable)],capture_output=True,text=True)
    if result.returncode not in (0,1):
        raise PatcherError('Не удалось проверить, закрыт ли ChatGPT. Закройте приложение и повторите.')
    if result.stdout.strip():
        raise PatcherError('ChatGPT ещё работает. Полностью выйдите через Cmd+Q и нажмите кнопку снова.')

def verify(app):
    run('/usr/bin/codesign','--verify','--deep','--strict',str(app))
    info=app_info(app)
    with (app/'Contents/Resources/app.asar').open('rb') as f:
        _,_,raw=read_header(f)
    if hashlib.sha256(raw).hexdigest()!=info['ElectronAsarIntegrity']['Resources/app.asar']['hash']:
        raise PatcherError('Контрольная сумма архива не совпадает. Замена остановлена.')

def clone(source, target):
    if target.exists():
        raise PatcherError('Путь подготовки уже занят. Повторная запись остановлена.')
    result=subprocess.run(['/bin/cp','-cR',str(source),str(target)],capture_output=True,text=True)
    if result.returncode:
        # Partial output belongs to this operation, never to the user-selected source.
        if target.exists():
            shutil.rmtree(target)
        run('/usr/bin/ditto',str(source),str(target))

def patch_framework(app, old_info, new_info):
    framework=(app/'Contents/Frameworks/Codex Framework.framework/Versions/Current/Codex Framework').resolve()
    if not framework.is_relative_to(app.resolve()):
        raise PatcherError('Неожиданный путь фреймворка.')
    expected=dictionary_digest(old_info)
    replacement=dictionary_digest(new_info)
    with framework.open('r+b') as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
            offsets=[];start=0
            while True:
                i=data.find(SENTINEL,start)
                if i<0:break
                n=i+len(SENTINEL)
                if data[n:n+2]==b'\x01\x01' and data[n+2:n+34]==expected:
                    offsets.append(n+2)
                start=i+len(SENTINEL)
        if len(offsets)!=1:
            raise PatcherError('Структура защиты приложения изменилась. Эта версия пока не поддерживается.')
        f.seek(offsets[0]);f.write(replacement);f.flush();os.fsync(f.fileno())

def atomic_swap(app, stage, park):
    os.rename(app,park)
    try:
        os.rename(stage,app)
    except BaseException:
        os.rename(park,app)
        raise

def write_record(path, record):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(record,f,ensure_ascii=False,indent=2)
        f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def operate(action, app, state):
    info=app_info(app)
    state.mkdir(parents=True,exist_ok=True)
    with (state/'patcher.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise PatcherError('Другая операция патчера уже выполняется.')
        assert_closed(app,info)
        record_file=record_path(state,app)
        record=read_record(record_file)
        if action=='apply' and (info.get('CFBundleShortVersionString'),info.get('CFBundleVersion'))!=SUPPORTED:
            raise PatcherError('Эта версия ChatGPT пока не поддерживается. Приложение не изменено.')
        if not os.access(app.parent,os.W_OK):
            raise PatcherError('Нет права записи в папку приложения. Переместите ChatGPT в доступную вам папку Applications; патчер не запрашивает пароль администратора.')
        progress('Проверяю приложение',5)
        verify(app)
        if action=='restore':
            if not record:raise PatcherError('Для этого приложения ещё нет резервной копии патчера.')
            source=Path(record['baseline']).resolve()
            if not source.is_relative_to(state.resolve()):raise PatcherError('Неожиданный путь резервной копии.')
            verify(source)
        else:
            source=app
            required=(app/'Contents/Resources/app.asar').stat().st_size+300_000_000
            if shutil.disk_usage(app.parent).free<required:
                raise PatcherError('Недостаточно свободного места для безопасной подготовки копии.')
        job=record_file.parent/'backups'/uuid.uuid4().hex
        job.mkdir(parents=True)
        backup=job/'ChatGPT.app'
        progress('Сохраняю рабочую версию',15)
        clone(app,backup)
        verify(backup)
        stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        if record is None:
            record={'schema':1,'target':str(app),'baseline':str(backup),'createdAt':stamp,'history':[]}
        # Persist recovery information before modifying the installed bundle.
        write_record(record_file,record)
        token=uuid.uuid4().hex
        stage=app.parent/('.'+app.stem+'.themes-stage-'+token+'.app')
        park=app.parent/('.'+app.stem+'.themes-previous-'+token+'.app')
        installed=False
        try:
            progress('Подготавливаю новую копию',25)
            clone(source,stage)
            if action=='apply':
                with tempfile.TemporaryDirectory(prefix='build-',dir=state) as work:
                    output=Path(work)
                    progress('Добавляю меню и менеджер тем',40)
                    build(app,ROOT/'tools/sumerki/theme.css',output,
                          manager_path=ROOT/'manager/manager.js',allow_repatch=True)
                    archive=stage/'Contents/Resources/app.asar'
                    try:os.replace(output/'app.asar',archive)
                    except OSError as e:
                        if e.errno!=errno.EXDEV:raise
                        shutil.copyfile(output/'app.asar',archive)
                    patched=plistlib.loads((output/'Info.plist').read_bytes())
                    (stage/'Contents/Info.plist').write_bytes(plistlib.dumps(patched,fmt=plistlib.FMT_XML,sort_keys=False))
                    patch_framework(stage,info,patched)
                    entitlements=output/'entitlements.plist'
                    entitlements.write_bytes(plistlib.dumps({
                        'com.apple.security.cs.allow-jit':True,
                        'com.apple.security.cs.allow-unsigned-executable-memory':True,
                        'com.apple.security.cs.disable-library-validation':True}))
                    progress('Подписываю подготовленную копию',65)
                    run('/usr/bin/codesign','--force','--deep','--sign','-','--options','runtime',
                        '--entitlements',str(entitlements),str(stage))
            progress('Проверяю результат',80)
            verify(stage)
            assert_closed(app,info)
            progress('Заменяю приложение',90)
            atomic_swap(app,stage,park)
            installed=True
            record['history'].append({'action':action,'at':stamp,'previous':str(backup),'parked':str(park)})
            record['lastAction']=action
            write_record(record_file,record)
            # Keep the displaced bundle intact as additional crash-recovery material.
            os.rename(park,job/'displaced.app')
            progress('Готово',100)
            return {'app':str(app),'backup':str(record['baseline']),'action':action}
        finally:
            if not installed and stage.exists():shutil.rmtree(stage)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['inspect','apply','restore'])
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--state',type=Path,default=DEFAULT_STATE)
    args=parser.parse_args()
    try:
        app=args.app.resolve();state=args.state.resolve()
        if state.is_relative_to(app):raise PatcherError('Резервные копии должны храниться вне приложения.')
        result=inspect(app,state) if args.action=='inspect' else operate(args.action,app,state)
        emit('result',**result)
    except Exception as e:
        emit('error',message=str(e))
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
