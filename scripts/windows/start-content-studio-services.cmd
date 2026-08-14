@echo off
REM Controlled start. No pause. Loopback only.
set CONTENT_STUDIO_OM_REPO=C:\ContentStudio\repos\OpenMontage
C:\ContentStudio\runtime\OpenMontage-test-venv\Scripts\python.exe -X utf8 %CONTENT_STUDIO_OM_REPO%\tools\content_studio_runtime.py start
exit /b %ERRORLEVEL%
