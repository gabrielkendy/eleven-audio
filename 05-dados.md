# 05 · Dados (arquivos JSON, sem banco de dados)

> Arquivo 5 de 12 do manual. Este projeto **não tem banco de dados**. Ele grava arquivos JSON na
> pasta de dados. A decisão é consciente e está explicada abaixo, porque saber quando NÃO usar
> banco é tão importante quanto saber usar.
> Padrão do kit: modelagem, índices, migração, retenção e backup. Adaptação: onde o kit tem tabela,
> aqui tem arquivo. O que o kit chama de migração, aqui é versão de esquema no próprio arquivo.

---

## 1. A decisão: por que arquivo, e não banco

Três fatos do projeto decidem isso:

1. **Um usuário só.** Não existe concorrência de escrita. Não existe "duas máquinas gravando".
2. **Poucos registros.** Uma pessoa gera dezenas a alguns milhares de áudios. Não é milhão de linha.
3. **O produto do trabalho já é arquivo.** O áudio é `.wav` no disco. O registro dele é acessório.

Com esses três fatos, um banco adiciona conceito sem adicionar capacidade.

| Opção | A favor | Contra aqui | Decisão |
|---|---|---|---|
| **Arquivo JSON** | zero dependência, abre no bloco de notas, backup é copiar, dá para inspecionar no vídeo | sem consulta, tudo carrega na memória | **sim** |
| SQLite | consulta em SQL, índice, transação | exige migração, esquema, PRAGMA e WAL. Conceito novo para um problema que não existe | não |
| Postgres/MySQL | relacional forte, multi usuário | servidor, senha, porta, instalação | não |
| MongoDB | flexível | servidor rodando | não |

**A regra que vale:** banco de dados resolve concorrência, volume e integridade entre muitos
escritores. Quando os três não existem, arquivo resolve melhor e o aluno entende mais rápido.

**Quando trocar para banco:** no dia em que existir mais de um usuário, mais de cem mil registros,
ou consulta por filtro combinado. Aí a migração é necessária, e o `09-metodo-de-construcao.md`
explica como fazer isso sem reescrever a aplicação.

---

## 2. Onde cada coisa mora (registro contra arquivo)

| Tipo de dado | Onde mora | Por quê |
|---|---|---|
| Áudio gerado | `saidas\audio\` (`.wav`, e `.opus` quando precisar) | é o produto do trabalho. A pessoa abre a pasta e vê |
| Áudio de referência (clipe de clonagem) | `dados\referencias\` | insumo sensível: precisa ser fácil de apagar |
| Registro de geração | `dados\geracoes.json` | histórico, tempo medido e caminho do arquivo |
| Perfis de voz | `dados\perfis.json` | espelho local do perfil que vive na base |
| Consentimento | `dados\consentimentos.json` | o registro mais importante do produto |
| Transcrições | `dados\transcricoes.json` | texto leve, histórico de uso |
| Vínculo de agente | `dados\vinculos.json` | qual voz cada cliente do MCP usa |
| Configuração | `dados\config.json` mais variável de ambiente | variável manda no que é de máquina. Arquivo guarda o que a pessoa escolheu |
| Eventos e auditoria | `dados\eventos.jsonl` | uma linha por evento, cresce só acrescentando |
| Log de execução | `dados\logs\AAAA-MM-DD.log` | diagnóstico e história da gravação |

```text
projeto\
  dados\
    config.json
    perfis.json
    consentimentos.json
    geracoes.json
    transcricoes.json
    vinculos.json
    eventos.jsonl          <- uma linha JSON por evento, nunca reescreve
    referencias\           <- clipes de voz usados para clonar
    logs\
      2026-09-27.log
  saidas\
    audio\
      2026-09-27_143052_demo-pt_motor-omnivoice.wav
```

**Regra dura:** binário de áudio nunca entra em arquivo de dados. Arquivo `.wav` dentro de JSON
significa base64 gigante, leitura lenta e corrupção mais provável. O JSON guarda o **caminho**, o
áudio fica no disco.

---

## 3. Formato de cada arquivo

### 3.1 `dados\geracoes.json`

```json
{
  "versao_esquema": 1,
  "atualizado_em": "2026-09-27T14:30:52-03:00",
  "registros": [
    {
      "id": "ger_20260927_143052_a1b2",
      "perfil_id": "per_20260927_141200_x9y8",
      "motor": "omnivoice",
      "texto_entrada": "texto que virou audio",
      "arquivo_saida": "saidas/audio/2026-09-27_143052_demo-pt_motor-omnivoice.wav",
      "duracao_audio_s": 12.4,
      "duracao_geracao_s": 3.1,
      "dispositivo": "cuda",
      "tamanho_bytes": 1185280,
      "criado_em": "2026-09-27T14:30:52-03:00",
      "status": "pronto",
      "erro": null
    }
  ]
}
```

### 3.2 `dados\perfis.json`

```json
{
  "versao_esquema": 1,
  "registros": [
    {
      "id": "per_20260927_141200_x9y8",
      "nome": "voz-do-gabriel",
      "origem": "clonado",
      "id_na_base": "vs_profile_8f21",
      "arquivo_referencia": "dados/referencias/clipe-2026-09-27.wav",
      "transcricao_ref": "trecho falado no clipe",
      "descricao_desenho": null,
      "idioma": "pt",
      "criado_em": "2026-09-27T14:12:00-03:00",
      "observacao": null
    }
  ]
}
```

### 3.3 `dados\consentimentos.json`

```json
{
  "versao_esquema": 1,
  "registros": [
    {
      "id": "con_20260927_141205_m3n4",
      "perfil_id": "per_20260927_141200_x9y8",
      "texto_aceito": "esta voz e minha, ou eu tenho autorizacao de quem e dono",
      "origem_voz": "propria",
      "aceito_em": "2026-09-27T14:12:05-03:00"
    }
  ]
}
```

**Um consentimento por perfil.** A gravação usa o `perfil_id` como chave e substitui o registro
anterior quando a pessoa refaz, mantendo a data nova. A prova do que foi aceito antes fica no
`eventos.jsonl`, que é append only.

### 3.4 `dados\eventos.jsonl` (formato diferente, de propósito)

Não é JSON de lista: é **uma linha JSON por evento**. Nunca reescreve o arquivo inteiro, só
acrescenta no fim. É o que garante histórico mesmo se a gravação for interrompida no meio.

```jsonl
{"id":"evt_...","tipo":"subida","detalhe":"app subiu na porta 7800","criado_em":"2026-09-27T14:10:00-03:00"}
{"id":"evt_...","tipo":"clonar","detalhe":"perfil per_... criado a partir de clipe de 9s","criado_em":"2026-09-27T14:12:05-03:00"}
{"id":"evt_...","tipo":"gerar","detalhe":"geracao ger_... motor omnivoice 12.4s em 3.1s","criado_em":"2026-09-27T14:30:52-03:00"}
{"id":"evt_...","tipo":"erro","detalhe":"motor voxcpm2 indisponivel: peso nao encontrado","criado_em":"2026-09-27T14:35:10-03:00"}
```

Tipos usados: `subida`, `gerar`, `clonar`, `transcrever`, `desenhar`, `vincular`, `revogar`,
`apagar`, `erro`, `limpeza`.

---

## 4. A técnica que faz JSON ser seguro: escrita atômica

Esta é a parte que separa arquivo JSON que funciona de arquivo JSON que corrompe.

**Nunca** abrir o arquivo final e escrever por cima. Se o processo cair no meio, o arquivo fica
pela metade e o dado some.

```python
# app/cofre.py
import json, os, tempfile
from pathlib import Path

def gravar_json(caminho: Path, dados: dict) -> None:
    """Grava JSON sem risco de corromper: escreve em temporario, sincroniza, renomeia."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=caminho.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())        # garante que saiu para o disco
        os.replace(tmp, caminho)        # troca atomica: ou o antigo, ou o novo
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

def append_jsonl(caminho: Path, linha: dict) -> None:
    """Acrescenta uma linha. Nunca reescreve o arquivo."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
```

As três partes que importam: **escreve em temporário**, **`fsync`** (força a descida para o disco)
e **`os.replace`** (troca atômica). O `os.replace` é atômico no mesmo sistema de arquivos: ou o
arquivo é o antigo completo, ou o novo completo. Nunca um meio termo.

---

## 5. Leitura e consulta (o jeito certo sem SQL)

```python
# app/cofre.py
from pathlib import Path
import json

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

def ler_json(nome: str) -> dict:
    p = DADOS / nome
    if not p.exists():
        return {"versao_esquema": 1, "registros": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # arquivo corrompido: preserva para diagnostico e recomeca vazio
        p.rename(p.with_suffix(p.suffix + ".corrompido"))
        return {"versao_esquema": 1, "registros": []}
```

Consultas que a tela e o vídeo usam:

```python
# ultimas 20 geracoes com tempo medido
ultimas = sorted(ler_json("geracoes.json")["registros"],
                 key=lambda r: r["criado_em"], reverse=True)[:20]

# media de tempo por motor (o numero que vai para o video)
from statistics import mean
por_motor = {}
for r in ler_json("geracoes.json")["registros"]:
    if r["status"] == "pronto" and r.get("duracao_geracao_s"):
        por_motor.setdefault(r["motor"], []).append(
            (r["duracao_audio_s"], r["duracao_geracao_s"])
        )
for motor, pares in por_motor.items():
    audio = mean(p[0] for p in pares)
    geracao = mean(p[1] for p in pares)
    print(f"{motor}: {len(pares)} geracoes, audio medio {audio:.1f}s, "
          f"geracao media {geracao:.1f}s, fator {geracao/audio:.2f}")

# perfis sem consentimento (tem que ser zero)
perfis = {p["id"] for p in ler_json("perfis.json")["registros"]}
com_consent = {c["perfil_id"] for c in ler_json("consentimentos.json")["registros"]}
orfaos = perfis - com_consent
assert not orfaos, f"perfil sem consentimento: {orfaos}"
```

**Limite honesto:** com lista em memória, tudo acima é O(n). Com cem mil registros isso fica lento.
Até algumas dezenas de milhares, abre instantâneo. No dia em que passar disso, esta seção vira a
migração para SQLite descrita no arquivo 09.

---

## 6. Versão de esquema (o que substitui a migração)

Cada arquivo carrega `versao_esquema`. Na subida, o app confere e atualiza quando precisa:

```python
# app/cofre.py
VERSAO_ESQUEMA = 1

def migrar(nome: str) -> None:
    dados = ler_json(nome)
    atual = int(dados.get("versao_esquema", 0))
    if atual == VERSAO_ESQUEMA:
        return
    if atual < 1:
        dados.setdefault("registros", [])
        dados["atualizado_em"] = agora_iso()
    dados["versao_esquema"] = VERSAO_ESQUEMA
    gravar_json(DADOS / nome, dados)
    append_jsonl(DADOS / "eventos.jsonl", {
        "id": novo_id("evt"), "tipo": "limpeza",
        "detalhe": f"{nome} migrado do esquema {atual} para {VERSAO_ESQUEMA}",
        "criado_em": agora_iso(),
    })
```

Regras: roda na subida, é **idempotente** (rodar duas vezes não muda nada), copia o arquivo antes
de mudança destrutiva, e cada mudança de formato entra com número novo.

---

## 7. Retenção, limpeza e tamanho

| Item | Regra | Por quê |
|---|---|---|
| Áudio gerado | fica até a pessoa apagar. A tela mostra o tamanho total da pasta | é o trabalho dela |
| Clipe de referência | fica em `dados\referencias\`, com botão de apagar junto do perfil | dado sensível de voz |
| Registro de geração | mantém. É leve e é o histórico de medição | permite provar número no vídeo |
| Eventos | mantém 90 dias, corta o resto com script | evita crescer para sempre |
| Log de execução | um arquivo por dia, mantém 30 | diagnóstico suficiente |
| Registro com arquivo ausente | marca `arquivo_ausente` em vez de apagar a linha | preserva a medição |

```python
# rotina de limpeza, uma vez por dia, na subida
def limpar_eventos_antigos(dias: int = 90) -> int:
    p = DADOS / "eventos.jsonl"
    if not p.exists():
        return 0
    corte = agora_iso(delta_dias=-dias)
    linhas = p.read_text(encoding="utf-8").splitlines()
    manter = [l for l in linhas if json.loads(l)["criado_em"] >= corte]
    removidas = len(linhas) - len(manter)
    if removidas:
        gravar_json(p.with_suffix(".jsonl.tmp"), {})   # marca intencao
        Path(str(p)).write_text("\n".join(manter) + "\n", encoding="utf-8", newline="\n")
    return removidas
```

---

## 8. Backup (em duas linhas, e é isso que vende o local)

| O que fazer | Comando |
|---|---|
| Backup completo | copiar as pastas `dados\` e `saidas\` para outro disco |
| Backup só do registro | copiar a pasta `dados\` inteira, com o app parado |
| Restaurar | copiar de volta com o app parado |
| Verificação | abrir o app, conferir a lista de perfis e gerar um áudio de teste |

Aviso que vai escrito na tela: **backup é pasta, não é nuvem.** Quem quiser nuvem decide
conscientemente, sabendo que o clipe de voz de referência sai da máquina se a pasta sincronizar.

---

## 9. O que fica FORA dos arquivos de dados (por decisão)

| Item | Por que fica fora |
|---|---|
| Áudio | regra dura da seção 2 |
| Peso de motor | é da base e é grande (GB) |
| Segredo de qualquer tipo | o projeto não tem segredo. Fingir que tem só cria risco |
| Cache da base | é da base. Duplicar gera divergência |
| Telemetria | não existe coleta no recorte |
| Caminho absoluto | caminho absoluto gravado quebra quando a pasta muda de lugar |
| Base64 de áudio | infla 33 por cento e mata a leitura |

---

## 10. Armadilhas de arquivo de dados (as que já morderam)

| Problema | Sintoma | Solução |
|---|---|---|
| Escrever direto no arquivo final | queda no meio deixa JSON pela metade e dado some | escrita atômica (seção 4) |
| Guardar áudio dentro do JSON | arquivo gigante, lentidão, corrupção | só o caminho. O áudio é arquivo |
| Caminho absoluto gravado | mover a pasta quebra tudo | caminho relativo ao projeto, resolvido na leitura |
| Dois processos escrevendo no mesmo arquivo | um sobrescreve o outro | trava de instância única na subida |
| JSON sem `ensure_ascii=False` | acento vira `\u00e7` e o arquivo fica ilegível | gravar com `ensure_ascii=False` e UTF-8 |
| Nome de arquivo com acento e emoji | ferramenta externa falha | sanitizar para ASCII |
| Sem versão de esquema | mudança de formato quebra dado antigo | `versao_esquema` em todo arquivo (seção 6) |
| Lista gigante em memória | trava ao abrir | cortar por data na leitura e paginar na tela |
| Data sem fuso | ordenação errada | ISO 8601 com fuso, sempre |
| Apagar perfil e deixar clipe órfão | voz esquecida no disco | apagar a referência junto, ou declarar órfão na tela |

---

## 11. Checklist de dados (20 itens)

- [ ] Nenhum banco de dados no projeto
- [ ] Seis arquivos JSON mais um JSONL em `dados\`
- [ ] Áudio nunca dentro de arquivo de dado
- [ ] Escrita atômica implementada (`tempfile` mais `os.fsync` mais `os.replace`)
- [ ] `eventos.jsonl` só acrescenta, nunca reescreve
- [ ] `versao_esquema` em todo arquivo de dados
- [ ] Migração idempotente na subida
- [ ] Cópia antes de mudança destrutiva de formato
- [ ] Caminho gravado em forma relativa
- [ ] Leitura tolerante a arquivo corrompido (renomeia e recomeça)
- [ ] Um consentimento por perfil, com data
- [ ] Consulta de perfis sem consentimento volta vazia
- [ ] Consulta de média de tempo por motor funcionando
- [ ] Lista de saídas lida do disco e cruzada com o registro
- [ ] Nome de arquivo sanitizado para ASCII
- [ ] Data em ISO 8601 com fuso em todos os registros
- [ ] Trava de instância única na subida
- [ ] Limpeza de evento com 90 dias
- [ ] Backup documentado em uma linha
- [ ] Nenhum segredo guardado em arquivo de dados
