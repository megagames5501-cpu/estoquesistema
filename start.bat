@echo off
setlocal

cd /d %~dp0

if not exist .venv (
  echo Criando ambiente virtual...
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul

set PYTHONPATH=%cd%\src
echo Iniciando Sistema de Estoque Visual...
python -m estoquesistema.webapp

endlocal
