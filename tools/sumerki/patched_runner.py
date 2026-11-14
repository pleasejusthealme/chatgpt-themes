"""Run the locally patched copy with explicit isolation and a launch log. No CDP."""
import fcntl
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent.parent
APP = ROOT / 'work/ChatGPT Theme Test.app/Contents/MacOS/ChatGPT'
STATE = ROOT / 'work/theme-lab/patched'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-name', default='ChatGPT Theme Test.app')
    parser.add_argument('--ui-only', action='store_true', help='Use a separate UI-only profile and mock keychain; never log in here')
    args = parser.parse_args()
    if Path(args.app_name).name != args.app_name or not args.app_name.endswith('.app'):
        raise SystemExit('Expected a simple .app name')
    app = ROOT / 'work' / args.app_name / 'Contents/MacOS/ChatGPT'
    state = ROOT / 'work/theme-lab/menu-ui-only' if args.ui_only else STATE
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'runner.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Тестовая копия уже запущена этим скриптом. Используйте её окно или Ctrl+C в прежнем Терминале.')
        profile, home = state / 'profile', state / 'codex-home'
        profile.mkdir(exist_ok=True)
        home.mkdir(exist_ok=True)
        env = os.environ.copy()
        env.pop('BUILD_FLAVOR', None)
        env['CODEX_ELECTRON_USER_DATA_PATH'] = str(profile)
        env['CODEX_HOME'] = str(home)
        env['CODEX_SPARKLE_ENABLED'] = 'false'
        print('Открываю патченную копию с отдельным профилем:', profile, flush=True)
        print('Отладочного порта и загрузчика нет. Тема встроена в приложение.', flush=True)
        print('Не входите в аккаунт. Терминал оставьте открытым; Ctrl+C завершает тест.', flush=True)
        with (state / 'launch.log').open('a') as log:
            log.write('\n--- PATCHED TEST START ---\n')
            log.flush()
            command = [str(app), '--user-data-dir=' + str(profile)]
            if args.ui_only:
                command.append('--use-mock-keychain')
                print('Только проверка UI: используется тестовый ключ, не входите в аккаунт.', flush=True)
            child = subprocess.Popen(command,
                                     env=env, stdout=log, stderr=log, start_new_session=True)
            try:
                code = child.wait()
                print('Тестовый процесс завершён, код:', code, flush=True)
                print('Журнал:', state / 'launch.log', flush=True)
            except KeyboardInterrupt:
                print('\nОстанавливаю тестовую копию.', flush=True)
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()


if __name__ == '__main__':
    try:
        main()
    except OSError as exc:
        raise SystemExit(str(exc))
