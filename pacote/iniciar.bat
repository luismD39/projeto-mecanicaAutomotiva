@echo off
chcp 65001 >nul
title AutoScan Pro
cd /d "%~dp0"

echo.
echo  ==================================================
echo   AutoScan Pro - simulador didático de diagnóstico
echo  ==================================================
echo.

rem Só roda dentro do pacote gerado pelo empacotar.py (tem run.py e a pasta wheels).
if not exist "run.py" goto :fora_do_pacote
if not exist "wheels\" goto :fora_do_pacote

rem 1) Procura o Python 3.11 ou mais recente ("py" vem com o instalador do python.org).
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=python"
if not defined PY goto :sem_python

rem 2) Primeira vez: cria o ambiente e instala as bibliotecas da pasta "wheels" (sem internet).
if exist ".venv\instalado.ok" goto :iniciar
echo  Preparando o AutoScan Pro pela primeira vez. Isso leva menos de um minuto...
if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv
if errorlevel 1 goto :erro_instalacao
".venv\Scripts\python.exe" -m pip install --no-index --find-links wheels -r requirements.txt --disable-pip-version-check -q
if errorlevel 1 goto :erro_instalacao
echo ok> ".venv\instalado.ok"
echo  Pronto!
echo.

:iniciar
rem 3) Modo apresentação: sem debug, porta livre e navegador aberto automaticamente.
set "AUTOSCAN_APRESENTACAO=1"
".venv\Scripts\python.exe" run.py
if errorlevel 1 goto :erro
goto :eof

:sem_python
echo  [!] Não encontrei o Python 3.11 ou mais recente neste computador.
echo.
echo      Instale o Python pelo instalador oficial (https://www.python.org/downloads/).
echo      Na primeira tela do instalador, marque "Add python.exe to PATH".
echo      Se não tiver senha de administrador, deixe DESMARCADA a opção
echo      "Use admin privileges when installing py.exe".
echo      Depois, abra este arquivo de novo.
echo.
pause
exit /b 1

:erro_instalacao
echo.
echo  [!] Não foi possível instalar as bibliotecas da pasta "wheels".
echo      A versão do Python deste computador pode não estar no pacote (3.11 a 3.14, 64 bits).
if exist ".venv" rmdir /s /q ".venv"
echo.
pause
exit /b 1

:fora_do_pacote
echo  [!] Este arquivo deve ser aberto de dentro da pasta AutoScanPro,
echo      junto com run.py e a pasta "wheels" (gerada pelo empacotar.py).
echo.
pause
exit /b 1

:erro
echo.
echo  [!] O AutoScan Pro parou com um erro. Leia a mensagem acima.
echo.
pause
exit /b 1
