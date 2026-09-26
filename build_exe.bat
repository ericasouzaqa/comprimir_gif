@echo off
setlocal

echo.
echo =============================================
echo        Criando Comprimir GIF
echo =============================================
echo.

if not exist "tools\ffmpeg.exe" (
    echo ERRO: tools\ffmpeg.exe nao foi encontrado.
    pause
    exit /b 1
)

if not exist "tools\ffprobe.exe" (
    echo ERRO: tools\ffprobe.exe nao foi encontrado.
    pause
    exit /b 1
)

if not exist "assets\comprimir-gif.ico" (
    echo ERRO: assets\comprimir-gif.ico nao foi encontrado.
    echo Coloque o arquivo ICO dentro da pasta assets.
    pause
    exit /b 1
)

if not exist "LICENSES\" (
    echo ERRO: a pasta LICENSES nao foi encontrada.
    pause
    exit /b 1
)

dir /b "LICENSES\*" >nul 2>&1

if errorlevel 1 (
    echo ERRO: a pasta LICENSES esta vazia.
    echo Coloque o arquivo de licenca dentro dela.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias Python...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Criando aplicativo em pasta...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name "Comprimir GIF" ^
  --icon "assets\comprimir-gif.ico" ^
  --add-data "assets;assets" ^
  --add-data "LICENSES;LICENSES" ^
  --add-binary "tools\ffmpeg.exe;tools" ^
  --add-binary "tools\ffprobe.exe;tools" ^
  app.py

if errorlevel 1 (
    echo.
    echo ERRO: o PyInstaller nao conseguiu criar o aplicativo.
    pause
    exit /b 1
)

echo.
echo Criando ZIP para distribuicao...

if exist "dist\Comprimir-GIF-v1.0.1.zip" (
    del /f /q "dist\Comprimir-GIF-v1.0.1.zip"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Compress-Archive -Path '.\dist\Comprimir GIF\*' -DestinationPath '.\dist\Comprimir-GIF-v1.0.1.zip' -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel criar o ZIP.
    pause
    exit /b 1
)

echo.
echo =============================================
echo Aplicativo pronto:
echo dist\Comprimir GIF\Comprimir GIF.exe
echo.
echo Arquivo para publicar:
echo dist\Comprimir-GIF-v1.0.1.zip
echo =============================================
echo.
pause