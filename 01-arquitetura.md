# 01 · Arquitetura

> Manual de execução do Estúdio de Voz Local. Este é o arquivo 1 de 10. Ele responde a pergunta
> "como as peças se encaixam e por quê", antes de qualquer linha de código.
> Padrão seguido: o kit de referência do método ultrassônico (arquitetura em camadas, princípios,
> fluxos, decisões com motivo), adaptado para uma solução LOCAL e SEM LOGIN.
>
> Contexto obrigatório: a base é o VoiceStudio (AGPL-3.0), clonado em
> `2-MATERIAIS-DA-SOLUCAO\4-BASE-VOICESTUDIO`. O motor de voz, a clonagem, a transcrição, a API
> local e o servidor MCP já existem lá. A gente NÃO reconstrói nada disso.

---

## 1. Visão em camadas

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ CAMADA 1 · TELA (nossa, em portugues)                                        │
│ Uma pagina, quatro areas: gerar | clonar | desenhar | transcrever            │
│ Rodape de estado: motor ativo, dispositivo, base no ar, tempo da ultima      │
│ Bloco do agente: ligar MCP, escolher voz, copiar comando pronto              │
│ Endereco: http://127.0.0.1:7800                                              │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ HTTP loopback (sem login, sem token)
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CAMADA 2 · NOSSA CAMADA FINA (o que a gente escreve)                         │
│ servidor.py   FastAPI: serve a tela e o contrato /api/*                      │
│ motor.py      adaptador: omnivoice | voxcpm2 | indextts | mock               │
│ base.py       cliente HTTP da base local                                     │
│ cofre.py      SQLite local: perfis, consentimento, geracoes, transcricoes    │
│ saidas.py     nomeacao, gravacao e leitura de saidas\audio\                  │
│ agente.py     liga MCP e faz vinculo de voz por agente                       │
│ tarefas.py    fila local: enfileira, acompanha, reporta progresso            │
└──────────┬────────────────────────────────────────────┬─────────────────────┘
           │ HTTP loopback                              │ arquivo em disco
           ▼                                            ▼
┌───────────────────────────────────────────┐  ┌──────────────────────────────┐
│ CAMADA 3 · BASE VOICESTUDIO (nao modificar)│  │ CAMADA 5 · DISCO LOCAL       │
│ backend em 127.0.0.1:3900                  │  │ saidas\audio\                │
│ /api/generate   /api/profiles              │  │ dados\estudio.db             │
│ /api/engines    /api/transcribe            │  │ dados\referencias\           │
│ /api/design/describe   /api/history        │  │ dados\logs\                  │
│ /mcp/ (servidor MCP montado no backend)    │  └──────────────────────────────┘
│ /v1/audio/speech (padrao OpenAI)           │
└──────────┬────────────────────────────────┘
           │ inferencia no dispositivo
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CAMADA 4 · MOTORES (a base orquestra, a gente so escolhe)                    │
│ OmniVoice (padrao, 24 kHz, piso de 6 GB de VRAM, referencia ate 20 s)        │
│ VoxCPM2 (48 kHz, clonagem ate 30 s, desenho de voz por descricao)            │
│ IndexTTS 2.5 (clonagem com emocao, segunda fase)                             │
│ Faster-Whisper e WhisperX (transcricao, ja instalados na base)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

Leitura do diagrama em uma frase: a tela fala com a nossa camada, a nossa camada fala com a base, a
base fala com o motor, e o motor usa a placa de vídeo. O disco guarda tudo o que importa.

---

## 2. Princípios arquiteturais (os 8 que sustentam o resto)

### 2.1 Local por desenho, não por configuração
O padrão é loopback. A base nasce sem autenticação **porque** só atende a própria máquina. A nossa
camada repete o padrão: sobe em `127.0.0.1`, não em `0.0.0.0`. Não existe caso de uso no recorte
que justifique abrir a porta para a rede, e a decisão de abrir (se um dia existir) é sempre
explícita e por sessão.

### 2.2 Camada fina que orquestra, nunca bifurca
A gente não copia nem edita o código da base. Toda comunicação é por HTTP local, que é contrato
público e documentado dela. Motivos, em ordem de peso:
1. Licença: a base é AGPL-3.0. Bifurcar e distribuir cria obrigação de publicar a modificação.
2. Manutenção: a base se atualiza rápido. Cada atualização dela viraria conflito manual na nossa
   cópia.
3. Escopo: o que faz o produto andar (motor, clonagem, fila de GPU, MCP) já está pronto. O nosso
   valor é o fluxo em português e a organização, não a inferência.

### 2.3 Adaptador de motor (trocar motor é trocar variável)
A regra de negócio chama `sintetizar(...)`. Quem decide o motor é o adaptador, por variável de
ambiente ou pela escolha da tela. Trocar OmniVoice por VoxCPM2 nunca toca em regra de negócio,
nunca toca na tela.

### 2.4 Motor de teste sempre disponível (o "mock" deste projeto)
Todo projeto tem um modo falso para construir sem depender do caro. Aqui o caro é a GPU e o peso de
2,3 GB. O motor `mock` gera um tom de 440 Hz e devolve um wav válido com a duração proporcional ao
texto. Com ele: a tela inteira, a fila, o banco, os estados de erro e a comparação de motores são
construídos e testados antes de qualquer download.

### 2.5 Artefato é arquivo em disco, sempre
Nada de guardar áudio dentro do banco. O banco guarda o registro (motor, tempo, duração, status), o
disco guarda o som. Consequências práticas: o usuário abre a pasta e vê os arquivos, o backup é
copiar a pasta, e o vídeo mostra arquivo tocando em vez de tela de app.

### 2.6 Env-driven, sem chumbado
Porta, pasta, motor padrão, endereço da base, tempo máximo de espera: tudo em variável de ambiente
com padrão sensato. Caminho absoluto dentro do código é proibido (a pasta do projeto tem acento e
espaço, então caminho chumbado quebra em outra máquina do dia para a noite).

### 2.7 Fatias verticais completas
Uma funcionalidade inteira por vez: banco, endpoint, tela, ligação e teste. Antes de ir para a
próxima, a atual precisa estar **funcionando de verdade**, com arquivo tocando no disco. O detalhe
completo está no arquivo 09 deste manual.

### 2.8 Verificar de verdade
"Deve funcionar" não existe. Toda fatia fecha com: endpoint chamado, arquivo no disco, tempo
medido, linha no banco e print (ou gravação) para o vídeo.

---

## 3. Fluxos principais (passo a passo, com quem manda o quê)

### 3.1 Fluxo de gerar áudio (o caminho mais usado)

```text
1. Pessoa escreve o texto na area GERAR e escolhe o perfil de voz e o motor.
2. A tela faz POST /api/gerar na nossa camada.
3. A nossa camada valida (texto, perfil, consentimento, motor disponivel).
4. A nossa camada grava um registro de geracao com status "na fila".
5. A nossa camada chama POST /api/generate na base, com engine e profile_id.
6. A base enfileira na fila de GPU dela, carrega o modelo se preciso e sintetiza.
7. A base devolve o audio e os metadados do render.
8. A nossa camada copia o arquivo para saidas\audio\ com nome legivel e data.
9. A nossa camada mede o tempo de parede e a duracao do audio, grava no banco.
10. A tela recebe o caminho, mostra o player e o tempo medido.
```

Detalhe de execução: a espera é longa (a fila de GPU da base tem orçamento de 1.800 s por padrão),
então a nossa camada nunca bloqueia a interface. O padrão é enfileirar, devolver um id, e a tela
consultar `/api/gerar/<id>` em intervalos curtos.

### 3.2 Fluxo de clonar voz

```text
1. Pessoa sobe um clipe de 5 a 15 segundos (ou grava na hora) e confere o aviso.
2. Pessoa escolhe a origem da voz: propria ou autorizada, e aceita.
3. A tela faz POST /api/clonar (multipart) na nossa camada.
4. A nossa camada grava o clipe em dados\referencias\ e o consentimento no banco.
5. A nossa camada corta o clipe se estiver acima do limite do motor escolhido.
6. A nossa camada chama POST /api/profiles na base com kind=clone, ref_audio e ref_text.
7. A base cria o perfil, tenta guardar a transcricao e devolve o profile_id.
8. A nossa camada chama POST /api/profiles/<id>/consent na base (consentimento nos dois lados).
9. A nossa camada espelha o perfil no nosso banco e confirma na tela.
10. Teste de aceitacao: gerar a mesma frase com a voz clonada e ouvir contra o original.
```

Detalhe que evita lentidão: se a transcrição do clipe ficar vazia no perfil, a base roda transcrição
completa em cada geração. Então o nosso fluxo **exige** transcrição do clipe na criação do perfil, e
quando a pessoa não digitar, a gente chama a transcrição uma vez e salva.

### 3.3 Fluxo de transcrição (brinde)

```text
1. Pessoa sobe audio ou video na area TRANSCREVER.
2. POST /api/transcrever na nossa camada.
3. A nossa camada chama POST /api/transcribe na base (motor de ASR escolhido).
4. A base devolve o texto (com o VAD limpando o audio antes).
5. A nossa camada grava o texto no banco e devolve para a tela.
6. Tela mostra o texto com botao copiar. Teste real: comparar com o texto que gerou o audio.
```

### 3.4 Fluxo do agente falando na voz clonada (o fecho)

```text
1. A base esta no ar e o /mcp/ esta montado (nada extra para subir).
2. Pessoa escolhe o identificador do cliente (ex.: estudio, hermes, claude-code).
3. A nossa camada chama PUT /api/mcp/bindings na base com client_id, label e profile_id.
4. A tela mostra o comando de configuracao pronto para colar no agente.
5. O agente chama generate_speech (ou clona antes, com clone_voice).
6. A base resolve a voz: profile_id explicito, depois vinculo do agente, depois padrao global.
7. Com OMNIVOICE_MCP_OUTPUT_MODE=files, o audio vira caminho no disco em vez de base64 no contexto.
8. O agente toca o arquivo ou entrega o caminho, e o arquivo aparece na pasta de saidas.
```

---

## 4. Fila, tempo e concorrência (onde mora o perigo real)

| Mecanismo | Onde vive | Valor real | O que a gente faz |
|---|---|---|---|
| Fila de GPU | base | orçamento de 1.800 s por padrão (`OMNIVOICE_GPU_QUEUE_TIMEOUT_S`) | não enfileirar duas gerações grandes ao mesmo tempo pela nossa tela |
| Tempo de geração acelerada | base | 300 s por padrão (`OMNIVOICE_GENERATE_TIMEOUT_S`) | avisar na tela e nunca tratar como travamento |
| Tempo de geração em CPU | base | 600 s por padrão (`OMNIVOICE_CPU_GENERATE_TIMEOUT_S`) | o rodapé mostra "CPU" com o motivo |
| Tempo de transcrição (arquivo) | base | 300 s por padrão (`OMNIVOICE_ASR_TRANSCRIBE_TIMEOUT_S`) | mostrar progresso por etapa |
| Tempo de transcrição (bloco de dublagem) | base | 120 s por padrão (`OMNIVOICE_TRANSCRIBE_CHUNK_TIMEOUT_S`) | não se aplica no primeiro dia |
| Fila local nossa | nossa camada | uma geração por vez na tela | serializar evita erro e evita VRAM duplicada |

Regra prática para 16 GB de VRAM: o motor padrão da base pede piso de 6 GB. Dá folga, mas não dá
para rodar dois motores grandes ao mesmo tempo, e não dá para deixar jogo ou editor de vídeo aberto
consumindo VRAM. O rodapé existe para mostrar isso antes de a pessoa culpar o app.

---

## 5. Por que esta arquitetura, e não outra

| Alternativa | Por que não |
|---|---|
| Usar só a interface da base | em inglês, sete telas, foco técnico. O produto do vídeo é o fluxo do criador em português |
| Bifurcar a base e reescrever a interface | dívida de merge eterna, peso de licença, escopo explode |
| Construir motor de voz próprio | meses de trabalho, qualidade pior, e não é o que o vídeo ensina |
| Microserviços (motor, API e tela separados em processos) | complexidade sem retorno com um usuário e uma máquina. O custo aparece no dia 1 sem benefício nenhum |
| Banco em nuvem | quebra a promessa de privacidade, que é a brecha número 2 do dossiê |
| Login e multiusuário | não existe equipe, não existe servidor, não existe a quem provar identidade |
| Fila dedicada (Redis e afins) | a fila da base já resolve, e a nossa fila é de uma pessoa |
| Guardar áudio no banco | infla backup, esconde o arquivo do usuário, e quebra a regra 2.5 |

---

## 6. Fronteiras: o que é nosso, o que é da base, o que é do motor

| Peça | Dono | A gente pode | A gente não pode |
|---|---|---|---|
| Tela e fluxo em português | nós | mudar à vontade | copiar marca e identidade visual de terceiro |
| Adaptador de motor e nossa fila | nós | mudar à vontade | inventar parâmetro que a base não aceita |
| Banco local nosso | nós | mudar à vontade | duplicar o áudio de referência em dois lugares |
| API local da base | base | chamar os endpoints documentados | contar com endpoint interno que não está na documentação |
| Servidor MCP | base | usar, vincular voz, pedir saída em arquivo | autenticar o transporte dele com coisa nossa. Ele não tem autenticação |
| Motor e pesos | terceiro | escolher, instalar, usar | redistribuir peso sem ler a licença |
| Placa e driver | sistema | detectar e reportar | exigir CUDA numa máquina AMD (no Windows a base cai para CPU) |

---

## 7. Mapa de pastas do projeto

```text
SÉRIE · ENGENHARIA REVERSA DE PRODUTO\
├── 2-MATERIAIS-DA-SOLUCAO\
│   ├── 3-AS-7-FASES-ENTREGUES\        (FASE-01 a FASE-07, este kit incluido)
│   │   ├── FASE-07-BLUEPRINT\00-BLUEPRINT.md         (o blueprint)
│   │   └── FASE-07-BLUEPRINT\            (este manual, 10 arquivos)
│   └── 4-BASE-VOICESTUDIO\            (a base, clonada, nao modificada)
└── estudio\                           (o nosso projeto, criado na FATIA 0)
    ├── app\                           (camada fina: servidor, motor, base, cofre, saidas, agente)
    ├── web\                           (a tela unica)
    ├── dados\                         (banco, referencias, logs)
    ├── saidas\audio\                  (os audios gerados)
    ├── scripts\                       (instalar, subir base, subir app, teste de fumaca)
    └── README.md                      (guia curto do aluno)
```

---

## 8. Checklist de arquitetura (20 itens)

- [ ] A nossa camada sobe em `127.0.0.1`, nunca em `0.0.0.0`
- [ ] A base não foi modificada em nenhum arquivo
- [ ] Toda chamada para a base passa por um único cliente HTTP (`base.py`)
- [ ] Todo motor é acessado por adaptador (`motor.py`), nunca direto da rota
- [ ] Existe motor de teste funcionando sem GPU
- [ ] Nenhum caminho absoluto no código
- [ ] Nenhuma porta chumbada: tudo por variável com padrão
- [ ] Nenhum segredo no código (o projeto não tem segredo)
- [ ] Toda geração grava linha no banco com tempo medido
- [ ] Todo áudio gerado cai em `saidas\audio\` com nome legível
- [ ] O áudio de referência fica em `dados\referencias\` e é apagável
- [ ] A interface nunca bloqueia esperando a GPU
- [ ] O progresso é visível por etapa (fila, carregando, sintetizando, salvando)
- [ ] O erro mostra o motivo literal vindo da base
- [ ] O rodapé mostra motor ativo, dispositivo e tempo da última geração
- [ ] A fila local serializa geração (uma por vez)
- [ ] Transcrição do clipe é exigida ou gerada na criação do perfil
- [ ] Consentimento é gravado nos dois lados antes de qualquer clonagem
- [ ] O agente fala pela voz vinculada usando `/mcp/` da base
- [ ] Backup é copiar `dados\` e `saidas\`, sem depender de banco em nuvem
