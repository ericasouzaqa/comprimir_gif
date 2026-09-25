@echo off
setlocal

echo.
echo =============================================
echo       Criando Comprimir GIF
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
    pause
    exit /b 1
)

if not exist "LICENSES" (
    echo ERRO: a pasta LICENSES nao foi encontrada.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Criando aplicativo...
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

echo.
echo Criando ZIP para distribuicao...
powershell -NoProfile -Command "Compress-Archive -Path '.\dist\Comprimir GIF\*' -DestinationPath '.\dist\Comprimir-GIF-v1.0.1.zip' -Force"

echo.
echo =============================================
echo Aplicativo criado:
echo dist\Comprimir GIF\Comprimir GIF.exe
echo.
echo Arquivo para publicar:
echo dist\Comprimir-GIF-v1.0.1.zip
echo =============================================
echo.
pause