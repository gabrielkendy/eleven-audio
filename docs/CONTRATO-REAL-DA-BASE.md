# Contrato real da base VoiceStudio (medido do openapi dela)

> Fonte: `GET http://127.0.0.1:3900/openapi.json` lido em 27/09/2026, com a base 0.5.6 no ar em loopback.
> 293 rotas no total. Este arquivo corrige a seção 4.1 do `00-BLUEPRINT.md`.

## Correção importante de prefixo

O PRD escreve os endpoints da base como `/api/generate`, `/api/profiles`, `/api/engines`, `/api/transcribe`
e `/api/design/describe`. **Na base real, esse prefixo `/api` não existe.** As rotas verdadeiras são
`/generate`, `/profiles`, `/engines`, `/transcribe` e `/design/describe`.

Único grupo que realmente vive sob `/api`: os vínculos do MCP (`/api/mcp/bindings`).

## Rotas que a nossa camada usa

| Uso | Método | Rota real | Corpo | Observações |
|---|---|---|---|---|
| Estado da base | GET | `/health` | nada | devolve `{"status":"ok","device":"cuda (NVIDIA GeForce RTX 4080)","version":"0.5.6"}` |
| Motores de voz | GET | `/engines/tts` | nada | lista de motores de voz |
| Motores de transcrição | GET | `/engines/asr` | nada | lista de motores de ASR |
| Selecionar motor | POST | `/engines/select` | JSON | troca o motor ativo da base |
| Gerar áudio | POST | `/generate` | **multipart/form-data** | ver campos abaixo |
| Áudio comprimido | GET | `/audio/{audio_id}.opus` e `.ogg` | nada | exige FFmpeg |
| Histórico | GET | `/history` | filtros | espelho do histórico da base |
| Listar perfis | GET | `/profiles` | nada | |
| Criar perfil | POST | `/profiles` | **multipart/form-data** | `name` é obrigatório |
| Ler perfil | GET | `/profiles/{profile_id}` | nada | |
| Editar perfil | PUT | `/profiles/{profile_id}` | JSON | |
| Trocar clipe | PUT | `/profiles/{profile_id}/audio` | multipart | troca a referência sem refazer clonagem |
| Consentimento | POST | `/profiles/{profile_id}/consent` | nada | marca consentimento na base |
| Remover consentimento | DELETE | `/profiles/{profile_id}/consent` | nada | |
| Apagar perfil | DELETE | `/profiles/{profile_id}` | nada | |
| Transcrever | POST | `/transcribe` | **multipart/form-data** | `audio` é obrigatório |
| Descrever voz | POST | `/design/describe` | **application/json** | só `{"description": "..."}` |
| Ler vínculos MCP | GET | `/api/mcp/bindings` | nada | único grupo com prefixo `/api` |
| Gravar vínculo MCP | PUT | `/api/mcp/bindings` | **application/json** | ver `_BindingBody` |
| Remover vínculo MCP | DELETE | `/api/mcp/bindings/{client_id}` | nada | |
| Padrão OpenAI | POST | `/v1/audio/speech`, `/v1/audio/transcriptions` | JSON / multipart | porta compatível com o padrão OpenAI |
| Capacidades OpenAI | GET | `/v1/audio/capabilities` | nada | |

## Campos reais do `POST /generate` (multipart/form-data)

Obrigatórios: `text`.
Opcionais: `language`, `ref_audio`, `ref_text`, `instruct`, `duration`, `num_step`, `guidance_scale` (padrão 2.0),
`speed` (padrão 1.0), `t_shift`, `denoise` (padrão true), `postprocess_output`, `layer_penalty_factor`,
`position_temperature`, `class_temperature`, `profile_id`, `seed`, `effect_preset` (padrão `broadcast`),
`engine`, `max_chunk_chars` (padrão 800), `crossfade_ms` (padrão 50), `pronounce` (padrão true), `stream` (padrão false).

Regra de motor: manda mais a variável de ambiente da base do que a escolha da tela. Para escolher por
requisição, envie o campo `engine`.

## Campos reais do `POST /profiles` (multipart/form-data)

`name` é obrigatório. Opcionais: `ref_audio`, `ref_text`, `instruct`, `language` (padrão `Auto`), `seed`,
`personality`, `kind` (padrão `clone`), `vd_states` (JSON em texto), `image`.

Regra: `kind=clone` exige `ref_audio`. `kind=design` exige `vd_states`.

## Campos reais do `POST /transcribe` (multipart/form-data)

`audio` é obrigatório. Opcionais: `language`, `model`, `mode`, `refine`.

## Campos reais do `PUT /api/mcp/bindings` (application/json)

`client_id` é obrigatório. Opcionais: `label`, `profile_id`, `default_engine`.

## Ressalvas que valem como requisito

1. A fila da GPU da base tem orçamento de tempo próprio (1800 s por padrão). Nossa tela mostra progresso e
   nunca trata espera como travamento.
2. O primeiro uso de um motor baixa peso. Tratar como etapa visível, não como erro.
3. Áudio sempre em arquivo. O banco guarda o registro, o disco guarda o som.
4. Nunca modificar arquivo da base. Todo acesso é por HTTP em loopback.
