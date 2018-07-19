@echo off
virtualenv venv
call .\activate_venv.bat
pip install docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew kivy.deps.gstreamer==0.1.12
pip install kivy==1.9.1
