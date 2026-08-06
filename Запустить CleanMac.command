#!/bin/bash
# Двойной клик — запустить CleanMac (актуальные исходники).
PY="/usr/bin/python3"
[ -x "$PY" ] || PY="/usr/bin/python3"
exec "$PY" "$HOME/projects/CleanMac/CleanMac.py"
