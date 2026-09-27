# 03 · Backend

> Arquivo 3 de 10 do manual. Aqui está o desenho do backend: o que a base já entrega, o que a
> nossa camada fina escreve, e os padrões que evitam dor.
> Padrão do kit: estrutura de arquivos real, blocos de código curtos, e a seção de boas práticas
> que economiza horas.

---

## 1. Estrutura da base (o que já existe, não mexer)

```text
4-BASE-VOICESTUDIO\
├── backend\
│   ├── main.py                 ponto de entrada único. A ordem de subida dele é sensível
│   ├── api\routers\            42 routers, montados automaticamente. Superfície HTTP e WS
│   │   ├── generation.py       POST /api/generate, histórico, áudio servido
│   │   ├── profiles.py         perfis de voz: criar, ler, editar, consentimento, apagar
│   │   ├── engines.py          catálogo de motores, seleção e instalação
│   │   ├── describe_voice.py   desenho de voz a partir de descrição
│   │   ├── capture.py e capture_ws.py   transcrição e ditado ao vivo
│   │   ├── mcp_bindings.py     vínculo de voz por agente de IA
│   │   ├── auth.py             sessão de administrador (só usada fora do loopback)
│   │   ├── system.py           superfície de admin, RCE class, loopback de verdade no desktop
│   │   ├── settings.py         preferências do app
│   │   └── openai_compat.py    /v1/audio/speech, transcrições e vozes no padrão OpenAI
│   ├── core\                   configuração, banco, fila de job, barramento de evento, auth, CSRF, caminho seguro
│   ├── services\               90 módulos de lógica: TTS, dublagem, DSP, gateway de GPU, roteamento de motor
│   ├── engines\                adaptadores por motor (indextts, voxcpm2, omnivoice_gguf, ...)
│   ├── mcp_shim\               entrada do servidor MCP para clientes que só falam stdio
│   ├── schemas\                formas de requisição e resposta
│   └── migrations\versions\    revisões de esquema (alembic)
├── frontend\                   UI web da base (React)
├── electron\                   app de mesa Electron (o único app de mesa desde a 0.5.3)
└── docs\                       a documentação que a gente lê e cita
```

O que a gente aprende olhando essa estrutura: **um ponto de entrada, routers finos, serviços com a
regra de negócio, adaptador por motor, esquema versionado.** É o mesmo desenho que a nossa camada
fina copia em escala menor.

---

## 2. Estrutura da nossa camada fina

```text
estudio\
├── app\
│   ├── servidor.py     app FastAPI: monta /api/* e serve a tela
│   ├── rotas.py        as 17 rotas do contrato (ou divididas em rotas_gerar.py, rotas_voz.py)
│   ├── motor.py        adaptador de motor: escolhe omnivoice, voxcpm2, indextts ou mock
│   ├── base.py         cliente HTTP da base local: um lugar só para timeout, retry e erro
│   ├── cofre.py        SQLite: esquema, migração simples, consultas
│   ├── saidas.py       nomear, gravar, listar e apagar áudio em saidas\audio\
│   ├── tarefas.py      fila local de uma geração por vez, com progresso
│   ├── agente.py       ligar MCP, criar e remover vínculo de voz por cliente
│   ├── config.py       leitura de variável de ambiente com padrão e validação na subida
│   └── log.py          log em dados\logs\ com rotação simples
├── web\                a tela única
├── dados\              estudio.db, referencias\, logs\
├── saidas\audio\       os áudios
├── scripts\
│   ├── subir-base.ps1  sobe a base em 3900
│   ├── subir-app.ps1   sobe a nossa camada em 7800
│   └── fumaca.py       teste de fumaça: health da base, gerar 1 áudio, conferir arquivo
└── requirements.txt    dependências da nossa camada (lista limpa)
```

Regra de organização: `servidor.py` é o maestro, `rotas_*.py` quando o arquivo crescer, regra de
negócio fora da rota (testável sem framework), e cliente da base só em um lugar (`base.py`).

---

## 3. Padrões essenciais com código

### 3.1 Configuração na subida, com padrão e validação (nunca no import)

```python
# app/config.py
import os
from pathlib import Path

PORTA          = int(os.environ.get("ESTUDIO_PORT", "7800"))
PORTA_BASE     = int(os.environ.get("ESTUDIO_BASE_PORT", "3900"))
URL_BASE       = os.environ.get("ESTUDIO_BASE_URL", f"http://127.0.0.1:{PORTA_BASE}")
MOTOR_PADRAO   = os.environ.get("ESTUDIO_MOTOR", "omnivoice")
MOTOR_ASR      = os.environ.get("ESTUDIO_MOTOR_ASR", "faster-whisper")
SAIDAS         = Path(os.environ.get("ESTUDIO_SAIDAS", "saidas/audio"))
DADOS          = Path(os.environ.get("ESTUDIO_DADOS", "dados"))
TIMEOUT_S      = int(os.environ.get("ESTUDIO_TIMEOUT_S", "1800"))

def validar_na_subida() -> list[str]:
    avisos = []
    SAIDAS.mkdir(parents=True, exist_ok=True)
    DADOS.mkdir(parents=True, exist_ok=True)
    if not (DADOS / "referencias").exists():
        (DADOS / "referencias").mkdir(parents=True, exist_ok=True)
    return avisos
```

Motivo do cuidado: variável obrigatória lida no topo do módulo com `os.environ["X"]` derruba a
subida inteira quando falta. Aqui tudo tem padrão, e o que precisa existir é criado na subida com
aviso claro em português.

### 3.2 Cliente único da base (timeout explícito e erro traduzido)

```python
# app/base.py
import httpx
from app import config

class ErroDaBase(Exception):
    def __init__(self, mensagem: str, status: int | None = None):
        super().__init__(mensagem)
        self.status = status

def _cliente() -> httpx.Client:
    return httpx.Client(base_url=config.URL_BASE, timeout=httpx.Timeout(config.TIMEOUT_S, connect=5.0))

def saudavel() -> bool:
    try:
        with _cliente() as c:
            return c.get("/health").status_code == 200
    except httpx.HTTPError:
        return False

def gerar(texto: str, motor: str, perfil_id: str | None, idioma: str = "pt", semente: int | None = None):
    dados = {"text": texto, "engine": motor, "language": idioma, "effect_preset": "broadcast"}
    if perfil_id:
        dados["profile_id"] = perfil_id
    if semente is not None:
        dados["seed"] = str(semente)
    with _cliente() as c:
        r = c.post("/api/generate", data=dados)
    if r.status_code >= 400:
        raise ErroDaBase(_motivo(r), r.status_code)
    return r.json()

def _motivo(r: httpx.Response) -> str:
    import json
    try:
        corpo = r.json()
        return str(corpo.get("detail") or corpo)
    except json.JSONDecodeError:
        return f"erro {r.status_code} sem corpo legivel"
```

Regra de ouro: **um só lugar** conhece a base. Se a base mudar de porta, de caminho ou de forma de
erro, muda um arquivo.

### 3.3 Adaptador de motor (trocar motor sem tocar em regra de negócio)

```python
# app/motor.py
import os
from app import base

MOTORES_VALIDOS = {"omnivoice", "voxcpm2", "indextts", "mock"}

def motores_disponiveis() -> list[dict]:
    """Le a base e normaliza para a tela. O motivo vem literal da base."""
    try:
        bruto = base.listar_motores()          # GET /api/engines
    except base.ErroDaBase as e:
        return [{"id": "mock", "nome": "Motor de teste", "disponivel": True, "motivo": str(e)}]
    lista = []
    for m in bruto.get("tts", bruto if isinstance(bruto, list) else []):
        lista.append({
            "id": m.get("id") or m.get("name"),
            "nome": m.get("label") or m.get("name"),
            "disponivel": bool(m.get("available", False)),
            "motivo": m.get("reason") or m.get("message") or "",
            "max_ref_segundos": m.get("max_ref_seconds"),
            "clonagem": bool(m.get("cloning", False)),
        })
    lista.append({"id": "mock", "nome": "Motor de teste", "disponivel": True,
                  "motivo": "tom de 440 Hz, sem GPU", "clonagem": False})
    return lista

def sintetizar(texto: str, motor: str | None, perfil_id: str | None,
               idioma: str = "pt", semente: int | None = None) -> dict:
    motor = (motor or os.environ.get("ESTUDIO_MOTOR", "omnivoice")).lower()
    if motor not in MOTORES_VALIDOS:
        raise ValueError(f"motor invalido: {motor}")
    if motor == "mock":
        return _mock(texto, perfil_id)
    return base.gerar(texto=texto, motor=motor, perfil_id=perfil_id, idioma=idioma, semente=semente)
```

### 3.4 Motor de teste (o mock que destrava o desenvolvimento)

```python
# app/motor.py (continuacao)
import math, struct, wave, time, uuid

def _mock(texto: str, perfil_id: str | None) -> dict:
    """Gera um wav valido com tom de 440 Hz. Duracao proporcional ao texto."""
    segundos = max(0.6, min(30.0, len(texto) / 14.0))
    taxa = 24000
    amostras = int(taxa * segundos)
    caminho = config.SAIDAS / f"{_carimbo()}_mock_{perfil_id or 'padrao'}.wav"
    with wave.open(str(caminho), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa)
        quadro = bytearray()
        for i in range(amostras):
            valor = int(0.25 * 32767 * math.sin(2 * math.pi * 440 * i / taxa))
            quadro += struct.pack("<h", valor)
        w.writeframes(bytes(quadro))
    return {"audio_id": f"mock-{uuid.uuid4().hex[:8]}", "arquivo": str(caminho),
            "duracao_audio_s": segundos, "motor": "mock"}
```

Por que isso não é brincadeira: com o mock, a tela, a fila, o banco, os estados e o teste
automatizado ficam prontos antes de baixar 2,3 GB. O modo mock nunca é padrão e sempre aparece no
nome do arquivo e no registro.

### 3.5 Rota completa (o padrão que se repete)

```python
# app/rotas.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app import motor, cofre, saidas

router = APIRouter(prefix="/api", tags=["estudio"])

class PedidoGerar(BaseModel):
    texto: str = Field(min_length=1, max_length=5000)
    perfil_id: str | None = None
    motor: str | None = None
    idioma: str = "pt"
    velocidade: float = Field(default=1.0, ge=0.5, le=2.0)
    semente: int | None = None

@router.post("/gerar")
def gerar(pedido: PedidoGerar):
    if pedido.perfil_id and not cofre.tem_consentimento(pedido.perfil_id):
        raise HTTPException(status_code=409, detail="perfil sem consentimento registrado")
    inicio = time.perf_counter()
    try:
        bruto = motor.sintetizar(pedido.texto, pedido.motor, pedido.perfil_id,
                                 pedido.idioma, pedido.semente)
    except motor.MotorIndisponivel as e:
        raise HTTPException(status_code=409, detail=f"motor indisponivel: {e}")
    except motor.ErroDaBase as e:
        raise HTTPException(status_code=502, detail=f"base respondeu: {e}")
    destino = saidas.guardar(bruto, pedido.motor or motor.PADRAO, pedido.perfil_id)
    medido = time.perf_counter() - inicio
    registro = cofre.registrar_geracao(destino, pedido, medido)
    return {**registro, "arquivo": str(destino)}
```

Esse é o "tijolo": validação, checagem de consentimento, chamada pelo adaptador, gravação em disco,
medição, registro e resposta. Toda rota nova copia esse formato.

### 3.6 Fila local (uma geração por vez)

```python
# app/tarefas.py (esqueleto)
import asyncio, uuid

_fila: asyncio.Queue = asyncio.Queue()
_estado: dict[str, dict] = {}

async def enfileirar(pedido: dict) -> str:
    tarefa_id = f"g-{uuid.uuid4().hex[:8]}"
    _estado[tarefa_id] = {"id": tarefa_id, "etapa": "na fila", "progresso": 0.0}
    await _fila.put((tarefa_id, pedido))
    return tarefa_id

async def trabalhar():
    while True:
        tarefa_id, pedido = await _fila.get()
        try:
            _estado[tarefa_id].update(etapa="chamando a base", progresso=0.2)
            ...  # chama o motor, salva, mede
            _estado[tarefa_id].update(etapa="pronto", progresso=1.0, arquivo=...)
        except Exception as e:
            _estado[tarefa_id].update(etapa="erro", erro=str(e))
        finally:
            _fila.task_done()
```

Etapas que a tela mostra (nomes iguais aos do estado): na fila, carregando o motor, sintetizando,
salvando, pronto, erro. Nunca "carregando" infinito sem etapa.

### 3.7 Teste de fumaça (o script que diz se está tudo no ar)

```python
# scripts/fumaca.py
from app import base, motor, saidas

def main():
    print("base saudavel:", base.saudavel())
    print("motores:", [m["id"] for m in motor.motores_disponiveis()])
    r = motor.sintetizar("Teste de fumaca do estudio local.", None, None)
    print("arquivo:", r.get("arquivo"), "duracao:", r.get("duracao_audio_s"))
    print("existe no disco:", saidas.existe(r.get("arquivo")))

if __name__ == "__main__":
    main()
```

---

## 4. Endpoints: a lista que a nossa camada expõe

| Método | Rota | Recebe | Responde | Observação |
|---|---|---|---|---|
| GET | `/api/estado` | nada | versão, base no ar, motores, motor ativo, dispositivo, pasta, última geração | base do rodapé |
| GET | `/api/motores` | nada | lista normalizada | motivo literal da base |
| POST | `/api/motores/ativo` | `{motor}` | motor gravado | grava em `configuracao` |
| POST | `/api/gerar` | `{texto, perfil_id, motor, idioma, velocidade, semente}` | id e caminho | enfileira e devolve id |
| GET | `/api/gerar/{id}` | nada | etapa e progresso | consultado em intervalo curto |
| GET | `/api/saidas` | filtros | lista de arquivos | lê o disco como fonte da verdade |
| POST | `/api/clonar` | multipart | perfil criado | consentimento obrigatório |
| GET | `/api/perfis` | nada | perfis com consentimento | |
| DELETE | `/api/perfis/{id}` | nada | removido | apaga na base e no nosso banco |
| POST | `/api/desenhar` | `{descricao, texto_previa, motor}` | áudio e caminho | usa VoxCPM2 |
| POST | `/api/transcrever` | multipart | texto | usa o motor de ASR |
| GET | `/api/agente/status` | nada | MCP e vínculos | |
| POST | `/api/agente/ligar` | `{cliente_id, perfil_id}` | vínculo feito | grava nos dois lados |
| POST | `/api/agente/desligar` | `{cliente_id}` | vínculo removido | |
| GET | `/api/config` | nada | configuração atual | sem segredo nenhum |
| POST | `/api/config` | chaves permitidas | configuração gravada | |
| GET | `/api/saude` | nada | nosso estado, estado da base, disco livre | usado pelo monitor |

---

## 5. Boas práticas que evitam dor

- **Não use `uvicorn --reload` no Windows.** Ele deixa processo órfão servindo código velho e você
  jura que a mudança não pegou. Rode um processo e reinicie na mão, ou use Docker.
- **Import sempre no topo do arquivo.** Um `import os` faltando vira erro 500 na primeira chamada
  real, e o erro aparece longe da causa.
- **Nunca leia variável obrigatória no import** (`os.environ["X"]`). Use `.get` com padrão e valide
  na subida, com mensagem em português.
- **Caminho com acento e espaço existe** (a pasta do projeto tem os dois). Sempre use `pathlib` e
  sempre passe caminho entre aspas no shell.
- **Cheque a porta antes de subir.** A base usa 3900 e a gente usa 7800. Porta ocupada por outro
  projeto é a causa clássica de "abri o endereço e apareceu outro site".
- **Não bloqueie a interface esperando a fila da GPU.** Enfileire e consulte.
- **Times distintos para coisas distintas:** fila de GPU (1.800 s), geração acelerada (300 s),
  geração em CPU (600 s), transcrição de arquivo (300 s). Não use um tempo único para tudo.
- **Trate o primeiro uso de um motor como etapa, não como erro.** O peso baixa na primeira chamada
  (cerca de 2,3 GB no motor padrão).
- **Nunca escreva na pasta da base.** Considere a base somente leitura de arquivo: toda conversa é
  por API, e toda escrita é na nossa pasta.
- **Registre o motivo literal do erro da base.** Traduza a moldura, mas nunca invente a causa.

---

## 6. Erros conhecidos da base que a nossa camada precisa tratar

| Sintoma | Causa real | O que a nossa camada faz |
|---|---|---|
| `[clone_ref_too_long]` | clipe acima do limite recebeu transcrição junto | cortar o clipe antes de enviar e avisar na tela |
| Motor aparece indisponível sem motivo | o painel de motivo é deliberadamente genérico na base | ler `/api/engines` e mostrar o campo de motivo; se vazio, mandar instalar ou trocar de motor |
| Primeira geração longa | download de peso, não travamento | mostrar etapa "baixando peso" e tempo separado no registro |
| Geração lenta demais em placa pequena | a base orça como hardware de CPU quando está abaixo do piso de VRAM | o rodapé mostra o dispositivo e o motivo |
| Transcrição falha com erro de cuDNN | falta cuDNN 8 no ambiente CUDA | mensagem clara com o comando de reparo, sem tentar de novo em laço |
| Interface abre e nada carrega | CORS quando a UI está em outra origem | declarar a origem exata em `OMNIVOICE_ALLOWED_ORIGINS` |
| Erro 409 de consentimento | perfil criado sem consentimento | a tela bloqueia antes, e o erro existe como rede de segurança |

---

## 7. Checklist de backend (20 itens)

- [ ] Cliente da base em um arquivo só, com timeout explícito
- [ ] Configuração com padrão e validação na subida
- [ ] Nenhum caminho absoluto no código
- [ ] Nenhum segredo no código
- [ ] Rota de saúde respondendo e conferindo a base
- [ ] Adaptador de motor com quatro opções (três reais mais o teste)
- [ ] Motor de teste gerando wav válido e com `mock` no nome do arquivo
- [ ] Validação de entrada com mensagem em português
- [ ] Consentimento checado antes de qualquer geração com perfil clonado
- [ ] Gravação de arquivo com nome legível e data
- [ ] Medição de tempo de parede e duração de áudio em toda geração
- [ ] Registro em banco para gerar, clonar, desenhar e transcrever
- [ ] Fila local serializando geração
- [ ] Etapas de progresso nomeadas e visíveis
- [ ] Erro da base traduzido com o motivo literal preservado
- [ ] Log em arquivo com data, sem dado sensível
- [ ] Teste de fumaça rodando em um comando
- [ ] Nenhuma escrita na pasta da base
- [ ] Base subindo com um comando de script
- [ ] Nossa camada subindo com um comando de script
