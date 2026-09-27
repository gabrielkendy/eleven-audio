# FASE 7 · PRD (o blueprint para construir o estúdio de voz local sem login)

> Este é o documento que o time de agentes de desenvolvimento segue sem precisar perguntar nada.
> Decisões fechadas, nomes reais de arquivo e de rota, critério de pronto por fatia.
> Nome de trabalho do produto: **Estúdio de Voz Local** (nome final: a decidir, e não muda nada
> aqui dentro além do título).
> O manual de execução completo, em 10 arquivos, vive na pasta irmã `FASE-07-BLUEPRINT\`. Este PRD é o
> blueprint; o manual é a mão na massa. Os dois usam o mesmo nome para as mesmas coisas.
>
> Fonte: DOSSIE.md (FASE 6) e o recorte fechado do primeiro dia. Base: VoiceStudio, repositório
> clonado em `2-MATERIAIS-DA-SOLUCAO\4-BASE-VOICESTUDIO`. Máquina alvo: Windows, RTX 4080 16 GB.

---

## 0. Resumo do build em 12 linhas

1. O produto é uma camada fina local que **orquestra** a base. Ele não constrói motor de voz.
2. Cinco fatias verticais completas: base subindo, texto vira voz, clonar voz, brindes
   (transcrição e voz por descrição), e a voz falando dentro do agente pelo MCP.
3. Sem login, sem nuvem, sem cobrança, sem multiusuário no primeiro dia.
4. Uma tela, quatro áreas (gerar, clonar, desenhar, transcrever) e um rodapé de estado.
5. Todo áudio gerado cai em `saidas\audio\` com nome legível e data.
6. Duas portas: a API local da base (`http://127.0.0.1:3900`) e o nosso app
   (`http://127.0.0.1:7800`), as duas em loopback.
7. O contrato de motor é por variável de ambiente, nunca chumbado no código.
8. A tela de motor mostra o motivo quando um motor não roda, igual a base já faz.
9. Consentimento antes de clonar, gravado no perfil, e nada de clonagem sem ele.
10. O agente recebe a voz por vínculo de cliente no servidor MCP da base, em `/mcp/`.
11. Cada fatia só é declarada pronta quando o arquivo de áudio toca no disco, com tempo medido.
12. Nada de segredo no código, nada de caminho absoluto chumbado, nada de porte de credencial para
    nuvem nenhuma.

---

## 1. Posicionamento

| Item | Decisão |
|---|---|
| Cliente exato | criador de conteúdo e produtor de áudio em volume (vídeo, aula, curso, agente) que já paga por minuto em nuvem ou já perdeu tempo regravando |
| A UMA coisa melhor que a nuvem | custo zero por minuto com privacidade estrutural: o texto e a voz não saem da máquina, e gerar mil áudios custa a luz |
| A segunda coisa | voz clonada falando dentro do agente local, sem nuvem e sem cobrança por minuto |
| O que NÃO copiar do alvo | editor completo, dublagem, música, efeito sonoro, trocador e isolador de voz, agente de telefonia, catálogo de 11.000 vozes, crédito, cadeado, assinatura, trial |
| Login | **não tem**. Local, uma máquina. Sem conta, sem nuvem, sem assinatura |
| Onde roda | Windows 10/11 x64, RTX 4080 16 GB, CUDA detectada sozinha. Fallback: CPU (lento, funcional) |
| Idioma do produto | português do Brasil em toda a interface e em todo o texto de erro |
| Licença do nosso código | a definir (sugestão: MIT para a camada fina, mantendo AGPL da base intacta) |
| Licença da base | AGPL-3.0, mantida e respeitada. Uso local e conteúdo no canal: ok. Virar serviço de rede com código modificado obriga a publicar o código |
| Licença dos modelos | própria de cada motor. Ler antes de uso comercial. Entra como aviso na tela |

### 1.1 O que fica FORA do primeiro dia (lista explícita, sem negociação)

1. Interface própria de estúdio com linha do tempo.
2. Dublagem e tradução de vídeo.
3. Audiobook, história longa e lote grande.
4. Música, efeito sonoro, isolador de ruído, trocador de voz.
5. Correção de fala (mudar texto e regenerar na mesma voz).
6. Treino de voz profissional (30+ minutos de referência).
7. Multiusuário, multitenant, conta, perfil de equipe.
8. Nuvem, servidor público, API pública, cobrança, crédito, medidor de uso.
9. App mobile.
10. Agente de telefonia.
11. Telemetria e análise de uso (fica desligado, opt in por princípio).
12. Instalador assinado e publicação em loja (o primeiro dia roda da pasta do projeto).

---

## 2. Arquitetura do build (o que a gente escreve e o que a gente usa)

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ NAVEGADOR (a nossa tela unica, em portugues)                             │
│ http://127.0.0.1:7800   gerar | clonar | desenhar | transcrever          │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │ HTTP local (loopback, sem login)
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ NOSSA CAMADA FINA (o que a gente constroi)                               │
│ app/servidor.py    FastAPI: serve a tela + /api/* em portugues           │
│ app/motor.py       adaptador de motor (omnivoice | voxcpm2 | mock)        │
│ app/base.py        cliente HTTP da base (127.0.0.1:3900)                 │
│ app/cofre.py       SQLite local (perfis, consentimento, geracoes, config) │
│ app/saidas.py      nomeacao e gravacao em saidas\audio\                  │
│ app/agente.py      liga/desliga MCP e faz o vinculo de voz por agente     │
└──────────┬──────────────────────────────────┬────────────────────────────┘
           │ HTTP loopback                    │ leitura e escrita de arquivo
           ▼                                  ▼
┌──────────────────────────────────────────┐  ┌────────────────────────────┐
│ BASE VoiceStudio (nao modificada)        │  │ DISCO LOCAL                │
│ backend em 127.0.0.1:3900                │  │ saidas\audio\              │
│ /api/generate  /api/profiles             │  │ dados\estudio.db           │
│ /api/engines   /api/transcribe           │  │ dados\referencias\         │
│ /api/design/describe                     │  │ dados\logs\                │
│ /mcp/  (servidor MCP montado)            │  └────────────────────────────┘
└──────────┬───────────────────────────────┘
           │ inferencia
           ▼
┌──────────────────────────────────────────┐
│ MOTORES (o que a base orquestra)         │
│ OmniVoice (padrao, 24 kHz, 6 GB+)        │
│ VoxCPM2 (48 kHz, clonagem ate 30 s)      │
│ IndexTTS 2.5 (segunda fase)              │
│ Faster-Whisper e WhisperX (transcricao)  │
└──────────────────────────────────────────┘
```

Regra de arquitetura número 1: **a gente não bifurca a base.**
Motivo: AGPL exige publicar modificação quando o software vira serviço de rede, e bifurcar
transforma cada atualização da base em trabalho manual. A camada fina fala com a base pela API
local, que é contrato público e documentado dela.

Regra número 2: **a camada fina é descartável e testável sozinha.**
Ela pode rodar com motor de teste (mock) para a interface ser construída e demonstrada antes de
qualquer download de peso.

Regra número 3: **todo artefato é arquivo em disco.**
Nada de áudio guardado dentro do banco. O banco guarda o registro; o disco guarda o som.

### 2.1 Decisão de arquitetura: por que camada fina e não usar a interface da base

| Opção | Prós | Contras | Decisão |
|---|---|---|---|
| Usar só a interface da base | zero código nosso, tudo pronto | em inglês, sete telas, foco técnico, sem fluxo de criador | não |
| Forkar a base e mudar a interface | controle total | dívida de merge a cada atualização, risco de licença, escopo explode | não |
| Camada fina em português sobre a API local | escopo pequeno, testável, mantém a base atualizável, interface nossa | exige entender a API local | **sim** |

---

## 3. Entidades (o dono do dado é sempre o usuário local)

Sem multitenant. Sem coluna de inquilino. O "dono do dado" é a pessoa que roda o app, o banco é um
arquivo SQLite no disco dela, e a única fronteira real é a pasta de dados.

### 3.1 Entidades do nosso banco (`dados\estudio.db`)

| Entidade | Campo | Tipo | Obrigatório | Dono do dado | Observação |
|---|---|---|---|---|---|
| perfil_voz | id | texto (uuid curto) | sim | usuário local | chave primária |
| perfil_voz | nome | texto (1 a 60) | sim | usuário local | nome que aparece na tela |
| perfil_voz | origem | texto (`clonado` ou `desenhado`) | sim | usuário local | espelha o `kind` da base |
| perfil_voz | id_na_base | texto | sim | usuário local | `profile_id` devolvido pela base |
| perfil_voz | arquivo_referencia | texto (caminho relativo) | sim para clonado | usuário local | clipe de 5 a 15 s, formato wav |
| perfil_voz | transcricao_referencia | texto | sim para clonado | usuário local | evita transcrição a cada geração |
| perfil_voz | descricao_desenho | texto | sim para desenhado | usuário local | descrição usada no desenho |
| perfil_voz | idioma | texto (padrão `pt`) | sim | usuário local | idioma de saída |
| perfil_voz | criado_em | data e hora (ISO) | sim | usuário local | |
| perfil_voz | observacao | texto | não | usuário local | campo livre da pessoa |
| consentimento | id | texto | sim | usuário local | um por perfil |
| consentimento | perfil_id | texto | sim | usuário local | referencia perfil_voz |
| consentimento | texto_aceito | texto | sim | usuário local | cópia literal do aviso mostrado |
| consentimento | aceito_em | data e hora | sim | usuário local | prova de quando aceitou |
| consentimento | origem_voz | texto (`propria` ou `autorizada`) | sim | usuário local | o que a pessoa declarou |
| geracao | id | texto | sim | usuário local | chave primária |
| geracao | perfil_id | texto | não | usuário local | vazio quando usa voz padrão |
| geracao | motor | texto (`omnivoice`, `voxcpm2`, `indextts`, `mock`) | sim | usuário local | qual motor gerou |
| geracao | texto_entrada | texto | sim | usuário local | guardado para reprocessar |
| geracao | arquivo_saida | texto (caminho relativo) | sim | usuário local | em `saidas\audio\` |
| geracao | duracao_audio_s | número (segundos) | sim | usuário local | medido do arquivo, não estimado |
| geracao | duracao_geracao_s | número (segundos) | sim | usuário local | tempo real de parede, medido |
| geracao | dispositivo | texto (`cuda` ou `cpu`) | sim | usuário local | onde rodou |
| geracao | tamanho_bytes | inteiro | sim | usuário local | tamanho do arquivo |
| geracao | criado_em | data e hora | sim | usuário local | |
| geracao | status | texto (`ok`, `erro`) | sim | usuário local | |
| geracao | erro | texto | não | usuário local | mensagem literal do erro |
| transcricao | id | texto | sim | usuário local | chave primária |
| transcricao | arquivo_entrada | texto | sim | usuário local | áudio ou vídeo transcrito |
| transcricao | motor | texto (`faster-whisper`, `whisperx`) | sim | usuário local | |
| transcricao | texto_saida | texto | sim | usuário local | |
| transcricao | idioma_detectado | texto | não | usuário local | quando o motor informa |
| transcricao | criado_em | data e hora | sim | usuário local | |
| vinculo_agente | id | texto | sim | usuário local | chave primária |
| vinculo_agente | cliente_id | texto (ex.: `hermes`, `claude-code`) | sim | usuário local | identificador do agente |
| vinculo_agente | perfil_id | texto | sim | usuário local | voz que o agente usa |
| vinculo_agente | criado_em | data e hora | sim | usuário local | |
| configuracao | chave | texto | sim | usuário local | chave primária |
| configuracao | valor | texto | sim | usuário local | valor serializado |
| configuracao | atualizado_em | data e hora | sim | usuário local | |
| evento | id | texto | sim | usuário local | log de auditoria local |
| evento | tipo | texto | sim | usuário local | `gerar`, `clonar`, `transcrever`, `erro` |
| evento | detalhe | texto | sim | usuário local | o que aconteceu |
| evento | criado_em | data e hora | sim | usuário local | |

### 3.2 Entidades da base que a gente lê e escreve (contrato de terceiro, não é nosso)

| Entidade da base | Onde vive | O que a gente faz | Cuidado |
|---|---|---|---|
| Perfil de voz (`profiles`) | SQLite da base, mais arquivos em `VOICES_DIR` | cria, lê, lista, apaga (via API) | a base guarda o áudio de referência e a transcrição. Não duplicar por conta própria |
| Histórico de geração (`history`) | SQLite da base | lê o que foi gerado | o arquivo em disco é a fonte da verdade para o nosso registro |
| Configuração de motor | base (catalog + env) | escolhe motor por requisição com o campo `engine` | a variável de ambiente da base manda mais que a escolha da tela |
| Vínculo de agente (`mcp/bindings`) | base | cria e remove vínculo | a base é a autoridade sobre o vínculo deles. Nosso espelho é só registro |
| Consentimento de perfil | base (`POST /api/profiles/<id>/consent`) | marca consentimento no perfil | manter o nosso registro também, para relatório do canal e do vídeo |

---

## 4. Endpoints

Dois blocos. Primeiro o que a gente **consome** da base (contrato real, levantado no código em
27/09/2026). Depois o que a gente **expõe** na nossa camada fina, que é o contrato da nossa tela.

### 4.1 Endpoints da base que a gente consome

| # | Método | Rota | O que envia | O que responde | Papel mínimo | Observações reais |
|---|---|---|---|---|---|---|
| B1 | GET | `/health` | nada | estado do backend | loopback | usado para esperar a base subir |
| B2 | GET | `/api/engines` | nada | lista de motores, com `max_ref_seconds` e `ref_strategy` | loopback | é a fonte do seletor de motor |
| B3 | GET | `/api/engines/tts` | nada | motores de voz | loopback | idem, filtrado para voz |
| B4 | GET | `/api/engines/asr` | nada | motores de transcrição | loopback | idem, para transcrição |
| B5 | POST | `/api/generate` | form: `text`, `profile_id` ou `ref_audio` + `ref_text`, `engine`, `language`, `instruct`, `speed`, `seed`, `effect_preset`, `max_chunk_chars`, `stream` | áudio e metadados da geração | loopback | `guidance_scale` padrão 2.0; `denoise` padrão `true`; `effect_preset` padrão `broadcast`; `max_chunk_chars` padrão 800; texto é normalizado em NFC (correção da issue #502) |
| B6 | GET | `/api/audio/<audio_id>.wav` | nada | arquivo wav do render | loopback | o id é hexadecimal de 8 dígitos |
| B7 | GET | `/api/audio/<audio_id>.opus` e `.ogg` | nada | áudio comprimido | loopback | exige FFmpeg instalado |
| B8 | GET | `/api/history` | filtros de página | lista de gerações | loopback | espelho do histórico da base |
| B9 | GET | `/api/profiles` | nada | lista de perfis | loopback | |
| B10 | POST | `/api/profiles` | form: `name`, `kind` (`clone` ou `design`), `ref_audio`, `ref_text`, `instruct`, `language`, `seed`, `personality`, `vd_states`, `image` | `profile_id` | loopback | `kind=clone` exige `ref_audio`; `kind=design` exige `vd_states` em JSON |
| B11 | GET | `/api/profiles/<profile_id>` | nada | dados do perfil | loopback | |
| B12 | PUT | `/api/profiles/<profile_id>` | campos do perfil | perfil atualizado | loopback | usado para corrigir nome, idioma e transcrição |
| B13 | PUT | `/api/profiles/<profile_id>/audio` | novo clipe | perfil atualizado | loopback | trocar referência sem refazer clonagem |
| B14 | POST | `/api/profiles/<profile_id>/consent` | nada | consentimento gravado | loopback | é o gancho do nosso aviso obrigatório |
| B15 | DELETE | `/api/profiles/<profile_id>/consent` | nada | consentimento removido | loopback | |
| B16 | DELETE | `/api/profiles/<profile_id>` | nada | perfil apagado | loopback | apagar clipe de referência quando não usar mais |
| B17 | POST | `/api/transcribe` | áudio (e opções) | texto transcrito | loopback | usa o motor de ASR escolhido |
| B18 | POST | `/api/design/describe` | descrição da voz | atributos de desenho | loopback | ponte para o desenho de voz |
| B19 | GET | `/api/mcp/bindings` | nada | vínculos de agente | loopback | |
| B20 | PUT | `/api/mcp/bindings` | `{client_id, label, profile_id}` | vínculo gravado | loopback | é o que faz o agente falar na voz clonada |
| B21 | DELETE | `/api/mcp/bindings/<client_id>` | nada | vínculo removido | loopback | |
| B22 | POST | `/v1/audio/speech` | `model`, `voice`, `input`, `response_format` | áudio | loopback | porta compatível com o padrão OpenAI. Serve para qualquer cliente que fale esse padrão |
| B23 | POST | `/v1/audio/transcriptions` | arquivo e modelo | texto | loopback | padrão OpenAI |
| B24 | GET | `/v1/audio/voices` | nada | vozes | loopback | padrão OpenAI |
| B25 | any | `/mcp/` | JSON-RPC do protocolo MCP | respostas das ferramentas | loopback | ferramentas: `generate_speech`, `clone_voice`, `transcribe`, `list_voices`, `list_personalities`, `list_languages`, `check_health` |

Ressalvas que valem como requisito:

1. Toda chamada carrega o campo `engine` quando queremos escolher o motor por requisição. Sem ele, a
   base usa o motor selecionado nela.
2. A base pode devolver erro `[clone_ref_too_long]` quando um clipe acima de 20 s (ou acima do
   limite do motor) recebe transcrição junto. A nossa tela corta o clipe antes de enviar, então
   esse erro não deve aparecer. Se aparecer, é bug nosso.
3. A base tem orçamento de tempo por geração (fila de GPU de 1.800 s por padrão, geração acelerada
   de 300 s, geração em CPU de 600 s). A nossa tela mostra progresso e nunca "achando que travou".
4. O primeiro uso de cada motor baixa peso (OmniVoice cerca de 2,3 GB por download). A tela avisa
   antes e trata esse tempo como etapa, não como erro.

### 4.2 Endpoints da nossa camada fina (o contrato da nossa tela)

Papel mínimo em todas as rotas: quem está na máquina (loopback). Não existe papel de administrador,
não existe conta. Se um dia ligar compartilhamento de rede, o portão é o da base e o nosso app passa
a exigir o mesmo PIN (ver 06-seguranca.md do manual).

| # | Método | Rota | O que recebe | O que responde | Papel mínimo |
|---|---|---|---|---|---|
| A1 | GET | `/api/estado` | nada | versão, base no ar ou não, motores disponíveis, motor ativo, dispositivo, pasta de saídas, tempo da última geração | local |
| A2 | GET | `/api/motores` | nada | lista normalizada de motores (nome, disponível, motivo, idiomas, clonagem, limite de referência, velocidade medida) | local |
| A3 | POST | `/api/motores/ativo` | `{motor}` | motor ativo gravado | local |
| A4 | POST | `/api/gerar` | `{texto, perfil_id, motor, idioma, velocidade, semente}` | `{geracao_id, arquivo, duracao_audio_s, duracao_geracao_s, motor, dispositivo}` | local |
| A5 | GET | `/api/gerar/<geracao_id>` | nada | estado da geração (na fila, rodando, pronto, erro) | local |
| A6 | GET | `/api/saidas` | filtros (data, motor, perfil) | lista de arquivos gerados | local |
| A7 | POST | `/api/clonar` | multipart: `nome`, `arquivo_referencia`, `transcricao`, `origem_voz`, `aceite_consentimento` | `{perfil_id, id_na_base, aviso}` | local |
| A8 | GET | `/api/perfis` | nada | lista de perfis com estado de consentimento e uso | local |
| A9 | DELETE | `/api/perfis/<perfil_id>` | nada | perfil removido na base e no nosso banco | local |
| A10 | POST | `/api/desenhar` | `{descricao, texto_previa, motor}` | `{audio_url, arquivo}` | local |
| A11 | POST | `/api/transcrever` | multipart: `arquivo`, `idioma` | `{transcricao_id, texto, idioma_detectado}` | local |
| A12 | GET | `/api/agente/status` | nada | estado do MCP, vínculos ativos, clientes conectados | local |
| A13 | POST | `/api/agente/ligar` | `{cliente_id, perfil_id}` | vínculo feito e MCP confirmado | local |
| A14 | POST | `/api/agente/desligar` | `{cliente_id}` | vínculo removido | local |
| A15 | GET | `/api/config` | nada | configuração atual (sem segredo nenhum, porque não existe segredo) | local |
| A16 | POST | `/api/config` | chaves permitidas (motor padrão, pasta de saídas, pasta de dados, motor de transcrição) | configuração gravada | local |
| A17 | GET | `/api/saude` | nada | `{nosso_app: ok, base: ok ou erro, disco_livre_gb}` | local |

### 4.3 Contrato do endpoint de gerar (o mais importante, detalhado)

Requisição:

```json
{
  "texto": "Bom dia. Este audio foi gerado na tua maquina, sem nuvem e sem conta.",
  "perfil_id": "voz-gabriel-01",
  "motor": "omnivoice",
  "idioma": "pt",
  "velocidade": 1.0,
  "semente": 42
}
```

Resposta:

```json
{
  "geracao_id": "g-2026-09-27-0007",
  "arquivo": "saidas/audio/2026-09-27_143012_omnivoice_voz-gabriel-01.wav",
  "duracao_audio_s": 8.4,
  "duracao_geracao_s": 3.1,
  "motor": "omnivoice",
  "dispositivo": "cuda",
  "tamanho_bytes": 403640
}
```

Campos obrigatórios, validação e erro:

| Campo | Regra | Erro se faltar ou estiver errado |
|---|---|---|
| texto | 1 a 5.000 caracteres, sem vazio | 422 com mensagem em português |
| perfil_id | existe no nosso banco e na base, com consentimento aceito | 409 `perfil sem consentimento registrado` |
| motor | um da lista de motores disponíveis | 409 `motor indisponivel` com o motivo vindo da base |
| idioma | `pt` por padrão | 422 |
| velocidade | de 0,5 a 2,0 | 422 |
| semente | inteiro opcional, para repetir a mesma voz | n/a |

Toda geração grava linha em `geracao` e em `evento`, com tempo medido de parede (nunca estimado).

---

## 5. Telas

Uma tela só, com quatro áreas e dois blocos fixos. Nada de menu de sete itens.

### 5.1 Estrutura da tela

| Área | O que faz | Componentes | Botões e o endpoint de cada botão |
|---|---|---|---|
| GERAR | texto vira áudio | caixa de texto com contador, seletor de perfil, seletor de motor, seletor de idioma, botão gerar, player, botão abrir pasta | gerar chama `A4`; atualizar lista chama `A6`; trocar motor chama `A3` |
| CLONAR | clipe vira perfil de voz | campo de nome, entrada de arquivo ou gravação, campo de transcrição, aviso de consentimento com escolha (`própria` ou `autorizada`), botão clonar, prévia original contra prévia clonada | clonar chama `A7`; ouvir original chama o player local; ouvir clonada chama `A4` com o perfil novo |
| DESENHAR | descrição vira voz | campo de descrição, exemplos prontos, campo do texto de prévia, botão ouvir | ouvir chama `A10` |
| TRANSCREVER | áudio ou vídeo vira texto | entrada de arquivo, seletor de idioma, botão transcrever, caixa de resultado com botão copiar | transcrever chama `A11`; copiar chama a área de transferência |
| RODAPÉ DE ESTADO | mostrar a verdade da máquina | motor ativo, dispositivo (GPU ou CPU com motivo), base no ar, tempo da última geração, espaço livre | atualiza por `A1` |
| AGENTE | ligar a voz no agente | campo de identificador do cliente, seletor de perfil, botão ligar, botão desligar, lista de vínculos, comando pronto para colar | ligar chama `A13`; desligar chama `A14`; listar chama `A12` |

### 5.2 Estados obrigatórios por componente (nada de casca)

| Componente | Estados que precisam existir |
|---|---|
| Caixa de texto | vazia, escrevendo, contador, acima de 5.000 caracteres com aviso em português |
| Seletor de motor | disponível, indisponível com motivo vindo da base, peso baixando, carregando modelo |
| Botão gerar | parado, gerando com progresso, pronto, erro com mensagem literal |
| Player | parado, tocando, baixar arquivo, abrir pasta |
| Lista de perfis | vazio com chamada para clonar, um perfil, vários, perfil sem consentimento (bloqueado) |
| Aviso de consentimento | não respondido (bloqueia clonar), próprio, autorizado, revogado |
| Indicador de dispositivo | GPU ativa, CPU com motivo, fila ocupada com posição |
| Transcrição | vazia, transcrevendo, pronta, erro de formato |
| Agente | desligado, ligado com vínculo, erro de conexão do agente |

### 5.3 Texto dos avisos (copiar e colar, em português)

Aviso de consentimento da clonagem:

```text
Antes de clonar, confirme: esta voz e sua, ou voce tem autorizacao de quem e dono.
Clonar voz de terceiro sem autorizacao e ilegal e antiético.
O audio que voce gerar e seu, mas cada motor tem licenca propria. Leia antes de uso comercial.
```

Aviso de motor indisponível:

```text
Este motor nao roda nesta maquina agora.
Motivo informado pela base: <motivo literal>
Caminhos: instalar o motor, escolher outro, ou rodar em CPU (mais lento).
```

Aviso de primeiro uso (download de peso):

```text
Primeira vez com este motor: ele vai baixar o peso agora (varios GB).
Isso e download, nao travamento. Acompanhe o progresso aqui.
```

---

## 6. Integrações

| Integração | Papel | Como entra | Estado no primeiro dia | Vira real quando |
|---|---|---|---|---|
| Motor OmniVoice | motor padrão de voz e clonagem | já vem na base | real | é real desde o começo |
| Motor VoxCPM2 | clonagem de mais alto nível (até 30 s) e desenho de voz | `pip install "voxcpm>=2.0.3"` no ambiente da base | real depois da instalação, ou desligado com motivo | instalação feita e checada por `/api/engines` |
| Motor IndexTTS 2.5 | clonagem com emoção | instalação em um clique do catálogo da base | fora do primeiro dia | segunda fase |
| Faster-Whisper | transcrição (brinde) | já vem na base | real | é real desde o começo |
| WhisperX | transcrição com tempo por palavra | já vem na base | desligado no primeiro dia | vídeo de legenda |
| Servidor MCP da base | a voz dentro do agente | montado em `/mcp/` quando a base está no ar | real | é real desde o começo |
| FFmpeg | opus e ogg, corte de clipe, medição de duração | instalado no sistema | real | é real desde o começo |
| Armazenamento local | arquivos de áudio e banco | pastas do projeto | real | é real desde o começo |
| Motor de teste (mock) | construir a tela sem peso baixado | adaptador nosso que gera tom de 440 Hz | real, ligado por env | nunca vira real, é ferramenta de desenvolvimento |
| Nuvem de qualquer tipo | nada | não existe | fora | nunca no recorte |
| Cobrança | nada | não existe | fora | nunca no recorte |

### 6.1 Padrão de adaptador de motor (a regra que evita amarrar o produto)

A regra de negócio da camada fina nunca chama motor direto. Ela chama o nosso adaptador:

```python
# app/motor.py (esqueleto do padrao, nao o arquivo final)
def sintetizar(texto, perfil_id, motor=None, idioma="pt", semente=None):
    motor = motor or os.environ.get("ESTUDIO_MOTOR", "omnivoice")
    if motor == "mock":
        return _gerar_tom_de_teste(texto)          # tom 440 Hz, sem GPU
    if motor == "voxcpm2":
        return _chamar_base(engine="voxcpm2", ...)
    return _chamar_base(engine="omnivoice", ...)   # padrao
```

Trocar de motor é mudar uma variável (`ESTUDIO_MOTOR`) ou o seletor da tela. Zero mudança de regra
de negócio, zero mudança de tela.

### 6.2 Padrão mock no primeiro dia

O motor de teste existe por três motivos concretos:

1. A tela e os fluxos podem ser construídos e demonstrados **antes** de baixar 2,3 GB de peso.
2. O teste automatizado do nosso código não depende de GPU.
3. Se a máquina estiver sem GPU disponível (ou com VRAM ocupada por outro app), o produto ainda
   abre, explica e permite testar o fluxo inteiro.

Como saber se o áudio é de teste ou real: o modo mock grava no nome do arquivo a palavra `mock` e
nunca aparece como padrão. Registro obrigatório em `geracao.motor`.

---

## 7. A ordem da construção (fatias verticais completas)

Regra da série: uma fatia completa e testada antes da próxima. Nada de "todas as telas" nem "todo o
backend" separados.

### FATIA 0 · A base subindo local (esqueleto que sobe)

| Item | Definição |
|---|---|
| Entrega | base instalada e no ar em `127.0.0.1:3900`, com `/health` respondendo e um áudio de teste gerado pela própria interface da base |
| Banco | nenhum nosso ainda. A base cria o banco dela |
| Endpoints | `B1` (health) usado no nosso diagnóstico |
| Tela | nenhuma. O teste é pela interface da base |
| Teste real | `curl http://127.0.0.1:3900/health` devolve ok e o áudio de teste toca no disco |
| Pronta quando | o arquivo de áudio de teste existe e toca, e o tempo de primeira geração foi medido (download separado do tempo de GPU) |

### FATIA 1 · Texto vira voz, com escolha de motor (a fatia do vídeo)

| Item | Definição |
|---|---|
| Entrega | nossa tela em `127.0.0.1:7800` com a área GERAR funcionando, chamando a base, gravando arquivo com nome legível |
| Banco | tabelas `geracao` e `evento` |
| Endpoints | `A1`, `A2`, `A3`, `A4`, `A5`, `A6`, `A17` na nossa camada, mais `B1`, `B2`, `B5`, `B6` na base |
| Tela | área GERAR com todos os estados da seção 5.2 |
| Teste real | gerar 3 áudios com 3 motores diferentes (ou 2 motores e o de teste), ouvir os três, e medir duração de áudio e tempo de geração de cada um |
| Pronta quando | os 3 arquivos existem, tocam, e a tabela `geracao` tem a medição dos 3 |

### FATIA 2 · Clonar voz a partir de clipe de 5 a 15 segundos

| Item | Definição |
|---|---|
| Entrega | área CLONAR funcionando: subir ou gravar clipe, consentimento obrigatório, perfil criado na base e espelhado no nosso banco, geração na voz clonada |
| Banco | `perfil_voz`, `consentimento`, mais `geracao` com `perfil_id` |
| Endpoints | `A7`, `A8`, `A9` na nossa camada, mais `B9`, `B10`, `B11`, `B12`, `B13`, `B14`, `B15`, `B16` na base |
| Tela | área CLONAR com prévia original contra prévia clonada |
| Teste real | gravar um clipe de 10 segundos, clonar, gerar a mesma frase na voz clonada, ouvir as duas lado a lado |
| Pronta quando | o áudio clonado toca, o consentimento está gravado nos dois lugares, e a transcrição do clipe está salva no perfil (para não transcrever a cada geração) |

### FATIA 3 · Comparar motores com a mesma voz (a cena do vídeo)

| Item | Definição |
|---|---|
| Entrega | botão de comparar: mesma frase, mesma voz clonada, dois motores, dois arquivos, um player só com duas faixas |
| Banco | `geracao` com dois registros ligados pelo mesmo `texto_entrada` e `perfil_id` |
| Endpoints | `A4` duas vezes com `motor` diferente, `A2` para o estado de cada motor |
| Tela | modo comparação dentro da área GERAR |
| Teste real | gerar a mesma frase em OmniVoice e VoxCPM2 com a voz clonada e registrar tempo e tamanho dos dois |
| Pronta quando | os dois arquivos tocam, os tempos estão medidos, e a tela mostra os dois lado a lado |

### FATIA 4 · Transcrição (o primeiro brinde)

| Item | Definição |
|---|---|
| Entrega | área TRANSCREVER funcionando com o motor de transcrição instalado por padrão |
| Banco | tabela `transcricao` |
| Endpoints | `A11` na nossa camada, mais `B4`, `B17` na base |
| Tela | área TRANSCREVER com copiar resultado |
| Teste real | transcrever o áudio gerado na fatia 2 e comparar o texto com o que foi pedido (medir acerto) |
| Pronta quando | o texto transcrito bate com o texto gerado em pelo menos uma comparação manual registrada, e o tempo de transcrição está medido |

### FATIA 5 · Voz por descrição (o segundo brinde)

| Item | Definição |
|---|---|
| Entrega | área DESENHAR funcionando, criando voz a partir de descrição, sem clipe |
| Banco | `perfil_voz` com `origem = desenhado` e `descricao_desenho` |
| Endpoints | `A10` na nossa camada, mais `B18`, `B10` (com `kind=design`) na base |
| Tela | área DESENHAR com exemplos prontos em português |
| Teste real | desenhar duas vozes diferentes por descrição e gerar a mesma frase nas duas |
| Pronta quando | as duas vozes soam diferentes entre si e tocam no disco, e a descrição usada está gravada |

### FATIA 6 · A voz dentro do agente (o fecho do vídeo)

| Item | Definição |
|---|---|
| Entrega | agente respondendo falando na voz clonada, com vínculo por identificador de cliente |
| Banco | tabela `vinculo_agente` |
| Endpoints | `A12`, `A13`, `A14` na nossa camada, mais `B19`, `B20`, `B21` e `/mcp/` (`B25`) na base |
| Tela | bloco AGENTE com comando pronto para colar no agente |
| Teste real | pedir algo ao agente e ouvir a resposta na voz clonada, com o arquivo aparecendo na pasta de saídas |
| Pronta quando | o agente fala, o arquivo existe no disco com nome legível, e o vínculo aparece na lista |

### FATIA 7 · Fechamento (pasta organizada, medição e empacotamento)

| Item | Definição |
|---|---|
| Entrega | pasta `saidas\audio\` organizada por data, tabela de medições do vídeo, guia curto de instalação para o aluno |
| Banco | nenhuma tabela nova. Relatórios lidos das tabelas existentes |
| Endpoints | `A6`, `A16` |
| Tela | botão abrir pasta e tela de configuração simples |
| Teste real | rodar o fluxo inteiro do zero (instalar, gerar, clonar, desenhar, transcrever, agente) numa sessão só, cronometrando |
| Pronta quando | o roteiro do vídeo roda sem tocar em terminal e sem erro em pé |

---

## 8. Definição de pronto

### 8.1 Por fatia (a régua que não negocia)

- [ ] O endpoint existe, foi chamado de verdade e devolveu resposta com dado real
- [ ] O arquivo de áudio existe no disco e toca
- [ ] O nome do arquivo é legível e segue a convenção (data, motor, perfil)
- [ ] O motor usado está registrado em `geracao`
- [ ] O tempo foi medido e registrado (nunca estimado)
- [ ] A tela mostra o resultado e tem os estados de carregando, vazio e erro
- [ ] Nada de caminho absoluto chumbado no código
- [ ] Nada de segredo no código (e não existe segredo neste projeto)
- [ ] O que foi testado está escrito no relatório da fatia, com horário
- [ ] O erro, quando acontece, aparece em português com o motivo

### 8.2 Do produto (antes de gravar o vídeo)

- [ ] Fluxo inteiro roda sem terminal aberto
- [ ] Consentimento bloqueia clonagem sem aceite
- [ ] Pasta de saídas abre com um clique
- [ ] Comparação de motores funciona com áudio real dos dois
- [ ] Agente responde falando na voz clonada
- [ ] Transcrição acerta o texto gerado
- [ ] Desenho de voz produz duas vozes distintas
- [ ] Rodapé mostra dispositivo, motor ativo e tempo da última geração
- [ ] Nenhuma chamada de rede sai da máquina (conferido no monitor de rede)
- [ ] Instalação do zero documentada em uma página para o aluno
- [ ] Lista de licenças visível na tela de configuração (app, base AGPL-3.0, cada motor)
- [ ] Nada de marca, logo ou identidade visual de terceiro no produto

---

## 9. Comandos, configuração e caminhos

| Item | Decisão |
|---|---|
| Porta da base | 3900 (`OMNIVOICE_PORT`) |
| Porta do nosso app | 7800 (`ESTUDIO_PORT`) |
| Pasta de saídas | `saidas\audio\` |
| Pasta de dados nossa | `dados\` (banco `estudio.db`, `referencias\`, `logs\`) |
| Pasta de dados da base | por padrão no diretório de dados do sistema. Recomendado fixar com `OMNIVOICE_DATA_DIR` para ficar junto do projeto |
| Convenção de nome de arquivo | `AAAA-MM-DD_HHMMSS_motor_perfil.wav` |
| Motor padrão | `omnivoice` |
| Motor de teste | `mock` (tom 440 Hz, sem GPU) |
| Motor de transcrição | `faster-whisper` |
| Configuração | variável de ambiente e tabela `configuracao`. Nada chumbado |
| Segredos | não existem no recorte. Não criar nenhum |
| Log | `dados\logs\estudio-AAAA-MM-DD.log` |

Variáveis de ambiente do nosso app:

| Variável | Padrão | Para que serve |
|---|---|---|
| `ESTUDIO_PORT` | 7800 | porta da nossa tela |
| `ESTUDIO_MOTOR` | omnivoice | motor padrão |
| `ESTUDIO_MOTOR_ASR` | faster-whisper | motor de transcrição padrão |
| `ESTUDIO_SAIDAS` | `saidas\audio` | pasta dos áudios |
| `ESTUDIO_DADOS` | `dados` | pasta do banco e das referências |
| `ESTUDIO_BASE_URL` | `http://127.0.0.1:3900` | endereço da base |
| `ESTUDIO_TIMEOUT_S` | 1800 | tempo máximo de espera numa geração, casado com a fila da base |

Variáveis da base que entram no nosso roteiro (todas opcionais no loopback):

| Variável | Para que serve no nosso caso |
|---|---|
| `OMNIVOICE_DATA_DIR` | fixar onde peso, banco e cache da base ficam |
| `OMNIVOICE_TTS_BACKEND` | fixar motor de voz |
| `OMNIVOICE_ASR_BACKEND` | fixar motor de transcrição |
| `OMNIVOICE_DEVICE` | fixar dispositivo se a detecção automática errar |
| `OMNIVOICE_MCP_OUTPUT_MODE` | `files` para o áudio sair do contexto do agente e virar caminho |
| `OMNIVOICE_MCP_BASE_PATH` | fronteira de segurança de arquivo do MCP |
| `OMNIVOICE_GPU_QUEUE_TIMEOUT_S` | orçamento da fila de GPU (padrão 1800) |
| `OMNIVOICE_GENERATE_TIMEOUT_S` | orçamento de geração acelerada (padrão 300) |
| `OMNIVOICE_CPU_GENERATE_TIMEOUT_S` | orçamento de geração em CPU (padrão 600) |

Configuração do agente (exemplo real, do tipo que a tela mostra pronto para colar):

```toml
# Codex CLI, trecho de configuracao
[mcp_servers.estudio]
url = "http://127.0.0.1:3900/mcp/"
http_headers = { "X-OmniVoice-Client-Id" = "estudio" }
```

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

---

## 10. Métricas que o vídeo mede (e que a tela registra)

| Métrica | Como medir | Estado hoje |
|---|---|---|
| Tempo de 1 minuto de áudio gerado | cronômetro na geração, dividido pela duração do áudio | a medir (pendência herdada) |
| Tempo por palavra gerada (RTF) | duração de geração dividida por duração de áudio | a medir |
| Qualidade do português por motor | mesma frase nos dois motores, escuta e nota de 1 a 5 | a medir |
| Similaridade da voz clonada | comparação do áudio clonado com o clipe original | a medir (métrica ainda não escolhida) |
| Acerto da transcrição | texto transcrito contra texto gerado, contagem de erro por palavra | a medir |
| VRAM de pico | medição durante geração com o motor carregado | a medir |
| Energia por minuto de áudio | medição de consumo em carga, para a conta de custo | a medir |
| Tempo de primeira geração (com download) | separado do tempo de geração real | a medir |
| Espaço em disco por motor | soma de peso e cache de cada motor | a medir |

---

## 11. Riscos do build e mitigação

| Risco | Tamanho | Mitigação |
|---|---|---|
| Escopo estourar e nada ficar pronto | alto | fatias fechadas, cada uma com definição de pronto, e a lista do que fica fora é explícita |
| Motor de clonagem com defeito no português | alto | medir antes de prometer. Se o português não prestar, o vídeo mostra o resultado real e o caminho alternativo (motor de mais qualidade ou mais tempo de referência) |
| Peso grande nunca baixar (rede, disco) | médio | motor de teste para construir tudo, e a tela trata o download como etapa visível |
| VRAM disputada com outro app | médio | o rodapé mostra o dispositivo e o motivo. Fechar o outro app ou cair para CPU |
| Base mudar e quebrar a nossa chamada | médio | camada fina só usa endpoints documentados. Não bifurcar a base. Teste de fumaça antes de gravar |
| AGPL mal entendida e virar problema | médio | uso local e conteúdo no canal. Não virar serviço de rede. Não modificar a base |
| Clonar voz sem autorização | alto | consentimento bloqueante no app, aviso no vídeo, registro com data e hora |
| Vazar áudio de terceiro na pasta de saídas | médio | regra de apagar clipe de referência e gerar em pasta local, sem sincronização em nuvem |
| Interface própria virar um segundo produto | médio | uma tela, quatro áreas. Nada de linha do tempo, nada de editor |

---

## 12. Histórico e aprovação

| Versão | Data | O que mudou |
|---|---|---|
| 1.0 | 27/09/2026 | primeira versão, escrita a partir do dossiê da FASE 6 |
| 2.0 | esta versão | reescrita completa: entidades com dono e tipo, endpoint da base e do nosso app lado a lado, tela com botão ligado a endpoint, sete fatias com definição de pronto, métricas com estado, riscos e fora de escopo explícitos. Manual de execução em 10 arquivos na pasta `FASE-07-BLUEPRINT\` |

Aprovação para gravar: o vídeo só começa quando a lista 8.2 estiver marcada. O resto é conversa.

---

## 13. Onde está cada coisa (mapa rápido para o time)

| Preciso de | Arquivo |
|---|---|
| Visão geral do método do kit | `FASE-07-BLUEPRINT\01-arquitetura.md` |
| Stack, versões e licenças | `FASE-07-BLUEPRINT\02-stack.md` |
| Backend, endpoints e adaptador de motor | `FASE-07-BLUEPRINT\03-backend.md` |
| Tela, componentes e estados | `FASE-07-BLUEPRINT\04-frontend.md` |
| Banco local, tabelas e retenção | `FASE-07-BLUEPRINT\05-banco.md` |
| Segurança local, consentimento e licenças | `FASE-07-BLUEPRINT\06-seguranca.md` |
| Integrações, MCP e motor de teste | `FASE-07-BLUEPRINT\07-integracoes.md` |
| Instalação, atualização e recuperação | `FASE-07-BLUEPRINT\08-deploy-local.md` |
| Como construir com IA, fatia por fatia, com prompt mestre | `FASE-07-BLUEPRINT\09-metodo-de-construcao.md` |
| Checklist final e armadilhas reais | `FASE-07-BLUEPRINT\10-checklist.md` |
