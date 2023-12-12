@echo off
set root="C:\Users\Lab Laptop\miniconda3"
call %root%\Scripts\activate.bat %root%
call conda activate mfiaEnv
call python "C:\Users\Lab Laptop\Desktop\prktkifnl\GUImain.py"
pause