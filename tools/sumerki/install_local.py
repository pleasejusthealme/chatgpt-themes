"""Install or restore the tested local build. Run manually after quitting ChatGPT."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import os

ROOT = Path(__file__).resolve().parent.parent.parent
APP = Path('/Applications/ChatGPT.app')
TEST = ROOT / 'work/ChatGPT Theme Test.app'
BACKUP = ROOT / 'work/original-ChatGPT.app'
STAGE = Path('/Applications/.ChatGPT-Sumerki-stage.app')
PARK = Path('/Applications/.ChatGPT-Sumerki-previous.app')

def run(*args):
    subprocess.run(args, check=True)

def version(p):
    return plistlib.loads((p/'Contents/Info.plist').read_bytes())['CFBundleVersion']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install','restore'])
    args=parser.parse_args()
    probe=subprocess.run(['/usr/sbin/lsof','-t',str(APP/'Contents/MacOS/ChatGPT')],capture_output=True,text=True)
    if probe.stdout.strip():
        raise SystemExit('Сначала полностью выйдите из основного ChatGPT через Cmd+Q, затем повторите команду.')
    if STAGE.exists() or PARK.exists():
        raise SystemExit('Обнаружены файлы предыдущей установки. Остановлено для проверки и сохранения резервной копии.')
    source=TEST if args.action=='install' else BACKUP
    if not source.exists():raise SystemExit('Не найдена копия: '+str(source))
    if args.action=='install':
        if version(APP)!=version(TEST):raise SystemExit('ChatGPT обновился. Нужно пересобрать патч для новой версии.')
        if BACKUP.exists():raise SystemExit('Резервная копия уже есть. Повторная установка остановлена; сначала проверьте текущую версию.')
    verify=['/usr/bin/codesign','--verify','--strict'] + (['--deep'] if args.action=='install' else [])
    run(*verify,str(source))
    if args.action=='install':
        print('Сохраняю оригинал:',BACKUP,flush=True)
        run('/bin/cp','-cR',str(APP),str(BACKUP))
        run('/usr/bin/codesign','--verify','--strict',str(BACKUP))
    print('Подготавливаю замену…',flush=True)
    run('/bin/cp','-cR',str(source),str(STAGE))
    run(*verify,str(STAGE))
    os.rename(APP,PARK)
    try:
        os.rename(STAGE,APP)
    except BaseException:
        os.rename(PARK,APP)
        raise
    # Keep the previous installed bundle as an additional rollback copy.
    retained=ROOT/'work'/('pre-install-ChatGPT.app' if args.action=='install' else 'removed-themed-ChatGPT.app')
    if not retained.exists():os.rename(PARK,retained)
    print('Готово. Запустите обычный ChatGPT из Dock. Профиль и чаты не переносились.',flush=True)
    print('Резервная копия оригинала:',BACKUP,flush=True)

if __name__=='__main__':
    try:main()
    except (OSError,subprocess.CalledProcessError) as e:raise SystemExit('Установка остановлена: '+str(e))
