"""Install the account-menu build or restore the immediately preceding installed app."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess

ROOT = Path(__file__).resolve().parent.parent
APP = Path('/Applications/ChatGPT.app')
BUILD = ROOT/'work/ChatGPT Theme Menu Test.app'
BACKUP = ROOT/'work/before-menu-ChatGPT.app'
STAGE = Path('/Applications/.ChatGPT-Themes-Menu-stage.app')
PARK = Path('/Applications/.ChatGPT-Themes-Menu-previous.app')

def run(*args):
    subprocess.run(args, check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['update','restore'])
    action=p.parse_args().action
    status=subprocess.run(['/usr/sbin/lsof','-t',str(APP/'Contents/MacOS/ChatGPT')],capture_output=True,text=True)
    if status.returncode not in (0,1) or status.stdout.strip():
        raise SystemExit('Полностью выйдите из основного ChatGPT через Cmd+Q перед заменой.')
    if STAGE.exists() or PARK.exists():
        raise SystemExit('Найдены файлы незавершённой установки. Остановлено для проверки.')
    source=BUILD if action=='update' else BACKUP
    if not source.exists():
        raise SystemExit('Не найдена копия: '+str(source))
    if action=='update':
        current=plistlib.loads((APP/'Contents/Info.plist').read_bytes())
        candidate=plistlib.loads((BUILD/'Contents/Info.plist').read_bytes())
        if current['CFBundleVersion']!=candidate['CFBundleVersion']:
            raise SystemExit('Версия приложения изменилась. Требуется новая сборка.')
        if BACKUP.exists():
            raise SystemExit('Резервная копия уже существует. Повторное обновление остановлено.')
    run('/usr/bin/codesign','--verify','--deep','--strict',str(source))
    if action=='update':
        run('/bin/cp','-cR',str(APP),str(BACKUP))
        print('Сохранена текущая рабочая версия:',BACKUP,flush=True)
    run('/bin/cp','-cR',str(source),str(STAGE))
    run('/usr/bin/codesign','--verify','--deep','--strict',str(STAGE))
    os.rename(APP,PARK)
    try:
        os.rename(STAGE,APP)
    except BaseException:
        os.rename(PARK,APP)
        raise
    print('Готово. Откройте обычный ChatGPT из Dock.',flush=True)
    print('Каталоги аккаунта, cookies и настройки Keychain не менялись.',flush=True)
    print('Предыдущая установленная копия также сохранена:',PARK,flush=True)
    # Keep a recovery artifact but free the park name so restore can run.
    retained=ROOT/'work'/('replaced-by-menu.app' if action=='update' else 'removed-menu.app')
    if not retained.exists():
        os.rename(PARK,retained)
    else:
        print('Резервный путь занят; перед следующей заменой проверьте '+str(PARK),flush=True)

if __name__=='__main__':
    try:
        main()
    except (OSError,subprocess.CalledProcessError) as e:
        raise SystemExit('Операция остановлена: '+str(e))
