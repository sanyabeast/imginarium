@echo off
setlocal enabledelayedexpansion

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if not defined VIRTUAL_ENV (
    echo [!] Failed to activate virtual environment.
    echo Please run install.bat first to set up the environment.
    pause
    exit /b 1
)
echo Virtual environment activated successfully!

:main_menu
cls
echo ===================================================
echo        IMGINARIUM - MAIN MENU
echo ===================================================
echo.
echo  [1] Generate Images
echo  [2] Search Images
echo  [3] Start Search Server
echo  [4] Setup/Update Dependencies
echo  [5] Exit
echo.
echo Enter your choice [1-5]:

set /p choice=

if "%choice%"=="1" goto config_selection
if "%choice%"=="2" goto search_menu
if "%choice%"=="3" goto server_menu
if "%choice%"=="4" goto setup
if "%choice%"=="5" goto exit_program
goto main_menu

:server_menu
cls
echo ===================================================
echo             START SEARCH SERVER
echo ===================================================
echo.
echo Enter server port (default: 5666, press Enter to use default):
set /p port=
if "%port%"=="" set port=5666

echo.
echo Starting search server on port %port%...
echo Press Ctrl+C to stop the server when done.
echo.
python search.py --server %port%
pause
goto main_menu

:search_menu
cls
echo ===================================================
echo             SEARCH IMAGES
echo ===================================================
echo.
echo Enter search query (or type 'cancel' to return to main menu):
set /p query=
if "%query%"=="cancel" goto main_menu
if "%query%"=="" goto search_menu

echo Enter maximum number of results to show (default: 5):
set /p limit=
if "%limit%"=="cancel" goto main_menu
if "%limit%"=="" set limit=5

echo Searching for images matching "%query%"...
python search.py -q "%query%" -l %limit% --noemoji
pause
goto main_menu

:config_selection
cls
echo ===================================================
echo        IMGINARIUM - CONFIGURATION SELECTION
echo ===================================================
echo.
echo Select a configuration to use:

:: List all available configs dynamically
set config_count=0
for %%f in (configs\*.yaml) do (
    set /a config_count+=1
    set "config_file[!config_count!]=%%~nf"
    echo  [!config_count!] %%~nf
)

echo  [0] Back to main menu
echo.
echo Enter your choice [0-!config_count!]:

set /p config_choice=

:: Handle back option
if "%config_choice%"=="0" goto main_menu

:: Handle empty choice (default to first config)
if "%config_choice%"=="" (
    set config=!config_file[1]!
    goto generate_menu
)

:: Validate choice is a number and in range
set /a choice_num=%config_choice% 2>nul
if %choice_num% LEQ 0 goto config_selection
if %choice_num% GTR %config_count% goto config_selection

:: Set the selected config
set config=!config_file[%choice_num%]!
goto generate_menu

:generate_menu
cls
echo ===================================================
echo             GENERATE IMAGES
echo ===================================================
echo Using configuration: %config%
echo.
echo  [1] Generate with default settings
echo  [2] Custom generation
echo  [0] Back to configuration selection
echo.
echo Enter your choice [0-2]:

set /p gen_choice=

if "%gen_choice%"=="1" (
    echo Running generator with default settings...
    python generate.py --num 5 --config %config% --noemoji
    pause
    goto generate_menu
)
if "%gen_choice%"=="2" goto custom_generation
if "%gen_choice%"=="0" goto config_selection
goto generate_menu

:custom_generation
cls
echo ===================================================
echo             CUSTOM GENERATION
echo ===================================================
echo Using configuration: %config%
echo.
echo At any prompt, type 'cancel' to return to the generate menu.
echo.

echo Enter number of images to generate (default from config or 5):
set /p num=
if "%num%"=="cancel" goto generate_menu
if "%num%"=="" set num=5

echo Enter workflow name (leave empty to use default from config):
set /p workflow=
if "%workflow%"=="cancel" goto generate_menu

echo Enter dimensions WIDTHxHEIGHT (default from config):
set /p dimensions=
if "%dimensions%"=="cancel" goto generate_menu

echo Enter steps (default from config):
set /p steps=
if "%steps%"=="cancel" goto generate_menu

echo Enter LLM model (default from config):
set /p model=
if "%model%"=="cancel" goto generate_menu

echo Running generator with custom settings...
if "%workflow%"=="" (
    set workflow_param=
) else (
    set workflow_param=--workflow %workflow%
)

if "%dimensions%"=="" (
    set dimensions_param=
) else (
    set dimensions_param=--dimensions %dimensions%
)

if "%steps%"=="" (
    set steps_param=
) else (
    set steps_param=--steps %steps%
)

if "%model%"=="" (
    set model_param=
) else (
    set model_param=--model %model%
)

python generate.py --num %num% %workflow_param% %dimensions_param% %steps_param% %model_param% --config %config% --noemoji
pause
goto generate_menu

:setup
echo Installing/Updating dependencies...
call install.bat
goto main_menu

:exit_program
echo Exiting program...
exit /b 0
