#!/bin/zsh
set -eu
printf 'Открываю ChatGPT с обычным профилем и локальным портом для темы.\n'
printf 'Перед запуском нужно полностью выйти из ChatGPT через Cmd+Q.\n'
printf 'Если приложение ещё работало, параметры могут не примениться.\n'
/usr/bin/open -a /Applications/ChatGPT.app --args \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=19382
