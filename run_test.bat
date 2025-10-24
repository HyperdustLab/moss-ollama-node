@echo off
echo Testing Nacos API call
echo ==================

REM Try using different Python commands
echo Trying to run Python test script...

REM Try python command
python test_nacos_api.py 2>nul
if %errorlevel% equ 0 goto :success

REM Try python3 command
python3 test_nacos_api.py 2>nul
if %errorlevel% equ 0 goto :success

REM Try py command
py test_nacos_api.py 2>nul
if %errorlevel% equ 0 goto :success

echo Error: Unable to find Python interpreter
echo Please ensure Python is installed and added to PATH environment variable
echo.
echo You can also manually run the following commands:
echo   python test_nacos_api.py
echo   or
echo   python3 test_nacos_api.py
echo   or
echo   py test_nacos_api.py
goto :end

:success
echo.
echo Test completed!

:end
pause
