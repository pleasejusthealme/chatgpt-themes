"""Isolated repeatable theme test. Run from a normal macOS Terminal."""
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from theme_loader import CDP

HERE = Path(__file__).resolve().parent
STATE = HERE.parent.parent / 'work' / 'theme-lab' / 'css'
PORT = 19381
APP = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT'


def environment(profile, home):
    env = os.environ.copy()
    env.pop('BUILD_FLAVOR', None)
    env.pop('CODEX_RELEASE_BUILD_FLAVOR', None)
    env['CODEX_ELECTRON_USER_DATA_PATH'] = str(profile)
    env['CODEX_HOME'] = str(home)
    return env


def free_port():
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', PORT))
        except OSError as exc:
            raise RuntimeError('Порт 19381 занят. Закройте старое тестовое окно и его скрипт. Основное окно закрывать не нужно.') from exc


def apply_theme(targets, css):
    count = 0
    expression = """(() => {
      if (!document.head || !document.body) return false;
      const css = %s, id = 'sumerki-experimental-theme';
      let s = document.getElementById(id);
      if (s && s.textContent === css) return false;
      if (!s) { s = document.createElement('style'); s.id = id; document.head.appendChild(s); }
      s.textContent = css;
      return true;
    })()""" % json.dumps(css)
    for target in targets:
        # Restrict injection to the app shell, never login pages or browser tabs.
        if target.get('type') != 'page' or target.get('url') not in (
            'app://-/index.html', 'app://-/detached-window.html'):
            continue
        client = CDP(target['webSocketDebuggerUrl'], PORT)
        try:
            count += bool(client.evaluate(expression))
        finally:
            client.sock.close()
    return count


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'runner.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Этот тест уже запущен. Используйте открытое окно Терминала.')
        free_port()
        profile, home = STATE / 'profile', STATE / 'codex-home'
        profile.mkdir(exist_ok=True)
        home.mkdir(exist_ok=True)
        command = [APP, '--user-data-dir=' + str(profile),
                   '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=19381']
        print('Постоянный отдельный тестовый профиль:', profile, flush=True)
        print('Основной профиль не меняется. Входить в аккаунт не требуется.', flush=True)
        print('Тема подключается автоматически. Ctrl+C завершает только этот тест.', flush=True)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with (STATE / 'launch.log').open('a') as log:
            child = subprocess.Popen(command, env=environment(profile, home), stdout=log, stderr=log, start_new_session=True)
            started, connected, last_error = time.monotonic(), False, None
            try:
                while child.poll() is None:
                    try:
                        with opener.open(f'http://127.0.0.1:{PORT}/json/list', timeout=2) as response:
                            targets = json.load(response)
                        count = apply_theme(targets, (HERE / 'theme.css').read_text())
                        if not connected:
                            print('Подключение работает. Ожидаю загрузки интерфейса.', flush=True)
                        connected, last_error = True, None
                        if count:
                            print(f'Тема применена: окон {count}. CSS и перезагрузка интерфейса отслеживаются автоматически.', flush=True)
                    except (OSError, ValueError, RuntimeError, EOFError) as exc:
                        message = str(exc)
                        if time.monotonic() - started > 20 and message != last_error:
                            print('Подключение пока не удалось:', message, flush=True)
                            print('Лог:', STATE / 'launch.log', flush=True)
                            last_error = message
                    time.sleep(1)
                print('Тестовый процесс завершён, код:', child.returncode, flush=True)
                if child.returncode:
                    print('Лог:', STATE / 'launch.log', flush=True)
            except KeyboardInterrupt:
                print('\nОстанавливаю тест.', flush=True)
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
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc))
