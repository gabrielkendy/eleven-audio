# 05 · Dados (SQLite local)

> Arquivo 5 de 10 do manual. A fonte de verdade é `00-BLUEPRINT.md`: os metadados do Estúdio de
> Voz Local ficam em `dados/estudio.db`, enquanto todo áudio continua como arquivo no disco.

---

## 1. Decisão

O projeto usa SQLite porque precisa manter relações e integridade entre perfil, consentimento,
geração, transcrição e vínculo de agente. Ele entrega transação, chave estrangeira e consulta sem
adicionar servidor, conta, senha ou serviço de nuvem.

| Opção | Decisão | Motivo |
|---|---|---|
| SQLite | sim | arquivo único, biblioteca padrão do Python, transações e índices |
| JSON ou JSONL | não | não garante as relações e transações exigidas pelo blueprint |
| Postgres, MySQL ou MongoDB | não | exigem serviço separado e ampliam o recorte local |

Não existe multiusuário nem `workspace_id` neste produto. O dono é a pessoa que executa o app e a
fronteira é a pasta local de dados. Uma migração para banco servidor só passa a fazer sentido se o
produto mudar para mais de uma máquina ou escritor concorrente.

---

## 2. Onde cada dado mora

| Dado | Local | Regra |
|---|---|---|
| Metadados do app | `dados/estudio.db` | SQLite, nunca editado manualmente |
| Áudio gerado | `saidas/audio/*.wav` | produto do trabalho, nunca BLOB no banco |
| Clipe de referência | `dados/referencias/*.wav` | dado sensível, removido com o perfil |
| Logs locais | `dados/logs/estudio-AAAA-MM-DD.log` | sem texto do usuário ou áudio |
| Pesos e cache da base | diretório da base | pertencem ao VoiceStudio e não são duplicados |

O banco guarda caminhos relativos à raiz do projeto. Caminho absoluto, áudio em base64 e credencial
ficam fora do esquema.

---

## 3. Esquema versionado

A migração roda na subida, dentro de uma transação, e é idempotente. A versão inicial cria sete
tabelas. Esse passo pertence à FATIA 1; a FATIA 0 apenas fixa o contrato.

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS perfil_voz (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL CHECK (length(nome) BETWEEN 1 AND 60),
    origem TEXT NOT NULL CHECK (origem IN ('clonado', 'desenhado')),
    id_na_base TEXT NOT NULL UNIQUE,
    arquivo_referencia TEXT,
    transcricao_referencia TEXT,
    descricao_desenho TEXT,
    idioma TEXT NOT NULL DEFAULT 'pt',
    criado_em TEXT NOT NULL,
    observacao TEXT,
    CHECK (
        (origem = 'clonado' AND arquivo_referencia IS NOT NULL
         AND transcricao_referencia IS NOT NULL)
        OR (origem = 'desenhado' AND descricao_desenho IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS consentimento (
    id TEXT PRIMARY KEY,
    perfil_id TEXT NOT NULL UNIQUE REFERENCES perfil_voz(id) ON DELETE CASCADE,
    texto_aceito TEXT NOT NULL,
    aceito_em TEXT NOT NULL,
    origem_voz TEXT NOT NULL CHECK (origem_voz IN ('propria', 'autorizada'))
);

CREATE TABLE IF NOT EXISTS geracao (
    id TEXT PRIMARY KEY,
    perfil_id TEXT REFERENCES perfil_voz(id) ON DELETE SET NULL,
    motor TEXT NOT NULL CHECK (motor IN ('omnivoice', 'voxcpm2', 'indextts', 'mock')),
    texto_entrada TEXT NOT NULL,
    arquivo_saida TEXT NOT NULL,
    duracao_audio_s REAL NOT NULL CHECK (duracao_audio_s >= 0),
    duracao_geracao_s REAL NOT NULL CHECK (duracao_geracao_s >= 0),
    dispositivo TEXT NOT NULL CHECK (dispositivo IN ('cuda', 'cpu')),
    tamanho_bytes INTEGER NOT NULL CHECK (tamanho_bytes >= 0),
    criado_em TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'erro')),
    erro TEXT
);

CREATE TABLE IF NOT EXISTS transcricao (
    id TEXT PRIMARY KEY,
    arquivo_entrada TEXT NOT NULL,
    motor TEXT NOT NULL CHECK (motor IN ('faster-whisper', 'whisperx')),
    texto_saida TEXT NOT NULL,
    idioma_detectado TEXT,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vinculo_agente (
    id TEXT PRIMARY KEY,
    cliente_id TEXT NOT NULL UNIQUE,
    perfil_id TEXT NOT NULL REFERENCES perfil_voz(id) ON DELETE CASCADE,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS configuracao (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evento (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    detalhe TEXT NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geracao_criado_em ON geracao(criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_geracao_motor ON geracao(motor);
CREATE INDEX IF NOT EXISTS idx_evento_criado_em ON evento(criado_em DESC);
```

Datas são ISO 8601 com fuso. Valores booleanos, listas ou objetos da configuração são serializados
como JSON no campo `valor`; isso não transforma os registros do domínio em arquivos JSON.

---

## 4. Regras de acesso

1. Toda conexão ativa `foreign_keys`, `WAL` e `busy_timeout`.
2. Toda escrita usa parâmetro SQL. Nenhum valor do usuário entra por concatenação.
3. Operações que alteram mais de uma tabela usam uma única transação.
4. Consentimento e perfil são gravados juntos. Sem consentimento, geração clonada responde 409.
5. O caminho do arquivo é relativo e confinado às raízes `dados/` ou `saidas/`.
6. A camada de dados nunca lê nem escreve o SQLite interno da base VoiceStudio.
7. O processo do app mantém uma única instância escritora por porta.

Exemplo de abertura:

```python
import sqlite3
from pathlib import Path


def conectar(caminho: Path) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho, timeout=5)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA journal_mode = WAL")
    conexao.execute("PRAGMA busy_timeout = 5000")
    return conexao
```

---

## 5. Migração e recuperação

As migrações usam `PRAGMA user_version`:

1. abrir a conexão e iniciar transação;
2. ler `PRAGMA user_version`;
3. aplicar somente passos posteriores à versão encontrada;
4. atualizar `user_version` na mesma transação;
5. confirmar e executar `PRAGMA foreign_key_check`.

Rodar a migração duas vezes não altera o resultado. Antes de uma migração destrutiva, o app cria
backup consistente com a API de backup do próprio SQLite. Copiar só `estudio.db` enquanto o app
está aberto em WAL não é backup válido.

Backup simples com o app parado: copiar `dados/` e `saidas/`. Na restauração, fechar os dois
processos, copiar as pastas de volta, subir a base, subir o app e rodar `scripts/fumaca.py`.

---

## 6. Retenção e privacidade

| Item | Retenção |
|---|---|
| Áudio gerado | até a pessoa apagar |
| Clipe de referência | até apagar o perfil |
| Geração e medição | mantidas para o histórico local |
| Evento | 90 dias, com limpeza transacional |
| Log | 30 dias |

Apagar um perfil remove consentimento e vínculo por chave estrangeira, remove o clipe de referência
do disco e preserva gerações antigas com `perfil_id` nulo. O arquivo de saída continua pertencendo
à pessoa até ela pedir a remoção.

---

## 7. Checklist de dados

- [ ] SQLite em `dados/estudio.db`
- [ ] Sete tabelas criadas por migração idempotente
- [ ] `PRAGMA foreign_keys = ON`
- [ ] `PRAGMA journal_mode = WAL`
- [ ] `PRAGMA busy_timeout = 5000`
- [ ] Chaves estrangeiras e índices verificados
- [ ] Um consentimento por perfil
- [ ] Geração clonada bloqueada sem consentimento
- [ ] Áudio fora do banco
- [ ] Caminhos relativos e confinados
- [ ] SQL sempre parametrizado
- [ ] Datas ISO 8601 com fuso
- [ ] Duração e tempo de parede medidos
- [ ] Migração controlada por `user_version`
- [ ] `foreign_key_check` após migrar
- [ ] Backup feito com app parado ou API SQLite
- [ ] Nenhuma leitura direta do banco da base
- [ ] Nenhum segredo no banco
- [ ] Retenção de eventos e logs aplicada
- [ ] Restauração validada pelo teste de fumaça
