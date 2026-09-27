# ELEVEN_AUDIO

Estúdio de voz local, sem login, sem nuvem e sem cobrança por minuto. O projeto cria uma camada fina em português sobre a API local do VoiceStudio.

## Estado atual

A FATIA 0 contém o esqueleto local: FastAPI em loopback, diagnóstico da base VoiceStudio, motor `mock` que gera WAV PCM e scripts de subida e fumaça. GERAR, clonagem, transcrição, desenho e agente continuam fora deste recorte.

## Fonte de verdade

O contrato principal está em `00-BLUEPRINT.md`. A execução prevista segue oito fatias verticais, da FATIA 0 à FATIA 7.

`05-dados.md` segue a decisão do blueprint: SQLite local em `dados/estudio.db`. A criação das sete tabelas pertence ao contrato de dados da FATIA 1 e não é antecipada aqui.

## Instalação da camada fina

```powershell
python -m pip install -r requirements.txt
```

Toda configuração usa variável de ambiente. Os padrões são `127.0.0.1:7800`, base em `http://127.0.0.1:3900`, dados em `dados/`, saídas em `saidas/audio/` e motor padrão `omnivoice`.

## Execução da FATIA 0

```powershell
$env:VOICESTUDIO_DIR = 'C:\caminho\para\4-BASE-VOICESTUDIO'
.\scripts\subir-base.ps1
```

Em outro terminal:

```powershell
.\scripts\subir-app.ps1
python scripts\fumaca.py
```

O script de fumaça consulta `/health` e `/api/saude`, gera um WAV local com o motor `mock`, reabre o arquivo e registra duração do áudio e tempo de geração. A base externa é somente leitura para este projeto. O script exige que o ambiente virtual dela já esteja preparado e não instala pesos.

## Verificação

```powershell
python -m ruff check app scripts tests
python -m pytest -q
python ferramentas\protocolo_seguranca.py --projeto .
```

## Documentação

- `00-BLUEPRINT.md`: PRD e ordem das fatias
- `01-arquitetura.md`: arquitetura e fronteiras
- `02-stack.md`: tecnologias, motores e licenças
- `03-backend.md`: contrato e estrutura do backend
- `04-frontend.md`: tela, componentes e estados
- `05-dados.md`: contrato de persistência local em SQLite
- `06-seguranca.md`: segurança local e consentimento
- `07-integracoes.md`: motores, MCP, FFmpeg e mock
- `08-deploy-local.md`: instalação e operação no Windows
- `09-metodo-de-construcao.md`: método por fatias
- `10-checklist.md`: critérios finais e armadilhas
- `ferramentas/protocolo_seguranca.py`: verificação das invariantes de segurança

## Regra de execução

Cada tarefa do Linear deve começar com `[ELEVEN_AUDIO] - FATIA N -`. Nenhuma fatia começa antes de a anterior cumprir seu critério de pronto.
