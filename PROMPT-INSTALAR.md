# PROMPT PARA A IA INSTALAR TUDO

Cole o bloco abaixo numa IA que rode comandos no computador (Claude Code, Cursor,
Codex, Gemini CLI). Ela baixa, instala, cria o atalho, baixa os modelos e prova
que funcionou. Funciona igual em qualquer versão futura: o link é fixo.

O prompt está pronto no repositório em `PROMPT-INSTALAR.md`, e repetido abaixo.

---

```
Instale o ELEVEN AUDIO nesta máquina, do zero, e me prove que funcionou.

O QUE É
Estúdio de voz local pra Windows. Clonagem de voz, geração de fala,
transcrição, tradução e dublagem de áudio pra outro idioma. Roda 100% na
máquina: sem conta, sem assinatura, sem telemetria. Internet só na instalação.

PASSO 1 — BAIXAR
Baixe e extraia:
https://github.com/gabrielkendy/eleven-audio/releases/latest/download/eleven-audio.zip

Se `git` estiver disponível, é equivalente e dá no mesmo:
git clone https://github.com/gabrielkendy/eleven-audio

Extraia numa pasta simples, tipo C:\ELEVEN. NÃO execute nada de dentro do zip.

PASSO 2 — INSTALAR
Entre na pasta `instalador` e rode `INSTALAR.bat`.

Não reimplemente este passo. O instalador já resolve quatro coisas que dão
errado quando feitas na mão, e você não tem como adivinhar isso:

  a) A base usa `uv sync`, não `pip`. O `pyproject.toml` dela aponta
     torch/torchaudio/torchvision pra um índice próprio de CUDA
     (`[tool.uv.sources]`) e trava as versões em `[tool.uv]`. O `pip` IGNORA as
     duas coisas e instalaria um torch diferente do testado.
  b) O interpretador vem do próprio `uv` (baixado por ele, na versão certa),
     não do Python do sistema.
  c) O app é a pasta que CONTÉM `instalador/`, não uma subpasta de nome fixo.
  d) O `local.ps1` (arquivo de ajustes da máquina) tem que ficar ao lado do
     `ABRIR.bat`, senão o launcher nunca encontra.

O instalador faz perguntas e espera "S". A primeira vez demora de 15 a 40
minutos: ele baixa o motor de voz e os pesos. Não feche a janela.

Se o Windows mostrar "O Windows protegeu o seu PC", é o aviso normal pra
arquivo novo: "Mais informações" e depois "Executar assim mesmo".

PASSO 3 — OS MODELOS
Os modelos de voz baixam sozinhos, do HuggingFace, na primeira vez que gerar
áudio. Não precisa de conta nem de token, e o download retoma de onde parou.
Se quiser adiantar, chame o launcher uma vez e gere um áudio de teste: é isso
que dispara o download.

PASSO 4 — O ATALHO
O instalador cria o atalho "ELEVEN AUDIO" na Área de Trabalho, apontando para o
`ABRIR.bat`. Se ele avisar que não conseguiu, crie o atalho à mão para o
`ABRIR.bat` que está na pasta `instalador`.

PASSO 5 — SUBIR E PROVAR
Rode `ABRIR.bat` (ou o atalho). Depois confirme, com o resultado na mão:

  curl http://127.0.0.1:3900/health
  curl http://127.0.0.1:7800/api/saude

O segundo tem que devolver algo como:
{"nosso_app":"ok","base":"ok","ffmpeg":"ok", ...}

Os três "ok" são a prova. Se algum não estiver "ok", é ali que está o problema.

Depois abra http://127.0.0.1:7800 no navegador pra pessoa ver a tela.

SE ALGO FALHAR
Rode `instalador\DIAGNOSTICO.bat`. Ele não altera nada: olha a máquina e grava
um relatório na Área de Trabalho (versões, GPU, o que foi instalado, o que
responde, modelos baixados e o fim dos logs). Leia esse arquivo antes de
concluir qualquer coisa, e mande ele de volta pra quem te deu esta tarefa.

Erros comuns:
- "a base nao respondeu em 3 minutos" -> primeira subida carrega os modelos;
  rode de novo e espere.
- ModuleNotFoundError em pacote da base -> apague `base-voicestudio\.venv` e
  rode o INSTALAR de novo.
- torch não instala / "no Python found" -> a máquina só tem Python 3.14+.
  Instale o 3.13 sem desinstalar o que já existe:
  winget install --id Python.Python.3.13 -e
- Geração muito lenta -> sem GPU NVIDIA. É esperado: na CPU leva minutos por
  trecho. Não é defeito.

O QUE A MÁQUINA PRECISA
  Windows 10 (21H2+) ou 11, 64 bits
  Python 3.11 a 3.13 — NÃO 3.14+ (o torch não tem build pra ela ainda)
  Git e ffmpeg (o instalador resolve sozinho via winget)
  GPU NVIDIA com 8 GB de VRAM (recomendado; sem ela roda na CPU, devagar)
  16 GB de memória
  25 GB livres no disco
  Sem conta, sem assinatura. Internet só na instalação.

REGRAS — NÃO CRUZE ESTAS
1. Não modifique nada dentro de `base-voicestudio/`. É código de terceiro, sob
   AGPL-3.0, e roda separado pela rede local.
2. Não apague arquivo da pessoa. Pra "limpar", mova pra uma pasta com aviso.
3. Não peça senha, cartão ou chave de API. Não existe conta em lugar nenhum.
4. Não venda nem empacote comercialmente: os pesos do modelo de voz são
   CC-BY-NC (grátis pra usar e repassar, proibido vender).
5. Se faltar disco ou memória, avise ANTES de baixar, com o número exato.

RELATÓRIO FINAL
Termine com:
1. status: INSTALADO / PARCIAL / NÃO DEU
2. os três resultados do /api/saude
3. a pasta onde ficou
4. o caminho do DIAGNOSTICO.txt, se você rodou
5. o que você NÃO conseguiu verificar, dito com essas palavras

Não diga "está tudo funcionando" sem os três "ok" na mão.
```
