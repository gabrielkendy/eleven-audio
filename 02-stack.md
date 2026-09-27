# 02 · Stack Tecnológica

> Arquivo 2 de 10 do manual do Estúdio de Voz Local.
> Toda escolha com o motivo. Onde a versão importa, a versão está escrita. Onde não foi medida,
> está escrito "a medir".
> Padrão do kit: tabela, coluna de "por quê", e um guia de "quando usar o quê" no fim.

---

## 1. Stack da nossa camada (o que a gente escreve)

### 1.1 Backend

| Item | Tecnologia | Por quê | Versão |
|---|---|---|---|
| Linguagem | Python | é a mesma língua da base, então o ambiente, o `uv` e os pesos são compartilháveis | 3.11 ou mais novo |
| Framework web | FastAPI | async, validação automática, documentação de API de graça em `/docs`, e é o mesmo padrão da base (o aluno vê o mesmo desenho duas vezes) | a medir (última estável no dia da instalação) |
| Servidor | Uvicorn | ASGI de alta performance e subida simples | a medir |
| Cliente HTTP | httpx | cliente moderno, async, com timeout explícito por chamada | a medir |
| Banco | SQLite (biblioteca padrão) | um arquivo, zero servidor, zero senha, zero instalação. É exatamente o que uma ferramenta local pede | 3.x embutido no Python |
| Migração | alembic | já é o padrão da base, então a gente segue o mesmo caminho quando o esquema crescer | a medir |
| Validação | Pydantic v2 | schemas de entrada e saída, erro 422 automático | v2 |
| Áudio | FFmpeg (binário do sistema) | corte de clipe, conversão para opus e ogg, medição de duração | instalado pelo sistema |

### 1.2 Frontend (a tela única)

| Item | Tecnologia | Por quê |
|---|---|---|
| Linguagem | JavaScript com JSX, ou HTML e JS direto | o fluxo cabe em uma página. Se virar JSX, é pelo conforto de componente, não por necessidade |
| Framework | React 19 com Vite | build rápido, ecossistema igual ao da base, e uma tela só não precisa de mais |
| Estilo | Tailwind CSS | velocidade e consistência. Cores por variável, nunca hex solto no componente |
| Componentes | shadcn/ui (Radix) | acessível, copiado para dentro do projeto (sem dependência fechada) |
| Estado | estado local do próprio React | uma tela, poucos estados. Zustand e Redux aqui seriam cerimônia sem retorno |
| Vídeo e áudio | elemento `audio` nativo do navegador | player simples resolve. Sem biblioteca de player no primeiro dia |
| Testes | vitest para componente, e teste manual roteirizado para o fluxo | não existe suíte pesada em um produto de uma tela |

Alternativa aceitável e mais simples, se o prazo apertar: **página estática com HTML, CSS e
JavaScript puro**, servida pela própria camada fina. O contrato `/api/*` não muda, então dá para
trocar a casca depois sem tocar no miolo. Regra: o que não pode faltar é estado de carregando,
vazio e erro em cada área.

### 1.3 Ferramentas de desenvolvimento

| Item | Tecnologia | Por quê |
|---|---|---|
| Ambiente Python | uv | resolve e sincroniza dependencies rápido, e é o que a base usa (`uv.lock` no repositório) |
| Runtime JS (quando houver build) | Bun | instalado pela base, então já está na máquina |
| Editor | qualquer. Sugestão: VS Code com extensão de Python | previsível |
| Terminal | Git Bash (vem com o Git para Windows) | evita surpresa de caminho com acento e espaço |
| Versionamento | Git com repositório próprio para a nossa camada | a base tem repositório próprio e não se mistura |

---

## 2. Stack da base (o que a gente usa pronto)

| Item | Tecnologia real da base | O que a gente usa disso |
|---|---|---|
| Linguagem | Python | o mesmo ambiente roda a nossa camada |
| Framework | FastAPI, com um ponto de entrada único (`backend/main.py`) e 42 módulos de rota | chamamos os endpoints documentados |
| Banco | SQLite com migração por alembic | lemos e escrevemos via API, nunca no arquivo dela |
| App de mesa | Electron (é o único app de mesa e web da base desde a versão 0.5.3) | é a interface de referência da base. A nossa tela é separada |
| Fila de GPU | fila interna com orçamento de tempo e degradação de precisão | nos dá tempo de espera previsível para a tela |
| Servidor MCP | montado no próprio backend em `/mcp/` | é o fecho do vídeo |
| API compatível com OpenAI | `/v1/audio/speech`, `/v1/audio/transcriptions`, `/v1/audio/voices` | encaixe universal com qualquer cliente que fale esse padrão |
| Marca d'água, ditado, dublagem, lote, projetos, galeria | recursos nativos | ficam para os próximos vídeos |

Frase para o aluno: **quase todo o trabalho pesado já está pronto. O trabalho do vídeo é o fluxo.**

---

## 3. Motores de voz (a escolha que define qualidade, velocidade e memória)

| Motor | Papel no projeto | Roda em | Clonagem | Como entra | Peso |
|---|---|---|---|---|---|
| **OmniVoice** | motor padrão. Primeira geração do vídeo | CUDA, MPS e CPU | sim, referência de até 20 s (janela de 15 s com mais fala) | já vem na base | cerca de 2,3 GB de peso no primeiro uso |
| **VoxCPM2** | clonagem de mais alto nível (referência de até 30 s) e voz por descrição | CUDA, MPS e CPU | sim, com corte de silêncio e teto de 30 s | `pip install "voxcpm>=2.0.3"` no ambiente da base, ou instalação em um clique no catálogo | multi GB, exato a medir |
| **IndexTTS 2.5** | clonagem com emoção | CUDA e CPU | sim, com emoção | instalação em um clique no catálogo da base | a medir |
| **Faster-Whisper** | transcrição (o brinde do primeiro dia) | CUDA e CPU | não se aplica | já vem na base | baixa no primeiro uso |
| **WhisperX** | transcrição com tempo por palavra (legenda) | CUDA e CPU | não se aplica | já vem na base | a medir |
| **mock (nosso)** | construir a tela sem GPU e sem peso | qualquer | não | código nosso, tom de 440 Hz | zero |

Regra do clipe de referência (o que a pessoa precisa gravar):

| Situação | O que a base aceita | O que a gente recomenda na tela |
|---|---|---|
| Clipe ideal | de 5 a 15 segundos de fala limpa | 10 segundos, uma frase inteira, sem música e sem ruído |
| Teto do motor padrão | até 20 s com transcrição, janela de 15 s sem transcript | clipe de 10 a 15 s |
| Teto do VoxCPM2 | primeiros 30 s depois de cortar o silêncio | 15 a 30 s |
| Teto bruto da tela | 75 s (a base recusa acima disso) | nunca passar de 30 s: acima disso o motor corta e a transcrição deixa de casar |

---

## 4. Hardware e sistema

| Item | Mínimo | Recomendado | Medido nesta máquina |
|---|---|---|---|
| Sistema | Windows 10 versão 21H2 ou mais novo, x64 | Windows 11 x64 | a medir no dia da instalação |
| GPU | NVIDIA com driver comum (CUDA acelerado de graça) | RTX com 8 GB ou mais | RTX 4080 com 16 GB |
| VRAM para o motor padrão | piso oficial de 6 GB | 8 GB ou mais com folga para o sistema | 16 GB, bem acima do piso |
| GPU AMD no Windows | roda, mas só em CPU (sem ROCm no Windows) | não se aplica | não se aplica |
| Disco | cerca de 10 GB livres para app, ambiente e pesos | 30 GB ou mais (dois motores, dois modelos de transcrição e cache) | a medir |
| Memória RAM | 16 GB | 32 GB | a medir |
| FFmpeg | obrigatório para opus, ogg e corte de clipe | obrigatório | a confirmar na máquina |
| Rede | necessária só para baixar peso e para o primeiro setup | necessária na instalação | ok |

---

## 5. Licenças (a parte chata que evita problema)

| Componente | Licença | O que isso quer dizer na prática |
|---|---|---|
| Base VoiceStudio | AGPL-3.0 | uso local livre. Modificar e oferecer como serviço de rede obriga a publicar o código. A gente não modifica e não oferece como serviço |
| Nossa camada fina | a definir (sugestão: MIT) | como ela não embute código da base, pode ser publicada com licença própria |
| OmniVoice (motor e pacote) | própria do projeto (a confirmar na página do pacote) | ler antes de uso comercial do áudio |
| VoxCPM2 | própria do OpenBMB (a confirmar) | ler antes de uso comercial |
| IndexTTS 2.5 | própria (a confirmar) | idem |
| Faster-Whisper e WhisperX | próprias (a confirmar) | idem |
| Pesos dos modelos | licença própria, separada do código | é a licença que mais importa para quem vende áudio |
| FFmpeg | LGPL ou GPL conforme o build | usar build com licença compatível com o uso |

Regra escrita na tela do produto: **o áudio que você gera é seu, respeitando a licença do motor
usado.** Isso é a mesma distinção que o alvo faz ao vender licença comercial como item de plano, só
que aqui de graça e em texto claro.

---

## 6. Custo

| Item | Valor | Estado |
|---|---|---|
| Licença do app | zero | medido |
| Assinatura mensal | zero | medido |
| Custo por minuto gerado | zero em serviço. A energia entra na conta | medido |
| Energia por minuto de áudio | a medir (consumo da GPU em carga) | pendente |
| Disco por motor | a medir (soma de peso mais cache) | pendente |
| Custo da nuvem do alvo para comparação | de $0,17 a $0,30 por minuto extra, mais assinatura de $5 a $990 | medido em 27/09/2026 |

---

## 7. Guia "quando usar o quê" (para decidir sem pensar muito)

### 7.1 Qual motor de voz

| Situação | Motor | Motivo |
|---|---|---|
| Primeira geração, português, quer simplicidade | OmniVoice | é o padrão, tem cobertura de idioma enorme e piso de VRAM de 6 GB |
| Quer o melhor áudio e clonagem mais fiel | VoxCPM2 | 48 kHz, clonagem com referência de até 30 s |
| Quer voz por descrição em português sem clipe | VoxCPM2 | desenho de voz por descrição livre é o forte dele |
| Quer emoção na clonagem | IndexTTS 2.5 | clonagem com emoção (segunda fase) |
| Está sem GPU ou com VRAM tomada | OmniVoice em CPU, ou motor de teste | funciona, só demora |
| Está construindo tela e banco | mock | instantâneo, zero peso, zero GPU |
| Máquina com menos de 6 GB de VRAM | variante GGUF do motor padrão | mesma família de modelo com pegada de memória menor |

### 7.2 Quando trocar de banco

Fica no SQLite até doer. Motivos para migrar (e não antes): mais de uma máquina precisando do mesmo
histórico, consulta analítica pesada em milhões de linhas, ou concorrência de escrita real. Nenhum
dos três existe no recorte.

### 7.3 Quando trocar de frontend

Se a tela única passar de 4 áreas para 10, ou se surgir necessidade de app mobile, o caminho é
React com roteamento e componente reaproveitado. Antes disso, tela única é mais rápida de manter e
de gravar em vídeo.

### 7.4 Quando ir para a nuvem

Nunca no recorte. Se um dia o produto virar serviço, a conta muda: hospedagem com GPU, fila, conta
de usuário, cobrança, LGPD, e a AGPL da base passa a morder de verdade (serviço de rede com código
modificado exige publicar o código). Esse cenário é vídeo próprio, não é este.

### 7.5 Quando usar a porta compatível com OpenAI

Sempre que um cliente de terceiro precisar de voz e falar o padrão OpenAI. Exemplo: ferramenta que
já aponta para `base_url` de API de áudio. Aí a gente entrega `http://127.0.0.1:3900/v1` e o
encaixe acontece sem código novo.

---

## 8. Versões: onde conferir (para não chutar)

| O que | Onde conferir |
|---|---|
| Versão do Python da base | arquivo `.python-version` na raiz da base |
| Versões travadas do Python | `uv.lock` na raiz da base |
| Versões do JS da base | `bun.lock` e `package.json` na raiz da base |
| Motores e o que cada um pede | `docs/engines/README.md` na base |
| Teto de tempo e variáveis de ambiente | `docs/mcp.md`, `docs/api-auth.md` e as páginas de cada motor |
| Requisitos de instalação no Windows | `docs/install/windows.md` na base |
| Versão do FFmpeg instalada | comando `ffmpeg -version` no terminal |

---

## 9. Checklist de stack (20 itens)

- [ ] Python 3.11 ou mais novo instalado e visível no terminal
- [ ] `uv` instalado
- [ ] Git instalado com Git Bash disponível
- [ ] FFmpeg instalado e respondendo a `ffmpeg -version`
- [ ] Driver NVIDIA atualizado, com `nvidia-smi` funcionando
- [ ] Base clonada e ambiente dela preparado (`uv` sincronizado)
- [ ] Base no ar respondendo em `http://127.0.0.1:3900/health`
- [ ] Motor padrão instalado e com peso baixado (primeiro uso feito)
- [ ] Motor de transcrição instalado e testado
- [ ] VoxCPM2 instalado por pip ou pelo catálogo, com estado conferido em `/api/engines`
- [ ] SQLite disponível (vem com o Python)
- [ ] Pasta de dados da base fixada (recomendado `OMNIVOICE_DATA_DIR`)
- [ ] Nossa pasta `estudio\` criada com `app\`, `web\`, `dados\`, `saidas\audio\`
- [ ] Variáveis nossas definidas num arquivo de exemplo (`ESTUDIO_PORT`, `ESTUDIO_MOTOR`, `ESTUDIO_SAIDAS`)
- [ ] `.gitignore` do nosso projeto ignorando `dados\` e `saidas\`
- [ ] Nenhum peso de modelo dentro do repositório
- [ ] Nenhum segredo em arquivo (o projeto não tem segredo)
- [ ] Tela sobe em `127.0.0.1:7800` e mostra o rodapé com dados reais
- [ ] Motor de teste funcionando sem GPU
- [ ] Licenças listadas na tela de configuração, com o aviso de uso comercial
