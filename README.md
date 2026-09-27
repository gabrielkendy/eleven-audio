# ELEVEN_AUDIO

Estúdio de voz local, sem login, sem nuvem e sem cobrança por minuto. O projeto cria uma camada fina em português sobre a API local do VoiceStudio.

## Estado atual

O repositório contém somente o blueprint, o manual de construção e a ferramenta de protocolo de segurança. Nenhum código de produto foi implementado.

## Fonte de verdade

O contrato principal está em `00-BLUEPRINT.md`. A execução prevista segue oito fatias verticais, da FATIA 0 à FATIA 7.

Antes da FATIA 0, é necessário resolver uma divergência documental: `00-BLUEPRINT.md`, `01-arquitetura.md`, `02-stack.md`, `03-backend.md`, `08-deploy-local.md`, `09-metodo-de-construcao.md` e `10-checklist.md` definem SQLite, enquanto `05-dados.md` define arquivos JSON sem banco.

## Documentação

- `00-BLUEPRINT.md`: PRD e ordem das fatias
- `01-arquitetura.md`: arquitetura e fronteiras
- `02-stack.md`: tecnologias, motores e licenças
- `03-backend.md`: contrato e estrutura do backend
- `04-frontend.md`: tela, componentes e estados
- `05-dados.md`: proposta alternativa de persistência em JSON
- `06-seguranca.md`: segurança local e consentimento
- `07-integracoes.md`: motores, MCP, FFmpeg e mock
- `08-deploy-local.md`: instalação e operação no Windows
- `09-metodo-de-construcao.md`: método por fatias
- `10-checklist.md`: critérios finais e armadilhas
- `ferramentas/protocolo_seguranca.py`: verificação das invariantes de segurança

## Regra de execução

Cada tarefa do Linear deve começar com `[ELEVEN_AUDIO] - FATIA N -`. Nenhuma fatia começa antes de a anterior cumprir seu critério de pronto.
