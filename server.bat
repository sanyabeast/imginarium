@echo off
echo Starting Image Search Server...

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Ask for port number
set /p PORT_NUMBER="Enter port number (default: 5666): "

REM Use default port if nothing entered
if "%PORT_NUMBER%"=="" set PORT_NUMBER=5666

REM Run the server
echo Starting server on port %PORT_NUMBER%...
python server.py --host 127.0.0.1 --port %PORT_NUMBER%

REM If we get here, the server was stopped
echo Server stopped.
pause
