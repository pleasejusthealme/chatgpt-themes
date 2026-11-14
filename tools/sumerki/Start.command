#!/bin/zsh
set -eu
THEME_DIR="${0:A:h}"
exec python3 -u "$THEME_DIR/test_runner.py"
