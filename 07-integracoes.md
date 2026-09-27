# 07 · Integrações (motor, agente, arquivo e o motor de teste)

> Arquivo 7 de 10 do manual. Aqui estão todas as ligações do projeto com o mundo de fora, e o padrão
> que deixa cada uma testável sem depender de terceiro.
> Padrão do kit: adaptador de provedor mais modo falso (mock). Adaptação: o "provedor" aqui é o
> motor de voz local e o servidor MCP, e o mock é um motor de tom de teste.

---

## 1. Visão das integrações

| Integração | Direção | Protocolo | Endereço | Estado no primeiro dia |
|---|---|---|---|---|
| Motor de voz da base | nossa camada para a base | HTTP local | `http://127.0.0.1:3900/api/generate` | real |
| Catálogo de motores | nossa camada para a base | HTTP local | `/api/engines` | real |
| Perfis de voz | nossa camada para a base | HTTP local | `/api/profiles` | real |
| Transcrição | nossa camada para a base | HTTP local | `/api/transcribe` | real |
| Desenho de voz | nossa camada para a base | HTTP local | `/api/design/describe` | real |
| Vínculo de voz por agente | nossa camada para a base | HTTP local | `/api/mcp/bindings` | real |
| Servidor MCP (agente falando) | agente para a base | Streamable HTTP e stdio | `http://127.0.0.1:3900/mcp/` | real |
| Porta padrão OpenAI | cliente de terceiro para a base | HTTP local | `http://127.0.0.1:3900/v1` | real |
| Arquivo em disco | nossa camada para o sistema de arquivos | arquivo | `saidas\audio\` | real |
| FFmpeg | nossa camada para o binário | processo | `ffmpeg` no PATH | real |
| Motor de teste | nossa camada para ela mesma | nada | interno | real (ferramenta de desenvolvimento) |
| Nuvem, webhook, cobrança, telefonia | não existe | n/a | n/a | fora do recorte |

---

## 2. Adaptador de motor (o padrão que evita amarrar o produto)

### 2.1 A regra

A regra de negócio chama `sintetizar(...)`. Quem escolhe o motor é o adaptador, por variável de
ambiente ou pela escolha da tela. Nenhuma rota conhece `omnivoice` ou `voxcpm2` pelo nome.

```python
MOTORES = {
    "omnivoice": {"rotulo": "VoiceStudio (padrao)", "clonagem": True, "ref_max_s": 20},
    "voxcpm2":   {"rotulo": "VoxCPM2 (qualidade)",  "clonagem": True, "ref_max_s": 30},
    "indextts":  {"rotulo": "IndexTTS 2.5 (emocao)", "clonagem": True, "ref_max_s": 15},
    "mock":      {"rotulo": "Motor de teste",        "clonagem": False, "ref_max_s": 0},
}
```

### 2.2 O que cada motor entrega, na prática

| Motor | Força | Fraqueza | Quando usar |
|---|---|---|---|
| OmniVoice | cobertura de idioma enorme, piso de VRAM de 6 GB, já vem pronto | 24 kHz, e janela de referência de 15 s | padrão do dia a dia |
| VoxCPM2 | 48 kHz, clonagem com referência de até 30 s, desenho de voz por descrição | mais lento, 30 idiomas | quando a qualidade importa |
| IndexTTS 2.5 | clonagem com emoção | instalação separada, segunda fase | depois do primeiro dia |
| mock | instantâneo, sem GPU, sem peso | não é voz | construir tela, testar fluxo, demonstrar sem máquina boa |

### 2.3 Escolha por requisição contra escolha por ambiente

| Forma | Como | Quando usar |
|---|---|---|
| Por requisição | campo `engine` na chamada de gerar | comparação de motores na tela (a cena do vídeo) |
| Por ambiente | `OMNIVOICE_TTS_BACKEND` na base, `ESTUDIO_MOTOR` na nossa camada | operação normal, um motor só |
| Por perfil | `profile_id` resolve a voz, não o motor | quando a voz clonada é a mesma e o motor muda |

Atenção real: na base, a variável de ambiente vence a escolha feita na interface dela. Se um motor
não muda de jeito nenhum, é variável de ambiente mandando. Está escrito na documentação de motores
da base, e vale conferir antes de acusar bug.

---

## 3. Servidor MCP (a voz dentro do agente)

| Item | Valor real |
|---|---|
| Onde é montado | no próprio backend da base, em `/mcp/`. Não tem processo extra |
| Endereço local | `http://localhost:3900/mcp/` (manter a barra no fim) |
| Ferramentas | `generate_speech`, `clone_voice`, `transcribe`, `list_voices`, `list_personalities`, `list_languages`, `check_health` |
| Voz por agente | cabeçalho `X-OmniVoice-Client-Id` |
| Precedência de voz | `profile_id` explícito, depois vínculo do agente, depois voz padrão global, depois voz padrão do produto |
| Modo de saída | `OMNIVOICE_MCP_OUTPUT_MODE` = `resources` (padrão), `files`, `both` |
| Fronteira de arquivo | `OMNIVOICE_MCP_BASE_PATH`. Fora dela, caminho é recusado com motivo |
| Tempo limite | `OMNIVOICE_MCP_TIMEOUT_S` (sem definir, segue o backend) |
| Desligar | `OMNIVOICE_MCP_DISABLE=1` |
| Host permitido | `OMNIVOICE_MCP_ALLOWED_HOSTS` para hostname, container ou proxy |
| Autenticação do transporte | nenhuma. Não expor na internet |

### 3.1 Modo de saída: por que `files` é o modo do nosso vídeo

Um agente de IA paga por byte que entra no contexto dele, e um wav em base64 é muito byte. Em
`resources`, o áudio volta embutido. Em `files`, volta caminho e URL, e o agente entrega o caminho
para um player ou para outro programa. Em `both`, volta tudo (e o embutido é sempre wav).

```bash
# recomendacao do nosso roteiro (na base, antes de subir)
export OMNIVOICE_MCP_OUTPUT_MODE=files
export OMNIVOICE_MCP_BASE_PATH="C:\Users\Gabriel\Downloads\YOUTUBE KENDY\02-EM-PRODUCAO\SÉRIE · ENGENHARIA REVERSA DE PRODUTO\estudio\saidas\audio"
```

Ajuste fino: o caminho base precisa ser visível para a base e para o agente. Se os dois rodam no
mesmo Windows, é o mesmo caminho. O caminho com acento e espaço precisa de aspas.

### 3.2 Configuração do agente (três formatos reais)

Codex CLI (Streamable HTTP direto):

```toml
[mcp_servers.estudio]
url = "http://127.0.0.1:3900/mcp/"
http_headers = { "X-OmniVoice-Client-Id" = "estudio" }
```

Claude Code (arquivo `.mcp.json` na pasta do projeto, com client id):

```json
{
  "mcpServers": {
    "estudio": {
      "type": "http",
      "url": "http://127.0.0.1:3900/mcp/",
      "headers": { "X-OmniVoice-Client-Id": "claude-code" }
    }
  }
}
```

Cliente que só fala stdio (usa o adaptador que vem na base):

```json
{
  "mcpServers": {
    "estudio": {
      "command": "python",
      "args": ["-m", "backend.mcp_shim"],
      "cwd": "C:\\caminho\\para\\4-BASE-VOICESTUDIO",
      "env": { "OMNIVOICE_PORT": "3900", "OMNIVOICE_CLIENT_ID": "estudio" }
    }
  }
}
```

Observação real do adaptador stdio: ele precisa do código-fonte da base (roda com o ambiente Python
daquela pasta), espera a base subir, retransmite o protocolo e fecha limpo quando o cliente sai.

### 3.3 Vínculo de voz por agente (o que faz o agente falar na voz clonada)

```bash
# lista os vinculos
curl http://127.0.0.1:3900/api/mcp/bindings

# liga o cliente "estudio" na voz clonada
curl -X PUT http://127.0.0.1:3900/api/mcp/bindings \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"estudio\",\"label\":\"Estudio\",\"profile_id\":\"<id-do-perfil>\"}"

# desliga
curl -X DELETE http://127.0.0.1:3900/api/mcp/bindings/estudio
```

Fluxo completo do agente falando: o agente lista vozes, o vínculo resolve a voz, o agente pede
`generate_speech`, a base sintetiza e devolve caminho, o agente toca ou entrega o arquivo.

---

## 4. Porta compatível com OpenAI (o encaixe universal)

A base expõe, em `/v1`, o mesmo formato da API de áudio do padrão OpenAI:

| Rota | Para que |
|---|---|
| `POST /v1/audio/speech` | texto para áudio |
| `POST /v1/audio/transcriptions` | áudio para texto |
| `POST /v1/audio/translations` | áudio para texto em outro idioma |
| `GET /v1/models` e `/v1/models/{id}` | lista de modelos |
| `GET /v1/audio/voices` | lista de vozes |

Exemplo real de uso (qualquer cliente que fale esse padrão aponta para cá):

```python
from openai import OpenAI

cliente = OpenAI(base_url="http://127.0.0.1:3900/v1", api_key="local")
audio = cliente.audio.speech.create(
    model="tts-1", voice="alloy",
    input="Teste da porta compativel, rodando local.",
    response_format="wav",
)
audio.write_to_file("saidas/audio/teste_compat.wav")
```

Nota de segurança real da base: em loopback, qualquer string serve como chave. A chave só passa a
importar quando o backend aceita tráfego de fora do loopback.

---

## 5. Motor de teste (o padrão "mock-first" deste projeto)

| Pergunta | Resposta |
|---|---|
| O que ele faz | gera um wav válido com tom de 440 Hz, com duração proporcional ao texto |
| Para que serve | construir tela, fila, banco, estados e testes sem GPU e sem peso |
| Como se identifica | o nome do arquivo termina com `_mock_<perfil>.wav` e o registro grava motor `mock` |
| Como liga | `ESTUDIO_MOTOR=mock` ou escolha na tela |
| Como vira real | trocando a variável ou o seletor. Nenhuma linha de regra de negócio muda |
| O que nunca acontece | mock como padrão silencioso. Se aparecer, é escolha explícita e aparece na tela |

Regra de honestidade que entra no vídeo: **mock não é voz.** Ele existe para o fluxo andar. Nenhum
número de qualidade sai de mock.

---

## 6. FFmpeg e arquivos (as integrações silenciosas)

| Necessidade | Ferramenta | Comando de referência |
|---|---|---|
| Medir duração de um áudio | ffprobe | `ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 arquivo.wav` |
| Cortar clipe de referência | ffmpeg | `ffmpeg -y -i clipe.wav -ss 0 -t 15 -ac 1 -ar 24000 curto.wav` |
| Converter para ogg com opus | ffmpeg | `ffmpeg -y -i audio.wav -c:a libopus audio.ogg` |
| Remover silêncio das pontas | ffmpeg com filtro de silêncio | usar o que a base já faz na preparação do clipe do VoxCPM2 |
| Conferir se o arquivo toca | player do sistema | abrir a pasta e dar play |

Política de arquivo (nome legível e sem acento):

```text
saidas\audio\2026-09-27_143012_omnivoice_voz-gabriel-01.wav
                data      hora   motor      perfil
```

---

## 7. Integrações que ficam de fora do primeiro dia (com o motivo)

| Integração | Existe na base? | Por que fica fora |
|---|---|---|
| n8n e automação | sim, documentada | segundo vídeo. O valor do primeiro dia é o fluxo direto |
| Twilio e telefonia | sim, documentada | é outro produto, com regulação e custo |
| Worker remoto (GPU em outra máquina) | sim | complexidade de rede sem necessidade com uma RTX 4080 na mesa |
| Docker | sim | o recorte é máquina do criador. Docker é assunto de servidor |
| Dublagem e tradução | sim | segundo vídeo da série |
| Integração com editor de vídeo | não direto | dá para fazer por arquivo: gerar wav e importar no editor |

---

## 8. Falha graciosa (o que a nossa camada faz quando o outro lado não responde)

| Situação | Sintoma | O que a nossa camada faz |
|---|---|---|
| Base não está no ar | conexão recusada | mostra "base fora do ar", com o comando para subir, e mantém a tela viva |
| Motor indisponível | erro da base com motivo | mostra o motivo literal e sugere instalar ou trocar |
| Peso não baixado | primeira chamada lenta | trata como etapa "baixando peso" e não como erro |
| Tempo estourado | erro de orçamento de tempo | explica o teto e sugere motor mais leve, texto menor ou CPU |
| VRAM insuficiente | erro de memória | sugere fechar outro app, usar motor mais leve ou GGUF |
| FFmpeg ausente | erro só em ogg e opus | mantém wav funcionando e avisa o que instalar |
| Arquivo de saída ausente | registro aponta para arquivo que não existe | marca como `arquivo_ausente` e não quebra a lista |
| Agente não vê o MCP | vínculo não aparece do lado do agente | mostra o comando pronto para colar e testa `/mcp/` com uma chamada simples |

---

## 9. Verificação de cada integração (o teste que prova que está ligada)

| Integração | Teste de aceitação |
|---|---|
| Motor de voz | gerar a mesma frase em dois motores e ouvir os dois arquivos |
| Catálogo de motores | abrir `/api/engines` e ver pelo menos o motor padrão disponível |
| Clonagem | clonar de um clipe de 10 s e gerar a mesma frase na voz clonada |
| Transcrição | transcrever o áudio gerado e comparar com o texto original |
| Desenho de voz | desenhar duas descrições diferentes e ouvir duas vozes diferentes |
| MCP | pedir algo ao agente e ouvir a resposta, com arquivo novo na pasta |
| Vínculo de agente | listar `/api/mcp/bindings` e ver o cliente ligado na voz certa |
| Porta OpenAI | chamar `/v1/audio/speech` e receber arquivo que toca |
| FFmpeg | gerar um `.ogg` e abrir |
| Arquivo em disco | abrir a pasta e encontrar o arquivo com nome legível e data |

Regra: integração sem teste de aceitação escrito é integração que vai quebrar no dia da gravação.

---

## 10. Checklist de integrações (20 itens)

- [ ] Adaptador de motor é o único lugar que conhece nome de motor
- [ ] Motor de teste funcionando sem GPU e sem peso
- [ ] Troca de motor por variável e por seletor funcionando
- [ ] Comparação de dois motores com a mesma frase funcionando
- [ ] `/mcp/` respondendo com as sete ferramentas
- [ ] Vínculo por cliente funcionando e visível na lista
- [ ] Modo `files` ligado para o áudio não entrar no contexto do agente
- [ ] Fronteira de arquivo do MCP definida
- [ ] Comando de configuração do agente pronto para copiar na tela
- [ ] Porta `/v1/audio/speech` respondendo no padrão OpenAI
- [ ] FFmpeg instalado e usado para duração e corte
- [ ] Nome de arquivo sanitizado, com data, motor e perfil
- [ ] Erro de cada integração tratado com mensagem em português
- [ ] Base fora do ar não derruba a tela
- [ ] Primeiro uso de motor tratado como etapa de download
- [ ] Nenhuma integração de nuvem no recorte
- [ ] Nenhum webhook de terceiro
- [ ] Nenhum segredo de integração no código
- [ ] Cada integração com teste de aceitação escrito
- [ ] Teste de fumaça cobrindo base, motor, arquivo e transcrição
