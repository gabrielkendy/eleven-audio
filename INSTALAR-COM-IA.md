# Instalar o ELEVEN AUDIO com a sua IA

Cole **este arquivo inteiro** numa IA que consiga rodar comandos no seu computador
(Claude Code, Cursor, Codex, Gemini CLI ou similar). Ela lê, confere a máquina,
instala e prova que funcionou.

Se você não usa IA de terminal, use o `INSTALAR.bat` — faz o mesmo, com cliques.

---

# INSTRUÇÃO PARA A IA

Você vai instalar o **ELEVEN AUDIO** nesta máquina para uma pessoa que não é
técnica. Trabalhe em passos, mostrando o que está fazendo, sem pedir decisões
técnicas a ela.

## O que é

Um estúdio de voz local para Windows. Clonagem de voz, geração de fala,
transcrição, tradução e dublagem de áudio para outro idioma. Roda 100% na máquina
da pessoa: sem conta, sem assinatura, sem telemetria. Internet só na instalação.

## Onde você está

Esta pasta é o pacote. A estrutura é:

```
<esta pasta>/
  instalador/          ← os scripts que VOCÊ vai usar
    SO-CONFERIR.bat    ← só olha a máquina
    INSTALAR.bat       ← instala
    ABRIR.bat          ← sobe os serviços e abre o navegador
    FECHAR.bat         ← encerra
    DIAGNOSTICO.bat    ← gera relatório pra mandar de volta
  app/  web/  scripts/ ← o código do app
  docs/                ← documentação técnica
  README.md  LEIA-ME  ← o que a pessoa lê
```

## Requisitos mínimos da máquina

Confirme isto ANTES de instalar. Se algo não bate, PARE e avise a pessoa com o
número exato, não com "seu computador pode não aguentar".

| item | mínimo | como conferir |
|---|---|---|
| Windows | 10 (21H2+) ou 11, **64 bits** | `$env:PROCESSOR_ARCHITECTURE` tem que ter `64` |
| Python | **3.11, 3.12 ou 3.13** — NÃO 3.14+ | `python --version` |
| Git | qualquer versão recente | `git --version` |
| ffmpeg | obrigatório | `ffmpeg -version` |
| GPU | **NVIDIA com 8 GB de VRAM** (recomendado) | `nvidia-smi` |
| RAM | 16 GB | |
| Disco livre | **25 GB** | |

**Sobre o Python, isto é crítico:** o `torch` publica pacote pronto para 3.11,
3.12 e 3.13 e fica meses sem build para a versão seguinte. Se a máquina só tem
3.14+, instale o 3.13 **sem desinstalar o que já existe**:
`winget install --id Python.Python.3.13 -e`

**Sobre a GPU:** sem NVIDIA, funciona, mas gera na CPU em minutos por trecho em vez
de segundos. Avise a pessoa disso. AMD no Windows roda só CPU.

## Passos

### 1. Diagnóstico primeiro

Rode:

```
instalador\SO-CONFERIR.bat
```

Ou, se preferir em PowerShell direto:

```
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "instalador\instalar.ps1" -SoVerificar
```

Isto **não instala nada**. Leia a saída. Se listar `falta: ...`, siga para o passo 2.
Se disser `esta maquina tem tudo para rodar`, ainda rode o passo 2 — ele completa o
que falta (a base e os ambientes).

### 2. Instalar

Rode:

```
instalador\INSTALAR.bat
```

**Não reimplemente este passo.** O instalador já resolve quatro coisas que dão
errado quando feitas na mão, e você não tem como saber disso sem ler o código:

- a base instala por **`uv sync`**, não por `pip`. O `pyproject.toml` dela aponta
  `torch`/`torchaudio`/`torchvision` para um **índice próprio de CUDA**
  (`[tool.uv.sources]`) e trava as versões em `[tool.uv]` (`torch==2.8.0`). **O pip
  ignora as duas coisas** e instalaria um torch diferente do testado.
- o interpretador vem do próprio `uv` (gerenciado, versão certa), não do Python do
  sistema.
- o app é a pasta que **contém** `instalador/`, não uma subpasta de nome fixo.
- o `local.ps1` fica ao lado do `ABRIR.ps1`, senão o launcher nunca o encontra.

Se você trocar qualquer um desses, quebra. Deixe o script fazer.

O download é grande: ~3 GB de dependências mais os modelos na primeira geração.
Isso é normal e demora. **O download retoma de onde parou** — se cair a conexão,
rode de novo.

### 3. Subir e provar que funcionou

```
instalador\ABRIR.bat
```

Depois confirme, com o resultado na mão:

```
curl http://127.0.0.1:3900/health
curl http://127.0.0.1:7800/api/saude
```

O segundo tem que devolver `{"nosso_app":"ok","base":"ok","ffmpeg":"ok", ...}`.
Os três `ok` são a prova. Se algum não estiver `ok`, é ali que está o problema.

Depois abra `http://127.0.0.1:7800` no navegador da pessoa para ela ver a tela.

### 4. Se algo falhar

Rode o diagnóstico e leia o relatório que ele abre:

```
instalador\DIAGNOSTICO.bat
```

Ele grava um `.txt` na Área de Trabalho com: versões de tudo, os Pythons da máquina
(e qual foi descartado por ser de outro programa), a GPU, o que foi instalado, o que
responde, os modelos baixados e as últimas linhas de log.

**Mande esse arquivo de volta para quem te deu esta pasta.** Ele diz exatamente onde
parou. Não invente causa antes de ler.

Erros comuns e o que fazer:

| sintoma | causa | o que fazer |
|---|---|---|
| `a base nao respondeu em 3 minutos` | primeira subida carrega os modelos | rode de novo e espere |
| `ModuleNotFoundError` em pacote da base | ambiente incompleto | apague `base-voicestudio\.venv` e rode o INSTALAR de novo |
| `no Python found` / torch não instala | só tem Python 3.14+ | instale o 3.13 (passo 1) e rode de novo |
| geração muito lenta | sem GPU NVIDIA | conferir no diagnóstico; é esperado |
| `Job not found` | trabalho assíncrono ainda não terminou | espere e tente de novo |

## Regras — não cruze estas

1. **Não modifique nada dentro de `base-voicestudio/`.** Ela é de terceiro, sob
   AGPL-3.0. O app conversa com ela pela rede local. Mexer no código dela muda a
   licença do que a pessoa fizer.
2. **Não apague arquivo da pessoa.** Para "limpar", mova para uma pasta com aviso.
3. **Não peça senha, cartão ou chave de API.** Não existe conta em lugar nenhum —
   nem no HuggingFace, que baixa os modelos anonimamente.
4. **Não venda nem empacote comercialmente.** O modelo de voz (OmniVoice) tem pesos
   **CC-BY-NC**: usar de graça e repassar de graça pode, vender não pode.
5. Se a máquina tiver menos de 25 GB livres ou menos de 16 GB de RAM, **avise antes
   de baixar**, com o número.

## Relatório final, no fim

Termine com:

1. **status**: INSTALADO / PARCIAL / NÃO DEU
2. os três resultados de `/api/saude`
3. onde os arquivos ficaram (caminho da pasta)
4. o caminho do `DIAGNOSTICO.txt`, se você rodou
5. o que você **não** conseguiu verificar, dito com essas palavras

Não diga "está tudo funcionando" sem os três `ok` na mão.
