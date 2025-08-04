#!/bin/bash

echo "Launching PySide6 GUI app in virtual display..."
export DISPLAY=:1

Xvfb :1 -screen 0 1024x768x16 &
fluxbox &
x11vnc -display :1 -nopw -listen localhost -xkb -forever &

sleep 3  # Wait for virtual display to start

python ui/main_window.py
