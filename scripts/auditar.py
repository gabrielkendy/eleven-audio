"""Auditoria profunda do ELEVEN AUDIO. Nao e teste de unidade: e uma varredura que
procura as CLASSES de defeito que ja morderam este projeto, para rodar sempre que
alguem mexer no codigo.

Uso:
    env -u PYTHONPATH <venv>/Scripts/python.exe scripts/auditar.py
    env -u PYTHONPATH <venv>/Scripts/python.exe scripts/auditar.py --com-app

Sai 0 quando nao acha nada e 1 quando acha, para poder entrar em hook de pre-push.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app"
WEB = RAIZ / "web"

falhas: list[str] = []
avisos: list[str] = []


def falha(texto: str) -> None:
    falhas.append(texto)


def aviso(texto: str) -> None:
    avisos.append(texto)


# --------------------------------------------------------------------------
# 1. fontes
# --------------------------------------------------------------------------
def fontes_py() -> list[Path]:
    return sorted(APP.rglob("*.py"))


def ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------
# 2. defeitos de Python, por AST (nao por regex: regex erra em comentario)
# --------------------------------------------------------------------------
def auditar_except(caminho: Path, arvore: ast.AST) -> None:
    """except Exception nu e except: nu sao proibidos quando engolem o erro."""
    for no in ast.walk(arvore):
        if not isinstance(no, ast.ExceptHandler):
            continue
        tipo = no.type
        nu = tipo is None or (
            isinstance(tipo, ast.Name) and tipo.id in {"Exception", "BaseException"}
        )
        if not nu:
            continue
        corpo = [n for n in no.body if not isinstance(n, ast.Expr)]
        # se o corpo so tem pass/continue/log e nao re-levanta, o erro morre aqui
        re_levanta = any(isinstance(n, ast.Raise) for n in ast.walk(no))
        if corpo and not re_levanta:
            falha(
                f"{caminho.relative_to(RAIZ)}:{no.lineno} except nu engole o erro "
                f"(sem raise e sem log). Use except (TipoA, TipoB) ou registre."
            )


def auditar_retorno_implicito(caminho: Path, arvore: ast.AST) -> None:
    """return dentro de finally engole excecao em silencio."""
    for no in ast.walk(arvore):
        if isinstance(no, ast.Try):
            for final in no.finalbody:
                if any(isinstance(n, ast.Return) for n in ast.walk(final)):
                    falha(
                        f"{caminho.relative_to(RAIZ)}:{final.lineno} return dentro de "
                        "finally: engole a excecao original."
                    )


def auditar_print_em_app(caminho: Path, arvore: ast.AST) -> None:
    """print solto no app nao substitui log e some no servico."""
    if caminho.name == "auditar.py":
        return
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "print":
            aviso(f"{caminho.relative_to(RAIZ)}:{no.lineno} print solto no app.")


# --------------------------------------------------------------------------
# 3. defeitos que so aparecem lendo: caminho pessoal, segredo, marcador
# --------------------------------------------------------------------------
PADROES_PROIBIDOS = [
    (re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z]"), "caminho pessoal do Windows"),
    (re.compile(r"C:\\Users\\|/c/Users/|C:/Users/", re.IGNORECASE), "caminho pessoal do Windows"),
    (re.compile(r"\bsk-[A-Za-z0-9]{16,}"), "chave OpenAI"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "token GitHub"),
    (re.compile(r"hf_[A-Za-z0-9]{20,}"), "token HuggingFace"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "chave AWS"),
]

# arquivos do proprio auditor e testes que FALAM sobre segredo de proposito
ISENTOS = {"auditar.py", "test_protocolo_seguranca.py"}


def auditar_segredos(caminho: Path) -> None:
    if caminho.name in ISENTOS:
        return
    texto = ler(caminho)
    for padrao, nome in PADROES_PROIBIDOS:
        achado = padrao.search(texto)
        if achado:
            linha = texto[: achado.start()].count("\n") + 1
            falha(f"{caminho.relative_to(RAIZ)}:{linha} {nome} no codigo: {achado.group()[:22]}...")


# --------------------------------------------------------------------------
# 4. o app so pode carregar o CSS/JS que existe E que a pagina declara
# --------------------------------------------------------------------------
def auditar_assets() -> None:
    html = ler(WEB / "index.html")
    declarados = set(re.findall(r'(?:src|href)="(/web/[^"?]+)', html))
    if not declarados:
        falha("index.html nao declara nenhum asset de /web/.")
    for caminho in sorted(declarados):
        alvo = RAIZ / caminho.lstrip("/")
        if not alvo.is_file():
            falha(f"index.html aponta para {caminho}, que nao existe.")

    # CSS/JS no disco que NINGUEM carrega = codigo morto, e ja custou 4 rodadas
    for arquivo in sorted(list(WEB.glob("*.css")) + list(WEB.glob("*.js"))):
        ref = f"/web/{arquivo.name}"
        if ref in declarados:
            continue
        if arquivo.name.endswith(".modulo.js"):
            continue
        aviso(
            f"{arquivo.relative_to(RAIZ)} existe mas NINGUEM carrega "
            "(editar nele nao muda nada na tela)."
        )


# --------------------------------------------------------------------------
# 5. o front so pode falar com rota que existe no back
# --------------------------------------------------------------------------
def rotas_do_back() -> set[str]:
    """Caminho completo de cada rota, ja com o prefixo do router.

    O router pode declarar `APIRouter(prefix="/api")` e o decorador so o resto
    (`@rotas.get("/estado")`). Ler so o decorador acusa rota existente como
    inexistente, que foi o primeiro erro deste proprio auditor.
    """
    rotas: set[str] = set()
    for caminho in fontes_py():
        texto = ler(caminho)
        try:
            arvore = ast.parse(texto)
        except SyntaxError:
            continue
        prefixos: dict[str, str] = {}
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Assign) or not isinstance(no.value, ast.Call):
                continue
            func = no.value.func
            nome_func = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if nome_func != "APIRouter":
                continue
            prefixo = ""
            for palavra in no.value.keywords:
                if palavra.arg == "prefix" and isinstance(palavra.value, ast.Constant):
                    prefixo = str(palavra.value.value)
            for alvo in no.targets:
                if isinstance(alvo, ast.Name):
                    prefixos[alvo.id] = prefixo
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorador in no.decorator_list:
                if not isinstance(decorador, ast.Call) or not isinstance(decorador.func, ast.Attribute):
                    continue
                if decorador.func.attr not in {"get", "post", "put", "delete", "patch"}:
                    continue
                objeto = decorador.func.value
                if not isinstance(objeto, ast.Name):
                    continue
                prefixo = prefixos.get(objeto.id, "")
                if not decorador.args or not isinstance(decorador.args[0], ast.Constant):
                    continue
                rota = str(decorador.args[0].value)
                rotas.add(prefixo + rota)
    return rotas


def chamadas_do_front() -> list[tuple[Path, int, str]]:
    """Toda URL que o front chama, ja resolvida.

    O front usa um helper `api(...)` que ja poe o `/api` na frente. Ler so a
    string crua acusa `/gerar` (que na verdade e `/api/gerar`) como inexistente.
    Aqui a resolucao e feita antes de comparar com o back.
    """
    achados: list[tuple[Path, int, str]] = []
    for arquivo in sorted(WEB.glob("*.js")):
        texto = ler(arquivo)
        for achado in re.finditer(r'(?<![\w.])(api|ler|enviar)?\(\s*["\'`](/[A-Za-z0-9_/{}.:-]*)', texto):
            helper, rota = achado.group(1), achado.group(2)
            if "${" in rota or "{" in rota:
                continue
            if helper in {"api", "ler", "enviar"} and not rota.startswith("/api"):
                rota = "/api" + rota
            linha = texto[: achado.start()].count("\n") + 1
            achados.append((arquivo, linha, rota.rstrip("/") or "/"))
    return achados


def auditar_contrato_de_rotas() -> None:
    existentes = rotas_do_back()
    if not existentes:
        falha("nao encontrei nenhuma rota declarada no back.")
        return
    for arquivo, linha, rota in chamadas_do_front():
        if rota in existentes or rota == "/api":
            continue
        # aceita prefixo: /api/perfis/x/audio casa com /api/perfis/{perfil_id}/audio
        casa = any(
            re.fullmatch(re.sub(r"\{[^}]+\}", r"[^/]+", existente) + r"(/.*)?", rota)
            for existente in existentes
            if "{" in existente
        )
        if casa:
            continue
        aviso(
            f"{arquivo.relative_to(RAIZ)}:{linha} chama {rota}, "
            "que o back nao declara com esse nome exato."
        )


# --------------------------------------------------------------------------
# 6. saidas: nome de arquivo nao pode colidir em geracao no mesmo segundo
# --------------------------------------------------------------------------
def auditar_nome_de_saida() -> None:
    sys.path.insert(0, str(RAIZ))
    try:
        from app import saidas
    except Exception as erro:  # noqa: BLE001 - import defensivo: o auditor
        # nao pode morrer por causa do que ele esta' auditando.
        falha(f"nao consegui importar app.saidas: {erro}")
        return
    primeiro = saidas.nome_arquivo("omnivoice", "vz-teste")
    if "/" in primeiro or "\\" in primeiro or ".." in primeiro:
        falha(f"app/saidas.py: nome de saida com separador de caminho: {primeiro}")

    # O invariante de verdade NAO e' "o gerador de nome produz nomes unicos" (ele
    # nao produz, e nem deve: o nome e' a convencao AAAA-MM-DD_HHMMSS_motor_perfil).
    # O invariante e' "gravar duas vezes no mesmo segundo nao perde audio".
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        gravados = []
        for numero in range(3):
            alvo = raiz / saidas.nome_arquivo("omnivoice", "vz-teste")
            gravados.append(saidas.gravar_bytes(alvo, f"audio-{numero}".encode()).name)
        if len(set(gravados)) != 3:
            falha(
                "app/saidas.py: gravar 3 vezes no mesmo segundo nao gerou 3 arquivos "
                f"({gravados}). A gravacao esta' apagando audio anterior."
            )
        vivos = sorted(arquivo.read_text() for arquivo in raiz.iterdir())
        if vivos != ["audio-0", "audio-1", "audio-2"]:
            falha(f"app/saidas.py: conteudo das saidas nao bate: {vivos}")


# --------------------------------------------------------------------------
# 7. servico no ar: todas as rotas GET respondem, e rapido
# --------------------------------------------------------------------------
def auditar_app_no_ar(porta: int = 7800) -> None:
    base = f"http://127.0.0.1:{porta}"
    try:
        import urllib.request
    except Exception:  # noqa: BLE001 - auditor nao pode morrer por causa de import
        return

    def bater(rota: str, limite_s: float = 5.0) -> tuple[int, float]:
        t0 = time.time()
        try:
            with urllib.request.urlopen(base + rota, timeout=30) as resposta:
                resposta.read(400)
                return resposta.status, time.time() - t0
        except urllib.error.HTTPError as erro:
            return erro.code, time.time() - t0
        except Exception:  # noqa: BLE001 - qualquer falha de rede aqui vira 'nao respondeu'
            return 0, time.time() - t0

    status, _ = bater("/api/saude")
    if status != 200:
        aviso(f"app nao respondeu em {base}/api/saude (status {status}). Pulando a varredura.")
        return

    # rotas GET sem parametro de caminho
    for rota in sorted(rotas_do_back()):
        if "{" in rota or not rota.startswith("/api"):
            continue
        status, tempo = bater(rota)
        if status == 0:
            falha(f"GET {rota} nao respondeu.")
        elif status >= 500:
            falha(f"GET {rota} devolveu {status}.")
        elif tempo > 5.0:
            aviso(f"GET {rota} levou {tempo:.2f}s (teto 5s).")


# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--com-app", action="store_true", help="tambem bate no app no ar")
    args = parser.parse_args()

    for caminho in fontes_py():
        texto = ler(caminho)
        try:
            arvore = ast.parse(texto)
        except SyntaxError as erro:
            falha(f"{caminho.relative_to(RAIZ)}: nao compila: {erro}")
            continue
        auditar_except(caminho, arvore)
        auditar_retorno_implicito(caminho, arvore)
        auditar_print_em_app(caminho, arvore)
        auditar_segredos(caminho)

    auditar_assets()
    auditar_contrato_de_rotas()
    auditar_nome_de_saida()
    if args.com_app:
        auditar_app_no_ar()

    print(json.dumps({"falhas": falhas, "avisos": avisos}, ensure_ascii=False, indent=1))
    print(f"\n{len(falhas)} falha(s), {len(avisos)} aviso(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
