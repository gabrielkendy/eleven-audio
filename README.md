# ELEVEN_AUDIO — Estúdio de Voz Local

Repositório público: **github.com/gabrielkendy/eleven-audio** (MIT)
Autor: Gabriel Kendy (Agência BASE)
Stack: Python 3.11+, HTML/CSS/JS puro, FastAPI, uvicorn, SQLite, ffmpeg

---

## O que é

Um estúdio de voz que roda **100% na sua máquina**, sem nuvem, sem custo de inferência,
sem telemetria. Você abre no navegador (`http://127.0.0.1:7800`), grava ou manda um
clipe da sua voz (5 a 180 segundos), e o app clona. Também desenha voz a partir de
descrição textual, transcreve, compara motores e serve de agente para o WhatsApp.

O motor que ficou melhor no ouvido (OmniVoice) tem pesos **CC-BY-NC** — não serve
para uso comercial. Para vender, use VoxCPM2 (Apache-2.0) ou Qwen3-TTS (Apache-2.0).
A tela avisa isso.

---

## Instalação mínima

### Pré-requisitos

| item | mínimo | por quê |
|---|---|---|
| Windows | 10/11 | testado só aqui |
| Python | 3.11+ | exigência da base |
| **ffmpeg** | obrigatório | corta silêncio, mede duração, normaliza — é o que mais melhora a clonagem (medido: 0,8025 com preparo contra 0,7404 sem) |
| GPU NVIDIA | 8 GB VRAM | o estúdio usa ~6 GB; 6 GB não dá folga pro Windows |
| RAM | 16 GB | consome ~1,3 GB numa geração |
| Disco livre | 20 GB | 9 GB ambiente + 2,9 GB transcrição + pesos + áudios |
| Internet | só na instalação | depois roda offline (provado: zero conexões com `HF_HUB_OFFLINE=1`) |

### Passos

```powershell
# 1) Clona
git clone https://github.com/gabrielkendy/eleven-audio.git
cd eleven-audio

# 2) Instala ffmpeg (precisa uma vez)
winget install Gyan.FFmpeg
# ou: choco install ffmpeg  /  scoop install ffmpeg

# 3) Cria venv e instala
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt

# 4) Baixa a base VoiceStudio (AGPL-3.0, imutável, serve na porta 3900)
git clone https://github.com/gabrielkendy/voice-studio-base.git ../voice-studio-base
cd ../voice-studio-base
.\scripts\subir-base.ps1   # sobe em modo offline, sem telemetria

# 5) Volta pro estúdio e liga tudo
cd ..\eleven-audio
.\scripts\ligar-tudo.ps1   # sobe base (3900) + app (7800) e abre o navegador
```

Pronto. A tela abre em `http://127.0.0.1:7800`.

---

## Como funciona (resumo técnico)

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  Navegador (127.0.0.1:7800)                                 │
│  ─────────────────────                                      │
│  HTML/CSS/JS puro · 7 abas · sem build · sem npm            │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/JSON
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  App Python (FastAPI, porta 7800)                           │
│  ──────────────────────────────                             │
│  • Orquestra tudo                                           │
│  • Prepara a referência (corta silêncio, acha melhor janela, │
│    normaliza nível) — ESSA É A MÁGICA                       │
│  • Gerencia perfis, saídas, comparações, agente             │
│  • SQLite em dados/estudio.db                               │
│  • ffmpeg resolvido em 3 camadas (PATH, instaladores, registro)│
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/JSON
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Base VoiceStudio (porta 3900) — AGPL-3.0                   │
│  ─────────────────────────────────────                      │
│  17 motores TTS, 4 disponíveis offline                      │
│  OmniVoice (CC-BY-NC) · VoxCPM2 (Apache-2.0) · Qwen3-TTS     │
│    (Apache-2.0) · Chatterbox PT-BR (MIT, CPU)               │
│  Roda em modo offline forçado:                              │
│  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
└─────────────────────────────────────────────────────────────┘
```

### O preparo da referência (o que faz valer a pena)

Quando você manda um clipe, o app **não passa direto** pro motor. Ele:

1. Decodifica com ffmpeg para mono 16 kHz float32 (só análise)
2. Mede a energia em janelas de 25 ms com salto de 10 ms
3. Corta o silêncio das pontas (piso absoluto 0,004 em escala 0..1)
4. Se o que sobrou passa de 30 s, acha a **melhor janela de 30 s** (mais energia média)
5. Normaliza o pico para -1 dBFS, sem amplificar mais que +12 dB
6. **Sempre devolve WAV**, mesmo se a entrada era MP3 (bug corrigido: antes degradava silencioso)

O resultado é **30 s limpos, nivelados, só fala** — e é isso que o motor recebe.
Medido A/B na mesma voz/texto/semente: **0,8025 com preparo vs 0,7404 sem**.
O preparo está ligado por padrão (`ESTUDIO_PREPARO=0` desliga).

---

## As 7 telas

| tela | o que faz | rotas principais |
|---|---|---|
| **Gerar** | Síntese simples: texto → áudio com o perfil selecionado | `POST /api/gerar`, `GET /api/gerar/{id}`, `GET /api/marcas` |
| **Clonar** | Cria perfil de voz a partir do seu clipe (5–180 s, exige consentimento) | `POST /api/clonar`, `GET /api/perfis`, `GET /api/perfis/{id}/qualidade`, `DELETE /api/perfis/{id}` |
| **Transcrever** | Áudio → texto (Whisper da base) | `POST /api/transcrever`, `GET /api/transcricoes` |
| **Traduzir** | Texto entre 50 idiomas, e **_áudio → áudio_** na sua voz clonada | `POST /api/traduzir/texto`, `POST /api/traduzir/detectar`, `POST /api/dublar`, `GET /api/audio` |
| **Desenhar voz** | Descrição textual → perfil (só com **VoxCPM2** ativo) | `POST /api/desenhar`, `GET /api/desenhos` |
| **Comparar** | Mesmo texto/perfil em vários motores lado a lado | `POST /api/comparar`, `GET /api/comparar/{grupo}`, `GET /api/comparar/{grupo}/audio/{id}` |
| **Agente** | Liga/desliga cliente no MCP da base (WhatsApp) | `GET /api/agente/status`, `POST /api/agente/ligar`, `POST /api/agente/desligar` |
| **Configuração** | Motor ativo, saídas, estado, limites, licenças | `GET /api/estado`, `GET /api/motores`, `POST /api/motores/ativo`, `GET /api/saidas` |

---

## Tradução e dublagem (áudio → áudio)

Tradutor **offline** (Argos, roda em CPU, sem chave de API), com **50 idiomas**.

### O problema que a cascata resolve

Medido em 29/09/2026: o Argos tem 100 pares, mas a distribuição é desigual —

| saindo de | idiomas de destino disponíveis |
|---|---|
| `pt` | **2** (`en`, `es`) |
| `en` | **47** |

Ou seja: "traduzir para qualquer idioma" só funciona com um intermediário. Quando
não existe par direto, o app passa pelo **inglês** e **avisa na tela** que houve
dois saltos (a resposta traz `saltos: 2` e uma observação). Esconder isso seria
esconder uma perda de qualidade de quem usa.

### Português do Brasil é idioma separado

O Argos tem `pt` (Portugal) e `pb` (Brasil) como códigos distintos. Traduzir para
`pt` devolve *"como estás, a correr"*, que soa errado para brasileiro. O app
normaliza: `pt-BR`, `pt_br`, `br` → `pb`. Testado:

| pedido | resultado |
|---|---|
| en → pb | "Bom dia! Este é o estúdio de voz da minha secretária eletrônica." |
| pt → en | "Good morning! This is the voice studio running on my machine." |
| pt → ja | おはようございます! マシン上での音声スタジオです。 (via inglês) |

### Como o áudio → áudio funciona

```
áudio em português
   │
   ├─ 1. TRANSCREVE (Whisper) ..... devolve o texto
   ├─ 2. DESCOBRE O IDIOMA ........ pelo texto, via Ollama (não pela base)
   ├─ 3. TRADUZ (Argos) ........... com cascata pelo inglês quando precisa
   ├─ 4. DIVIDE em pedaços ........ por fim de frase, sem cortar palavra
   └─ 5. FALA (motor + seu perfil)  na sua voz clonada
                │
                ▼
        áudio em inglês, NA SUA VOZ
```

**Por que o idioma não vem da transcrição:** medido em 29/09/2026, o campo
`language` que a base devolve é apenas **eco do que foi enviado**, não detecção. Um
áudio em inglês transcrito com `language=pt` voltava como `"pt"`. Por isso o app
manda `auto` para o Whisper e descobre o idioma pelo texto transcrito, com o
Ollama. Sem isso, um áudio inglês era tratado como português e pegava um caminho de
dois saltos sem necessidade.

Texto longo é dividido (motores degradam ou recusam textos compridos) e os pedaços
são juntados sem recodificar, exigindo o mesmo formato em todos: misturar taxas
produziria áudio em velocidade errada.

**Por que não usar o dublador da própria base (SoniTranslate):** ele tem ambiente
próprio e servidor separado na porta 7860, e está **não instalado** nesta máquina.
Fazendo aqui, o áudio sai na **sua voz clonada**, que é o ponto do projeto, e não
numa voz genérica de dublador.

### Quem traduz: o modelo local ou o Argos

Há dois tradutores e você escolhe na tela, no campo **Tradutor**:

| opção | o que é | quando usar |
|---|---|---|
| **Modelo local, com Argos de reserva** (padrão) | Usa o modelo do Ollama; se ele não estiver no ar, o Argos assume e a resposta diz isso | uso normal |
| **Só o modelo local** | Exige o modelo; qualidade máxima de texto | quando o texto importa mais que a velocidade |
| **Só o Argos** | Offline, instantâneo, roda sem carregar modelo | quando quer velocidade ou está sem o Ollama |

**Medido em 29/09/2026, no mesmo trecho** ("A gente resolve o problema do cliente
antes de falar de preço, entendeu? É isso que segura a parceria."):

| | tradução |
|---|---|
| modelo local | "We solve **the customer's** problem before we **even** talk about price, **got it**? And that's what **keeps** the partnership **going**." |
| Argos | "We solve **the client's** problem before we talk about price, **understand**? That's what **holds** the partnership." |

O Argos erra tempo verbal: "A gente resolve" (hábito) saía como "We'll solve"
(futuro). Em dublagem isso se ouve na hora. O Argos continua sendo o mais rápido e
o que funciona sem modelo carregado.

O texto longo também passa: 238 palavras traduzidas inteiras em **8 s**, sem truncar
nem encher linguiça.

### Duas dublagens: completa e simples

A tela deixa escolher, no campo **Dublagem**:

| modo | o que faz | quando usar |
|---|---|---|
| **Completa** (padrão) | A base separa a voz da trilha (demucs), transcreve com o tempo de cada trecho e encaixa a fala nova no tempo do original. Mantém a música de fundo | dublar vídeo, entrevista, qualquer coisa com trilha ou mais de uma pessoa |
| **Simples** | Transcreve, traduz e sintetiza de uma vez | quando a pressa importa mais que o encaixe |

**Medido em 29/09/2026**, num trecho de 10 s de português:

```
original   segmentos: [0,87-4,28] e [4,28-9,98]
dublado    segmentos: [0,85-4,08] e [4,27-9,50]
duração do dublado: 10,00 s, igual ao original
sync_scores: [1.067, 0.942]
```

A fala nova cai praticamente no mesmo lugar que a antiga. Na simples isso não
acontece: o áudio sai com a duração que a voz quiser.

Outras diferenças medidas:

- **Trilha**: a completa separa `vocals.wav` da música (`no_vocals.wav`), então a
  música continua no dublado. A simples descarta tudo que não é voz.
- **Vários falantes**: a completa identifica quem fala (`speaker_id`) e avisa na
  resposta em quantos falantes o áudio foi dividido.
- **No modo completo o campo Motor fica desabilitado**: quem sintetiza é a base,
  não o motor escolhido na tela, e deixar habilitado faria escolher um motor que
  nunca entra.

### Armadilhas da pipeline da base, medidas em 29/09/2026

Nenhuma aparece na suíte de testes, porque todas vêm do comportamento da base:

1. **O upload é assíncrono.** Ele roda extract e demucs em segundo plano. Só
   depois do evento `ready` no `/tasks/stream/{task_id}` a transcrição funciona.
   Tentar antes devolve `Job not found`, que parece erro de identificador e não é.
2. **O `source_lang` da base não é confiável.** Ela marcou `'en'` num áudio
   claramente em português. Por isso o idioma de origem é detectado pelo texto,
   com o modelo local, em `app/dub_base.py`.
3. **`start` e `end` chegam como texto** (`"0.87"`), não número. Sem converter, o
   encaixe no tempo falha em silêncio e o áudio sai fora de sincronia.
4. **`/dub/audio` devolve a ENTRADA.** O dublado está em `/dub/download-audio`.
   Confundir os dois entrega o áudio original com nome de dublado.
5. **`profile_id` precisa ir em todos os segmentos.** Sem ele a base clona o
   falante original, o que é ótimo para dublar outra pessoa e errado quando o
   pedido é sair na voz escolhida. Medido: com o identificador errado o áudio sai
   diferente, com o certo sai na sua voz.
6. **O perfil local não é o perfil da base.** `vz-b2f95272834d` é o id local;
   `2bee8696` é o que a base conhece. Mandar o local faz a base cair na clonagem
   automática sem avisar.

### Pacotes de idioma (a tela baixa o que falta)

O tradutor é offline e cada par de idiomas é um pacote que baixa uma vez e fica na
máquina. A aba **Traduzir** tem um painel que mostra o que falta e baixa sem sair
dela. Quando falta pacote no meio de uma tradução, o erro aponta o painel para o
par exato que falhou, em vez de só reclamar.

Nem todo par existe no catálogo: saindo de `pb` só existe `en` como destino
direto. Então `pb -> fr` **nunca** vai existir, e a tradução passa por
`pb -> en -> fr`. Quando você pede para baixar um par assim, a rota baixa **as duas
etapas** e diz qual foi o caminho, em vez de devolver o erro em inglês do Argos
(*"No Argos language pack is available for pb → fr"*).

| rota | o que faz |
|---|---|
| `GET /api/traduzir/pacotes?origem=pb` | Lista o que já está baixado, saindo de um idioma |
| `POST /api/traduzir/pacotes` | Baixa o que falta, resolvendo o caminho sozinho |

Limite medido: a base recusa mais de **32 destinos por chamada** ("List should have
at most 32 items"), então consultas e downloads vão em lotes de 32.

### Dependência opcional: detecção de idioma

O Argos não detecta idioma, e a base também não expõe detecção de texto. Se o
**Ollama** estiver rodando em `127.0.0.1:11434`, o app usa o modelo local para
detectar. Se não estiver, a tela simplesmente pede a escolha na mão — nunca chuta.
Para o áudio → áudio isso nem é necessário: o Whisper já devolve o idioma.

---

## Motores disponíveis (offline)

| motor | licença | clona? | usa quanto da referência | nota |
|---|---|---|---|---|
| **OmniVoice** | código Apache-2.0, **pesos CC-BY-NC** | sim | melhor janela ~20 s (`best_window`) | **Não use em produto pago** — a tela avisa |
| **VoxCPM2** | Apache-2.0 | sim | primeiros 30 s (`head`) | o que "Desenhar voz" exige |
| **Qwen3-TTS** | Apache-2.0 | sim | **sem transcrição** (destrava 3 min) | 1,7B, 10 idiomas incluindo PT-BR |
| **Chatterbox PT-BR** | MIT | sim | aceitou 75 s no teste | roda em **CPU** (~90 s para 7 s de áudio) |

**Honestidade na tela:** cada motor mostra `uso_da_referencia` (`head`, `best_window`, `full`, ou `não verificado`), `dispositivo`, `licenca` (com `comercial: true/false`) e `aviso_licenca` quando proíbe uso comercial.

---

## O que foi medido (não prometido)

### Qualidade de clonagem (mesma voz/texto/semente 2026)

| motor | similaridade (ECAPA-TDNN) | tempo | observação |
|---|---|---|---|
| VoxCPM2 | **0,8064** | 49,8 s | melhor número |
| Qwen3-TTS (sem transcrição) | 0,7979 | — | praticamente empata, sem precisar transcrever |
| Qwen3-TTS (com transcrição) | 0,7940 | — | idêntico ao anterior |
| OmniVoice | 0,7694 | 15,9 s | usa ~20 s da referência |
| Chatterbox PT-BR | 0,7567 | 90 s (CPU) | licença MIT, roda sem GPU |

### Com saída crua (effect_preset=raw, denoise=false — padrão do app)

| motor | similaridade |
|---|---|
| OmniVoice | **0,8178** (era 0,7694 com limpeza) |
| VoxCPM2 | 0,7842 |

A base aplicava limpeza de ruído + compressão "broadcast" sem pedir; desligando, **os dois motores melhoraram**. O app injeta isso por padrão (`PADROES_FIEIS`).

### Localidade (provada, não prometida)

Com `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1` injetados nos scripts de inicialização:
- **Zero conexões externas** durante geração e transcrição
- Modelos baixam **uma vez** na primeira execução
- Inferência 100% na sua RTX 4080

Guard em `tests/test_empacotamento.py` impede regressão.

---

## Custos

| item | custo |
|---|---|
| Inferência | **R$ 0,00** (seu hardware) |
| Eletricidade | sua conta |
| Modelos | baixam uma vez |
| Hospedagem online com GPU | **não é grátis**: HF Spaces free é só CPU; ZeroGPU exige Space público e tem quota; Oracle Free Tier A10 instável; Vast.ai/RunPod ~$0,20–0,50/h (A10G/4080) |

---

## Licenças (resumo)

| componente | licença | implica o quê |
|---|---|---|
| **Este app** | MIT | faça o que quiser, inclusive cobrar |
| **Base VoiceStudio** | AGPL-3.0 | quem receber precisa acessar o código dela; como é pública e imutável, basta manter o aviso e o link |
| **OmniVoice** | pesos CC-BY-NC | **não pode em produto pago** |
| **VoxCPM2** | Apache-2.0 | pode comercial |
| **Qwen3-TTS** | Apache-2.0 | pode comercial |
| **Chatterbox** | MIT | pode comercial |
| **KittenTTS** | Apache-2.0 | só inglês, não clona |

O arquivo `app/licencas.py` é a fonte única; a tela lê dele. Qualquer motor sem licença confirmada aparece como "não verificada".

---

## Testes e qualidade

```
pytest -q        # 159 passed
ruff check       # All checks passed
protocolo_seguranca.py --projeto .  # 10/10 LIBERADO
```

O gate de segurança vaza:
- segredos no código/histórico
- caminhos pessoais
- dependências não declaradas
- `eval`/`exec`/`pickle`
- CORS aberto

---

## Estrutura do repositório

```
eleven-audio/
├── app/                    # backend FastAPI
│   ├── servidor.py         # cria o app, monta rotas
│   ├── rotas.py            # rotas principais (gerar, estado, motores, saúde)
│   ├── rotas_clonar.py     # clonar, perfis, qualidade, audio
│   ├── rotas_agente.py     # agente MCP
│   ├── rotas_comparar.py   # comparar motores
│   ├── rotas_desenhar.py   # desenhar voz
│   ├── rotas_transcrever.py
│   ├── preparo.py          # corta silêncio, melhor janela, normaliza
│   ├── referencia.py       # diagnóstico completo do áudio
│   ├── clonar.py           # orquestra clonagem + preparo
│   ├── ffmpeg.py           # resolve ffmpeg em 3 camadas
│   ├── licencas.py         # licença verificada de cada motor
│   ├── base.py             # fala com a base (padrões fiéis)
│   ├── agente.py           # serviço do agente (idempotente)
│   ├── config.py           # carregamento de config
│   └── cofre.py            # SQLite (perfis, vinculos, saídas)
├── web/                    # front puro
│   ├── index.html          # shell + navegação
│   ├── app.js              # roteador de áreas
│   ├── gerar.js            # tela Gerar
│   ├── clonar.js           # tela Clonar
│   ├── transcrever.js
│   ├── desenhar.js
│   ├── comparar.js
│   ├── agente.js
│   ├── config.js
│   ├── estilo.css / estilo-v2.css
│   └── recursos/           # ícones SVG inline
├── scripts/
│   ├── ligar-tudo.ps1      # sobe base + app (modo offline)
│   └── subir-base.ps1
├── dados/                  # SQLite + referencias (gitignored)
├── saidas/                 # áudios gerados (gitignored)
├── experimentos/           # benchmarks, Qwen3-TTS isolado
├── docs/
│   ├── REQUISITOS.md       # o que a máquina precisa (medido)
│   ├── RODA-LOCAL.md       # prova de localidade
│   ├── MODELOS-INSTALAVEIS.md
│   └── CLONAGEM-ALTO-NIVEL.md
├── tests/                  # 159 testes
└── requirements.txt
```

---

## Para quem vai receber / instalar

### Se for doar (uso pessoal, estudo, comunidade)

Já está pronto. O repo é público, MIT, sem segredos. A pessoa clona, instala o ffmpeg,
sobe a base, roda `ligar-tudo.ps1` e usa.

### Se for vender (entregar como solução)

1. **Troque o motor ativo** para VoxCPM2 ou Qwen3-TTS (OmniVoice não serve)
2. Entregue a pasta `eleven-audio/` + `voice-studio-base/` (ou o link do repo da base)
3. Inclua este arquivo (`LEIA-ME.md`) e `docs/REQUISITOS.md`
4. A base é AGPL-3.0: mantenha o aviso de licença e o link do repositório junto
5. O app é MIT: seu preço, sua marca, seu suporte

---

## Problemas conhecidos / não promessas

- **Só testado em Windows 11 + RTX 4080 + Python 3.11.** Windows 10, Linux, macOS
  não foram testados. Os scripts são PowerShell.
- **Tamanho exato dos pesos dos motores não medido.** Eles baixam na primeira execução
  para um cache gerenciado pela base; eu não localizei os arquivos para pesar.
- **O app assume ffmpeg no PATH do usuário** (WinGet/Chocolatey/Scoop). O resolvedor
  em `app/ffmpeg.py` cobre a maioria dos casos, mas se a pessoa instalar de forma
  exótica pode precisar apontar à mão.
- **VRAM compartilhada:** o Windows reserva parte da placa para o vídeo da tela, e
  navegador aberto também come. 8 GB é o piso honesto; 12 GB dá folga.
- **Histórico do GitHub tem caminhos pessoais** em commits antigos (ex.: `c5b59ad`).
  Force-push derrubaria 13 branches remotas — só com ordem do dono. O código atual
  está limpo.

---

## Armadilhas ao subir os serviços (todas medidas, não teóricas)

Cada uma destas derrubou o estúdio de verdade em 29/09/2026. Vão aqui porque nenhuma
delas aparece rodando `pytest`: a suíte não sobe serviço.

**1. O Python da base é o venv DELA.** Não use um Python do sistema nem do `uv`. O
`torch` e o `torchaudio` só existem em `<base>/.venv/Scripts/python.exe`. Com outro
Python, a base morre na largada:

```
ModuleNotFoundError: No module named 'torchaudio'
FATAL: backend startup failed during 'ml_imports'
```

**2. `.ps1` com acento precisa de BOM.** O caminho da base tem `SÉRIE · ENGENHARIA`.
O PowerShell 5.1 lê arquivo sem BOM como ANSI, e o caminho vira `S�%RIE ��`. O script
então procura uma pasta que não existe. Grave o `.ps1` em **UTF-8 com BOM**.

**3. `/health` não responde a HEAD.** Responder HEAD devolve **405**; só GET devolve
200. Um laço de espera com `-Method Head` nunca detecta a base como pronta, estoura o
tempo, e aí o script mata a base que estava funcionando. Use `-Method Get`.

**4. `$nome:` quebra o parser do PowerShell.** `"$nome: texto"` é lido como variável
com qualificador de drive e o script **não roda**. Use `"${nome}: texto"`. Dá para
conferir sem executar:

```powershell
$e = $null
[System.Management.Automation.Language.Parser]::ParseFile('arquivo.ps1', [ref]$null, [ref]$e) | Out-Null
$e | ForEach-Object { $_.Extent.StartLineNumber, $_.Message }
```

**5. PYTHONPATH de fora atrapalha, e muito.** Se o estúdio for iniciado por dentro de
outro programa que define `PYTHONPATH`, o `site-packages` desse outro sombreia o do
projeto:

```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

O app e a base têm venv próprio; os launchers zeram `PYTHONPATH` antes de subir.

**6. `.bat` não aguenta caminho com acento.** Depende da página de código do console e
o caminho quebra em silêncio. Deixe o `.bat` só chamar o `.ps1`, que é o que
`scripts/ligar-tudo.bat` faz.

**Conferência rápida depois de subir:**

```bash
curl -s http://127.0.0.1:7800/api/saude
# {"nosso_app":"ok","base":"ok","ffmpeg":"ok", ...}
```

Se o app responde mas `base` ou `ffmpeg` não estão `ok`, o problema está embaixo, não
na interface.

---

## Contato / Comunidade

- Repositório: https://github.com/gabrielkendy/eleven-audio
- Base VoiceStudio (AGPL): https://github.com/gabrielkendy/voice-studio-base
- Comunidade AI CREW: https://skool.com/ai-crew-1437

---

*Última atualização: 28/09/2026 — commit `023fa03`*
*Tudo aqui é medição desta máquina, não promessa. Onde não medi, está escrito que não medi.*