#!/bin/bash
# Двойной клик — запустить CleanMac (если не хочется открывать .app).
PY="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
exec "$PY" "$HOME/mac-optimizer/cleaner/CleanMac.py"
