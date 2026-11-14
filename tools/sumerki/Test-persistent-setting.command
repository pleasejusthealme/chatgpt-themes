#!/bin/zsh
set -eu
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp/}chatgpt-pref-test.XXXXXX")"
mkdir -p "$TEST_DIR/profile" "$TEST_DIR/codex-home"
# Chromium's persisted preference, not a command-line debugging switch.
printf '%s\n' '{"devtools":{"remote_debugging":{"user-enabled":true}}}' > "$TEST_DIR/profile/Local State"
printf '19381\n' > "$TEST_DIR/profile/DevToolsActivePort"
printf 'Проверка сохранённой настройки Chromium на пустом профиле.\n'
printf 'Основное окно и его профиль не меняются. Входить в аккаунт здесь не нужно.\n'
printf 'Если осталось старое тестовое окно, сначала закройте его.\n'
printf 'Тестовый профиль: %s\n' "$TEST_DIR/profile"
printf 'Здесь НЕТ флага --remote-debugging-port и НЕТ режима nightly.\n'
printf 'После открытия окна напишите в основном чате: «проверка настройки открылась».\n'
CODEX_ELECTRON_USER_DATA_PATH="$TEST_DIR/profile" \
CODEX_HOME="$TEST_DIR/codex-home" \
"/Applications/ChatGPT.app/Contents/MacOS/ChatGPT" \
  "--user-data-dir=$TEST_DIR/profile" \
  > "$TEST_DIR/launch.log" 2>&1 &
TEST_PID=$!
trap 'kill "$TEST_PID" 2>/dev/null || true' EXIT INT TERM
if wait "$TEST_PID"; then
  printf '\nТестовый процесс завершён.\n'
else
  printf '\nОшибка запуска. Лог: %s/launch.log\n' "$TEST_DIR"
fi
printf 'Нажмите Enter для завершения.\n'
read -r
