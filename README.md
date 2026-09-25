# Comprimir GIF

Aplicativo para Windows que converte arquivos GIF grandes em vídeos MP4 menores, com foco em preservar a legibilidade e reduzir o tamanho final para até 10 MB.

O processamento é feito localmente no computador. Nenhum arquivo é enviado para servidores.

## Download

Quando uma versão estiver disponível, baixe o arquivo `Comprimir GIF.exe` na seção [Releases](../../releases).

> O Windows pode exibir um aviso ao abrir executáveis novos que ainda não possuem assinatura digital. Baixe o arquivo apenas pela página oficial de Releases deste repositório.

## Recursos

- Seleção de arquivos GIF
- Aceita arquivos de entrada de até 100 MB
- Converte GIF em vídeo MP4
- Meta de arquivo final de até 10 MB
- Mantém a qualidade visual sempre que possível
- Ajusta resolução, FPS e bitrate automaticamente apenas quando necessário
- Exibe o tamanho antes e depois da conversão
- Exibe progresso durante o processamento
- Mostra uma estimativa de tempo restante
- Permite cancelar a conversão
- Salva o resultado na mesma pasta do GIF original
- Inclui ícone próprio no executável
- Funciona sem enviar arquivos para a internet

## Como usar

1. Baixe `Comprimir GIF.exe` na página de [Releases](../../releases).
2. Abra o aplicativo.
3. Clique em **Selecionar arquivo**.
4. Escolha um arquivo `.gif`.
5. Clique em **Comprimir**.
6. Aguarde a conversão.
7. Clique em **Abrir pasta do arquivo** para localizar o vídeo criado.

O aplicativo cria um vídeo MP4 ao lado do arquivo original.

Exemplo:

```text
animacao.gif
animacao_comprimido.mp4
```

## Limites e qualidade

O aplicativo aceita GIFs de até **100 MB** e procura gerar um MP4 de até **10 MB**.

Para conseguir reduzir arquivos grandes mantendo a imagem legível, o aplicativo usa conversão para MP4 com codec H.264 e codificação em duas passagens. Primeiro, ele tenta preservar a resolução e a fluidez. Caso o resultado ultrapasse o tamanho máximo, aplica perfis progressivos que reduzem resolução, FPS e bitrate apenas quando necessário.

A qualidade possível depende principalmente de:

- Duração da animação
- Resolução original
- Quantidade de movimento entre os frames
- Complexidade visual, como texto pequeno, vídeos, gradientes e efeitos

GIF é limitado a uma paleta de até 256 cores e costuma ser muito maior que um vídeo equivalente. Converter para MP4 permite reduzir drasticamente o tamanho mantendo uma qualidade visual melhor do que seria possível em um GIF com o mesmo limite de 10 MB.

## Privacidade

Todos os arquivos são processados localmente no seu computador.

O aplicativo:

- Não faz upload dos GIFs
- Não envia arquivos a servidores
- Não exige conta
- Não usa API externa
- Não coleta conteúdo dos arquivos selecionados

## Desenvolvimento

### Requisitos

Para executar ou gerar o aplicativo a partir do código-fonte:

- Windows 10 ou superior
- Python 3.10 ou superior
- FFmpeg e FFprobe para Windows
- Git, caso queira clonar ou contribuir com o projeto

A estrutura esperada do projeto é:

```text
ComprimirGIF/
├── app.py
├── requirements.txt
├── build_exe.bat
├── README.md
├── .gitignore
├── LICENSES/
│   └── LICENSE.txt
├── assets/
│   └── comprimir-gif.ico
└── tools/
    ├── ffmpeg.exe
    └── ffprobe.exe
```

### Executar pelo Python

No PowerShell, dentro da pasta do projeto:

```powershell
python -m pip install -r requirements.txt
python app.py
```

### Criar o executável

No PowerShell:

```powershell
.\build_exe.bat
```

O arquivo será criado em:

```text
dist\Comprimir GIF.exe
```

Teste o executável gerado antes de disponibilizá-lo.

## Tecnologias

- Python
- Tkinter
- FFmpeg
- FFprobe
- PyInstaller

O FFmpeg é usado para converter GIFs em MP4, com H.264 e codificação em duas passagens para controlar melhor o tamanho final.

## Licenças e créditos

Este projeto inclui FFmpeg e FFprobe para processamento local de mídia.

- Site do FFmpeg: https://ffmpeg.org/
- Código-fonte do FFmpeg: https://github.com/FFmpeg/FFmpeg
- Texto da licença do build usado: pasta `LICENSES/`

A licença aplicável ao FFmpeg depende da configuração do build distribuído. O FFmpeg é predominantemente LGPL, mas builds compiladas com componentes GPL podem estar sujeitas à GPL. Consulte o arquivo de licença incluído na pasta `LICENSES/` para os termos específicos do build utilizado.

## Publicação de versões

As versões distribuíveis do aplicativo devem ser disponibilizadas na seção [Releases](../../releases).

Cada Release pode incluir:

- `Comprimir GIF.exe`
- Notas da versão
- Melhorias e correções incluídas
- Instruções de uso, quando necessário
