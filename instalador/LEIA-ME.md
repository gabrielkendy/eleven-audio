# ELEVEN AUDIO

Estúdio de voz que roda **na sua máquina**. Clonar voz, gerar fala, transcrever,
traduzir texto e **dublar áudio de um idioma para outro mantendo a sua voz**.

Nada sai do seu computador. Sem conta, sem assinatura, sem crédito, sem nuvem.

---

## O que você precisa

| | |
|---|---|
| Sistema | Windows 10 (21H2+) ou Windows 11, 64 bits |
| Disco | ~25 GB livres (a maior parte é o motor de voz) |
| Placa de vídeo | NVIDIA com ~6 GB de VRAM livres: rápido. Sem ela roda, mas devagar |
| Internet | **só para instalar.** Depois funciona desconectado |
| Conta | **nenhuma.** Não pede login em lugar nenhum |

---

## Como instalar

1. Descompacte esta pasta onde quiser (ex.: `C:\ELEVEN-AUDIO`)
2. Duplo clique em **`INSTALAR.bat`**
3. Responda **S** quando ele perguntar se pode baixar o que falta

O instalador faz cinco coisas, e mostra cada uma:

1. confere o que sua máquina já tem
2. instala o que falta (Python, Git, ffmpeg) pelo site oficial da Microsoft
3. baixa o motor de voz
4. cria os dois ambientes Python
5. deixa o atalho na Área de Trabalho

Quer só saber se sua máquina dá conta, sem instalar nada? Rode **`SO-CONFERIR.bat`**.

Se parar no meio, **rode de novo**: ele reaproveita o que já baixou.

---

## Como usar

Duplo clique no atalho **ELEVEN AUDIO** da Área de Trabalho, ou em `ABRIR.bat`.
O navegador abre sozinho em `http://127.0.0.1:7800`.

Na primeira vez que gerar áudio, ele baixa o motor do HuggingFace. **O download
retoma de onde parou**, então pode fechar e voltar depois.

Para encerrar, `FECHAR.bat`. Seus áudios continuam salvos.

### Se algo der errado

Rode **`DIAGNOSTICO.bat`**. Ele **não altera nada**: só olha a máquina e grava um
relatório na sua Área de Trabalho, que abre sozinho no Bloco de Notas. Mande esse
arquivo para quem te passou esta pasta — ele diz exatamente onde parou.

O relatório traz: versões de tudo, os Pythons da máquina (e qual foi descartado),
a placa de vídeo, o que foi instalado, o que está respondendo, os modelos já
baixados e as últimas linhas de log. **Não tem senha nem nada seu** além dos
caminhos da sua própria máquina.

### Dublar (o motivo de existir)

Na aba **Traduzir**, seção **Áudio para áudio**:

1. solte um áudio em português
2. confira **Vira: Inglês** e escolha a voz em **Na voz de**
3. deixe **Dublagem: Completa**, que mantém a trilha e respeita o tempo
4. **Dublar agora**

Sai o mesmo conteúdo em inglês, na voz que você escolheu, com a música de fundo
preservada e a fala encaixada no tempo do original.

---

## Onde ficam as coisas

| | |
|---|---|
| Seus áudios | `eleven-audio\saidas\` |
| Vozes que você clonou | `eleven-audio\dados\` |
| Trabalhos de dublagem | `%APPDATA%\OmniVoice\dub_jobs\` |
| Modelos baixados | `%USERPROFILE%\.cache\huggingface\` |

Para desinstalar: apague a pasta e as três acima. Não deixa nada no sistema.

---

## Créditos e licenças

Este projeto **não é meu sozinho**. Ele usa trabalho de terceiros, e os créditos
abaixo são obrigatórios.

### O motor de voz: VoiceStudio

O trabalho pesado (clonar voz, gerar fala, separar trilha, dublar) é feito pelo
**VoiceStudio**, projeto aberto de terceiro.

- Repositório: https://github.com/debpalash/VoiceStudio
- Licença: **AGPL-3.0**

O que isso significa na prática: o código dele continua aberto. Este app aqui
conversa com ele pela rede local (dois programas separados), sem alterar o código
dele. Se você for modificar o VoiceStudio e distribuir, a AGPL exige abrir o seu
código também.

### O modelo de voz: OmniVoice

- Modelo: https://huggingface.co/k2-fsa/OmniVoice
- **Código: Apache-2.0. Pesos do modelo: CC-BY-NC.**

**Atenção:** `CC-BY-NC` significa **NonCommercial**. Você pode usar de graça, para
você, e pode repassar de graça com os créditos. **Não pode vender** o que gerar
com este modelo, nem cobrar pelo acesso a ele.

Se o seu caso é comercial, troque o motor na tela por um dos liberados
(VoxCPM2, Qwen3-TTS ou Chatterbox) — a base já traz o catálogo.

### Transcrição e análise de voz

| componente | licença |
|---|---|
| faster-whisper (Systran) | MIT |
| speechbrain (ECAPA) | Apache-2.0 |
| demucs (separação de trilha) | MIT |

### Este adaptador

O app, a tela e o instalador: **MIT**. Use, copie, modifique, venda — sem
obrigação. Só não use o nome nem a marca do ElevenLabs, que é de outra empresa e
não tem relação com este projeto.

---

## Problemas comuns

**"a base nao respondeu em 3 minutos"**
A primeira subida carrega os modelos, e demora. Rode de novo. Se persistir, veja
`base-voicestudio\logs\`.

**"ModuleNotFoundError" em algum pacote**
Apague a pasta `.venv` dentro de `base-voicestudio` e rode o `INSTALAR.bat` de novo.

**Geração muito lenta**
Provavelmente está rodando na CPU. Confira se você tem NVIDIA com driver
atualizado. `SO-CONFERIR.bat` mostra o que ele encontrou.

**Falta um idioma na tradução**
A aba Traduzir tem a seção **Idiomas do tradutor**, que baixa o pacote que falta
sem você precisar mexer em nada por fora.

**Tradução estranha**
A tela deixa escolher quem traduz: o **modelo local** (melhor qualidade, mais
lento) ou o **Argos** (rápido, offline, às vezes erra tempo verbal). O padrão usa
o modelo local e cai no Argos se ele não estiver disponível.

---

## Sobre

Feito para doação à comunidade. Se te ajudou, ensina alguém.
