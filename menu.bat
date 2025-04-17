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

echo  [0] Exit
echo.
echo Enter your choice [0-!config_count!]:

set /p config_choice=

:: Handle exit option
if "%config_choice%"=="0" goto exit_program

:: Handle empty choice (default to first config)
if "%config_choice%"=="" (
    set config=!config_file[1]!
    goto main_menu
)

:: Validate choice is a number and in range
set /a choice_num=%config_choice% 2>nul
if %choice_num% LEQ 0 goto config_selection
if %choice_num% GTR %config_count% goto config_selection

:: Set the selected config
set config=!config_file[%choice_num%]!
goto main_menu

:main_menu
cls
echo ===================================================
echo        IMGINARIUM - MAIN MENU
echo ===================================================
echo Using configuration: %config%
echo.
echo  [1] Generate Images
echo  [2] Search Images
echo  [3] Database Management
echo  [4] Setup/Update Dependencies
echo  [5] Change Configuration
echo  [6] Exit
echo.
echo Enter your choice [1-6]:

set /p choice=

if "%choice%"=="1" goto generate_menu
if "%choice%"=="2" goto search_menu
if "%choice%"=="3" goto database_menu
if "%choice%"=="4" goto setup
if "%choice%"=="5" goto config_selection
if "%choice%"=="6" goto exit_program
goto main_menu

:generate_menu
cls
echo ===================================================
echo             GENERATE IMAGES
echo ===================================================
echo Using configuration: %config%
echo.
echo  [1] Generate with default settings
echo  [2] Custom generation
echo  [0] Back to main menu
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
if "%gen_choice%"=="0" goto main_menu
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

:search_menu
cls
echo ===================================================
echo             SEARCH IMAGES
echo ===================================================
echo Using configuration: %config%
echo.
echo  [1] Search by tags
echo  [2] Browse all images
echo  [0] Back to main menu
echo.
echo Enter your choice [0-2]:

set /p search_choice=

if "%search_choice%"=="1" goto search_by_tags
if "%search_choice%"=="2" (
    echo Browsing all images...
    python search.py --recent 100 --config %config% --noemoji
    pause
    goto search_menu
)
if "%search_choice%"=="0" goto main_menu
goto search_menu

:search_by_tags
cls
echo ===================================================
echo             SEARCH BY TAGS
echo ===================================================
echo Using configuration: %config%
echo.
echo At any prompt, type 'cancel' to return to the search menu.
echo.

echo Enter tags (comma separated):
set /p tags=
if "%tags%"=="cancel" goto search_menu
if "%tags%"=="" goto search_menu

python search.py --tags "%tags%" --config %config% --noemoji
pause
goto search_menu

:database_menu
cls
echo ===================================================
echo             DATABASE MANAGEMENT
echo ===================================================
echo Using configuration: %config%
echo.
echo  [1] Show database stats
echo  [2] Trim database
echo  [0] Back to main menu
echo.
echo Enter your choice [0-2]:

set /p db_choice=

if "%db_choice%"=="1" (
    echo Showing database stats...
    python db.py --stats --config %config% --noemoji
    pause
    goto database_menu
)
if "%db_choice%"=="2" (
    echo Trimming database...
    python db.py --trim --config %config% --noemoji
    pause
    goto database_menu
)
if "%db_choice%"=="0" goto main_menu
goto database_menu

:setup
echo Installing/Updating dependencies...
call install.bat
goto main_menu

:exit_program
echo Exiting program...
exit /b 0
