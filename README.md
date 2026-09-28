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
| **Desenhar voz** | Descrição textual → perfil (só com **VoxCPM2** ativo) | `POST /api/desenhar`, `GET /api/desenhos` |
| **Comparar** | Mesmo texto/perfil em vários motores lado a lado | `POST /api/comparar`, `GET /api/comparar/{grupo}`, `GET /api/comparar/{grupo}/audio/{id}` |
| **Agente** | Liga/desliga cliente no MCP da base (WhatsApp) | `GET /api/agente/status`, `POST /api/agente/ligar`, `POST /api/agente/desligar` |
| **Configuração** | Motor ativo, saídas, estado, limites, licenças | `GET /api/estado`, `GET /api/motores`, `POST /api/motores/ativo`, `GET /api/saidas` |

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

## Contato / Comunidade

- Repositório: https://github.com/gabrielkendy/eleven-audio
- Base VoiceStudio (AGPL): https://github.com/gabrielkendy/voice-studio-base
- Comunidade AI CREW: https://skool.com/ai-crew-1437

---

*Última atualização: 28/09/2026 — commit `023fa03`*
*Tudo aqui é medição desta máquina, não promessa. Onde não medi, está escrito que não medi.*