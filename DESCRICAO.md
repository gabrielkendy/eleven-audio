# ELEVEN AUDIO

**Descrição curta** (pra colar na descrição do repositório ou onde precisar):

> Estúdio de voz local sem login e sem nuvem: clona voz, gera fala, transcreve,
> traduz e dubla áudio pra outro idioma. Windows, MIT, roda na sua máquina.

---

## Os caminhos

**Pasta local (esta máquina):**
```
C:\Users\Gabriel\Documents\eleven-audio
```

**Repositório:**
```
https://github.com/gabrielkendy/eleven-audio
```

**Download direto, link fixo (sempre a versão mais nova):**
```
https://github.com/gabrielkendy/eleven-audio/releases/latest/download/eleven-audio.zip
```

**Quem já está rodando:**
```
app   (a tela)   http://127.0.0.1:7800   →  /api/saude
base  (o motor)  http://127.0.0.1:3900   →  /health
```

---

## Bloco pra colar numa IA

```
Contexto do projeto ELEVEN AUDIO.

O QUE É
Estúdio de voz local pra Windows: clonagem de voz, geração de fala, transcrição,
tradução e dublagem de áudio pra outro idioma. Roda 100% na máquina, sem conta,
sem assinatura, sem telemetria. Licença MIT. Autor: Gabriel Kendy (Agência BASE).

ONDE ESTÁ
  Pasta local: C:\Users\Gabriel\Documents\eleven-audio
  Repositório: https://github.com/gabrielkendy/eleven-audio
  Zip (link fixo): https://github.com/gabrielkendy/eleven-audio/releases/latest/download/eleven-audio.zip

COMO ESTÁ MONTADO
  app/        o adaptador (FastAPI + HTML/CSS/JS puro, sem build). Porta 7800.
              É a raiz do repositório.
  web/        a interface, servida pelo app.
  instalador/ os .bat e .ps1 de instalação. Fica DENTRO do app.
  tests/      a suíte. 290 testes.
  scripts/    verificar-tudo.py e verificar-instalador.py, os comandos canônicos.
  docs/       documentação, incluindo a mensagem de envio.
  base-voicestudio/  o motor de voz, projeto de terceiro sob AGPL-3.0. Roda
              separado, na porta 3900, e NÃO é versionado nem modificado aqui.

O QUE NÃO FAZER
  1. Não modificar nada em base-voicestudio/. É código de terceiro.
  2. Não usar pip na base: ela instala por `uv sync` (o pyproject aponta o torch
     pra um índice de CUDA e trava as versões; o pip ignora as duas coisas).
  3. Não apagar arquivo do dono.
  4. Não commitar chave, token, senha ou caminho pessoal.

COMO RODAR OS SERVIÇOS
  Abrir os dois:  instalador/ABRIR.bat
  Derrubar:       instalador/FECHAR.bat
  Ver se dá:      instalador/SO-CONFERIR.bat
  Diagnóstico:    instalador/DIAGNOSTICO.bat  (não altera nada, gera relatório)

COMO VERIFICAR MUDANÇA
  ruff:        python -m ruff check app tests scripts ferramentas
  testes:      python -m pytest -q
  instalador:  python scripts/verificar-instalador.py
  tudo:        python scripts/verificar-tudo.py   (exige os dois serviços no ar)
```

---

## O que é, em uma linha por função

| função | o que faz |
|---|---|
| **Clonar** | a partir de um áudio de referência de 5 s a 180 s |
| **Gerar** | fala com a voz clonada, em 50 idiomas |
| **Transcrever** | áudio pra texto, com tempo por palavra |
| **Traduzir** | texto ou áudio, por LLM local (Ollama) com Argos de reserva |
| **Dublar** | áudio em um idioma vira áudio em outro, com a voz clonada |

Estúdio de voz **local**. Sem login, sem nuvem, sem crédito.
