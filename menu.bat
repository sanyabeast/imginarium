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
echo        STOCK IMAGES GENERATOR - MAIN MENU
echo ===================================================
echo.
echo  [1] Generate Images
echo  [2] Search Images
echo  [3] Database Management
echo  [4] Setup/Update Dependencies
echo  [5] Exit
echo.
echo Enter your choice [1-5]:

set /p choice=

if "%choice%"=="1" goto generate_menu
if "%choice%"=="2" goto search_menu
if "%choice%"=="3" goto database_menu
if "%choice%"=="4" goto setup
if "%choice%"=="5" goto exit_program
goto main_menu

:generate_menu
cls
echo ===================================================
echo             GENERATE IMAGES
echo ===================================================
echo.
echo  [1] Generate with default settings
echo  [2] Custom generation
echo  [0] Back to main menu
echo.
echo Enter your choice [0-2]:

set /p gen_choice=

if "%gen_choice%"=="1" (
    echo Running generator with default settings...
    python generate.py --num 5 --workflow flux_dev --noemoji
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
echo.
echo At any prompt, type 'cancel' to return to the generate menu.
echo.

echo Enter number of images to generate (default: 5):
set /p num=
if "%num%"=="cancel" goto generate_menu
if "%num%"=="" set num=5

echo Enter workflow name (default: hidream):
set /p workflow=
if "%workflow%"=="cancel" goto generate_menu
if "%workflow%"=="" set workflow=hidream

echo Enter dimensions WIDTHxHEIGHT (default: 1536x1536):
set /p dimensions=
if "%dimensions%"=="cancel" goto generate_menu
if "%dimensions%"=="" set dimensions=1536x1536

echo Enter steps (default: 35):
set /p steps=
if "%steps%"=="cancel" goto generate_menu
if "%steps%"=="" set steps=35

echo Enter LLM model (default: gemma-3-4b-it):
set /p model=
if "%model%"=="cancel" goto generate_menu
if "%model%"=="" set model=gemma-3-4b-it

echo Running generator with custom settings...
python generate.py --num %num% --workflow %workflow% --dimensions %dimensions% --steps %steps% --model %model% --noemoji
pause
goto generate_menu

:search_menu
cls
echo ===================================================
echo             SEARCH IMAGES
echo ===================================================
echo.
echo  [1] Search by tags
echo  [2] Browse all images
echo  [0] Back to main menu
echo.
echo Enter your choice [0-2]:

set /p search_choice=

if "%search_choice%"=="1" (
    cls
    echo ===================================================
    echo             SEARCH BY TAGS
    echo ===================================================
    echo.
    echo Enter tags (comma separated):
    set /p tags=
    
    python search.py --tags "!tags!" --noemoji
    pause
    goto search_menu
)
if "%search_choice%"=="2" (
    echo Browsing all images...
    python search.py --all --noemoji
    pause
    goto search_menu
)
if "%search_choice%"=="0" goto main_menu
goto search_menu

:database_menu
cls
echo ===================================================
echo             DATABASE MANAGEMENT
echo ===================================================
echo.
echo  [1] Show database stats
echo  [2] Trim database
echo  [0] Back to main menu
echo.
echo Enter your choice [0-2]:

set /p db_choice=

if "%db_choice%"=="1" (
    echo Showing database stats...
    python db.py --stats --noemoji
    pause
    goto database_menu
)
if "%db_choice%"=="2" (
    echo Trimming database...
    python db.py --trim --noemoji
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
