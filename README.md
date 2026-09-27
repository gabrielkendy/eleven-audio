# ELEVEN_AUDIO · Estúdio de Voz Local

Estúdio de voz que roda na sua máquina. Sem login, sem nuvem e sem cobrança por minuto. Seus áudios não saem do seu computador.

O projeto é uma camada fina em português sobre uma base de síntese de voz local. Ele adiciona a tela, a clonagem com consentimento, o histórico, a transcrição e um adaptador para outros motores, tudo em Python puro e HTML sem build.

## O que dá para fazer

| Área | O que faz |
|---|---|
| **Gerar** | Escreve o texto, escolhe a voz e o motor, gera o áudio e baixa o WAV |
| **Clonar** | Sobe ou grava uma amostra de 5 a 30 s, registra o consentimento e cria um perfil de voz |
| **Comparar motores** | Gera o mesmo texto em dois motores com a mesma voz, lado a lado |
| **Desenhar voz** | Cria uma voz nova a partir de uma descrição em texto |
| **Transcrever** | Transcreve áudio ou vídeo local |
| **Agente** | Liga a voz clonada a agentes que falam por MCP |
| **Configuração** | Mostra motor ativo, dispositivos, pastas e licenças em uso |

## Como funciona

```
┌──────────────────────────┐        HTTP        ┌──────────────────────────┐
│  ELEVEN_AUDIO            │  ───────────────▶  │  Base de voz local       │
│  127.0.0.1:7800          │                    │  127.0.0.1:3900          │
│  tela + rotas + SQLite   │                    │  motores de síntese      │
└──────────────────────────┘                    └──────────────────────────┘
        │
        └── dados/estudio.db  e  saidas/audio/AAAA-MM-DD/  (só na sua máquina)
```

Dois servidores em loopback. O estúdio guarda perfis, consentimentos e o histórico de geração em SQLite local. O áudio é sempre gravado em arquivo, nunca dentro do banco.

Importante: a base **não acompanha este repositório**. Ela é um projeto separado e mantém a própria licença. O estúdio apenas conversa com ela pela porta 3900.

## Requisitos

- Windows 10 ou 11 (os scripts de subida são PowerShell)
- Python 3.11 ou superior
- Uma base de síntese de voz local rodando em `127.0.0.1:3900`
- GPU NVIDIA é opcional, mas deixa a geração muito mais rápida

## Instalação

```powershell
git clone https://github.com/gabrielkendy/eleven-audio.git
cd eleven-audio
python -m venv C:\caminho\para\o-venv-do-projeto
C:\caminho\para\o-venv-do-projeto\Scripts\python.exe -m pip install -r requirements.txt
```

## Configuração

Toda a configuração vem de variável de ambiente, com padrões que funcionam sem nenhum ajuste:

| Variável | Padrão | Para que serve |
|---|---|---|
| `ESTUDIO_PORT` | `7800` | Porta do estúdio |
| `ESTUDIO_BASE_URL` | `http://127.0.0.1:3900` | Endereço da base de voz |
| `ESTUDIO_DADOS` | `dados` | Onde ficam o SQLite e as referências de voz |
| `ESTUDIO_SAIDAS` | `saidas/audio` | Onde os áudios gerados são gravados |
| `ESTUDIO_MOTOR` | `omnivoice` | Motor padrão |
| `ESTUDIO_TIMEOUT_S` | `1800` | Tempo máximo de cada geração, em segundos |
| `VOICESTUDIO_DIR` | vazio | Pasta da base, usada pelos scripts de subida |
| `ESTUDIO_PYTHON` | vazio | Python do projeto, usado pelos scripts de subida |

Se preferir, crie `scripts/local.ps1` com os seus caminhos. Ele é carregado na hora e está no `.gitignore`:

```powershell
$VoiceStudioPadrao = 'C:\sua\pasta\da\base'
$PythonProjetoPadrao = 'C:\seu\venv\Scripts\python.exe'
```

## Como usar

Ligue tudo com um duplo clique em `scripts/ligar-tudo.bat`. Ele sobe o que estiver faltando e abre o navegador em `http://127.0.0.1:7800`. Deixe a janela aberta enquanto usa.

Para subir só o estúdio:

```powershell
python -m uvicorn app.servidor:app --host 127.0.0.1 --port 7800
```

### Clonagem de voz

Clonar exige consentimento registrado. O estúdio recusa a operação sem o aceite, e guarda junto do perfil o texto aceito, a origem da voz e o áudio da referência. A amostra precisa ter de 5 a 30 segundos, uma voz só e sem música. Use apenas a sua voz ou uma voz que você tenha autorização para clonar.

## Verificação

```powershell
python -m pytest -q
python -m ruff check app tests scripts ferramentas
python ferramentas\protocolo_seguranca.py --projeto .
```

O `protocolo_seguranca.py` é um gate, não um selo. Ele verifica doze invariantes
do projeto, como servidor só em loopback, consentimento bloqueando a geração no
servidor e nenhum segredo no código. Sai com código de erro quando uma delas é
violada. Ele não prova que o app é seguro: prova que essas invariantes foram
checadas nesta versão.

Estado atual: 131 testes passando, `ruff` limpo e gate liberado.

## Estrutura

```
app/                rotas FastAPI, integração com a base, SQLite e regras
web/                tela em HTML, CSS e JavaScript puro (sem build)
tests/              suíte de testes
scripts/            subida dos servidores e verificação ponta a ponta
ferramentas/        protocolo de segurança do projeto
experimentos/       motores em avaliação, isolados do app
docs/               notas de engenharia
00-BLUEPRINT.md     PRD e ordem das fatias
01-arquitetura.md   arquitetura e fronteiras
02-stack.md         tecnologias, motores e licenças
03-backend.md       contrato e estrutura do backend
04-frontend.md      tela, componentes e estados
05-dados.md         contrato de persistência local
06-seguranca.md     segurança local e consentimento
07-integracoes.md   motores, MCP, FFmpeg
08-deploy-local.md  instalação e operação no Windows
09-metodo-de-construcao.md   método por fatias
10-checklist.md     critérios finais e armadilhas
```

## Contribuindo

Contribuição é bem-vinda. O caminho mais curto:

1. Abra uma issue descrevendo o problema ou a ideia antes de escrever código grande.
2. Faça um fork, crie uma branch com nome curto (`fix/titulo-da-correcao`).
3. Rode `pytest -q`, `ruff check app tests scripts ferramentas` e o protocolo de segurança antes de abrir o pull request.
4. No pull request, diga o que mudou, por que mudou e o que você rodou para provar.

Duas regras do projeto que não são negociáveis:

- **A base de voz roda em modo somente leitura.** Nenhuma alteração nela. Adaptações ficam neste repositório.
- **Nada de otimizar no escuro.** Tempo de geração é sempre medido, nunca estimado, e nenhum número que aparece na tela pode ser inventado.

Um bom pull request aqui é pequeno, tem teste e explica o motivo. Um número sem medição por trás não passa.

## Segurança e privacidade

- Nenhuma chave de API é necessária. O projeto não tem credencial nenhuma.
- Tudo roda em loopback. Áudio, transcrição e perfis ficam na máquina.
- `dados/`, `saidas/` e os caches de modelo estão no `.gitignore` e nunca sobem para o repositório.
- Se você for contribuir, confira antes de commitar que nenhum arquivo seu de áudio ou de perfil entrou junto.

## Licença

MIT. Veja `LICENSE`.

A base de voz é um projeto separado, sob AGPL-3.0, e não está incluída aqui. O `LICENSE` traz a observação sobre essa relação.

Os ícones da interface vêm do Tabler Icons, sob MIT, com atribuição em `web/LICENCA-TABLER.md`. A fonte Inter é distribuída sob a SIL Open Font License.
