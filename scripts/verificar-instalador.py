"""Verifica o instalador de 1 clique (pasta instalador/).

Por que existe separado do verificar-tudo.py: aquele cobre o APP rodando. Este
cobre o INSTALADOR, que e outro tipo de risco — ele roda em maquina alheia, uma
vez, sem ninguem olhando. Os defeitos aqui nao aparecem em teste de unidade:
aparecem como "nao achei o app" ou "a base nao respondeu" na maquina de quem
baixou.

Roda assim:

    env -u PYTHONPATH <venv>/Scripts/python.exe scripts/verificar-instalador.py

Sai com 0 se tudo passa, 1 se algo falha.

O QUE NAO DA PRA PROVAR AQUI, e esta escrito de proposito: o caminho de
instalacao em si — clonar a base, criar os dois ambientes do zero, baixar os
pesos. Isso exige maquina limpa. Este script prova o que da: sintaxe, deteccao de
maquina, e que os defeitos ja corrigidos nao voltaram.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
INSTALADOR = RAIZ_PROJETO / "instalador"

PS1 = ("instalar.ps1", "ABRIR.ps1", "FECHAR.ps1")
BAT = ("INSTALAR.bat", "SO-CONFERIR.bat", "ABRIR.bat", "FECHAR.bat")

# caminho de quem montou o pacote nao pode ir junto para a comunidade
PESSOAL = (r"Users\\Gabriel", r"YOUTUBE KENDY", r"\.venvs", r"SÉRIE")


class _SemRedirect(HTTPRedirectHandler):
    """Nao segue redirect: so devolve o codigo do primeiro salto.

    O urlopen padrao SEGUE redirect, igual ao Invoke-WebRequest do PowerShell. A
    raiz da base responde 307 e, seguindo, o pedido estoura e some — escondendo
    justamente o caso que derrubava o launcher. Mesmo defeito, dois idiomas.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_OPENER = build_opener(_SemRedirect)


def _powershell(comando: str, timeout: int = 300) -> str:
    proc = subprocess.run(
        ["powershell", "-NoLogo", "-NoProfile", "-Command", comando],
        capture_output=True, text=True, timeout=timeout,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def _parsear(nome: str) -> str:
    """Passa o arquivo pelo parser do proprio PowerShell."""
    alvo = str(INSTALADOR / nome)
    return _powershell(
        f"$e=$null;"
        f"[System.Management.Automation.Language.Parser]::ParseFile('{alvo}',[ref]$null,[ref]$e)"
        "|Out-Null;"
        "if($e){$e|ForEach-Object{$_.Extent.StartLineNumber.ToString()+': '+$_.Message}}else{'LIMPO'}"
    )


def _status(url: str, seguir: bool = True) -> int | None:
    try:
        abrir = urlopen if seguir else _OPENER.open
        with abrir(Request(url), timeout=20) as resposta:
            return resposta.status
    except HTTPError as erro:
        return erro.code
    except (URLError, OSError, ValueError):
        return None


def main() -> int:
    resultado: list[tuple[str, bool, str]] = []

    def conferir(nome: str, ok: bool, detalhe: str = "") -> None:
        resultado.append((nome, ok, detalhe))
        marca = "ok  " if ok else "FALHA"
        sufixo = f"   {detalhe}" if detalhe else ""
        print(f"  [{marca}] {nome}{sufixo}")

    print()
    print("=== 1. os arquivos do pacote ===")
    for nome in PS1 + BAT + ("LEIA-ME.md",):
        conferir(f"existe {nome}", (INSTALADOR / nome).exists())

    sujos = []
    for arquivo in INSTALADOR.rglob("*"):
        if arquivo.is_file() and arquivo.name != "local.ps1":
            texto = arquivo.read_text(encoding="utf-8", errors="replace")
            if any(re.search(p, texto) for p in PESSOAL):
                sujos.append(arquivo.name)
    conferir("nenhum caminho pessoal no pacote", not sujos, str(sujos))
    conferir("local.ps1 fora do pacote (nasce no destino)",
             not (INSTALADOR / "local.ps1").exists())

    print()
    print("=== 2. sintaxe, pelo parser do PowerShell ===")
    for nome in PS1:
        saida = _parsear(nome)
        conferir(f"parse {nome}", "LIMPO" in saida, saida.strip()[:110])

    print()
    print("=== 3. os defeitos ja corrigidos nao voltaram ===")
    instalar = (INSTALADOR / "instalar.ps1").read_text(encoding="utf-8")
    abrir = (INSTALADOR / "ABRIR.ps1").read_text(encoding="utf-8")
    fechar = (INSTALADOR / "FECHAR.ps1").read_text(encoding="utf-8")

    # o app e a pasta que CONTEM o instalador, nao uma subpasta de nome fixo
    conferir("app achado pelo pai de instalador/",
             "Split-Path -Parent $PSScriptRoot" in instalar)
    # a base instala por uv: o pip ignora o indice de CUDA e as travas do pyproject
    conferir("base instala por uv sync, nao por pip",
             "uv sync" in instalar and "pip install -e $script:PastaBase" not in instalar)
    conferir("uv escolhe o Python alvo", "PyAlvoBase" in instalar)
    # o instalador grava o local.ps1 onde o ABRIR procura
    conferir("local.ps1 gravado onde o ABRIR le",
             "$arqLocal = Join-Path $PSScriptRoot 'local.ps1'" in instalar)
    conferir("venv do app dentro da pasta do app",
             "$venvApp = Join-Path $script:PastaApp '.venv'" in instalar)
    # $pid e somente leitura no PowerShell
    conferir("nenhuma atribuicao a $pid (reservado)",
             not re.findall(r"^\s*\$pid\s*=", abrir + fechar, re.M))
    # sonda de saude certa, sem seguir redirect
    conferir("sonda /health e /api/saude, nao a raiz",
             "'/health'" in abrir and "'/api/saude'" in abrir)
    conferir("sonda nao segue redirect", "MaximumRedirection 0" in abrir)
    conferir("aceita resposta HTTP como servico vivo",
             "if ($_.Exception.Response) { return $true }" in abrir)

    print()
    print("=== 4. o instalador roda nesta maquina (-SoVerificar) ===")
    proc = subprocess.run(
        ["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(INSTALADOR / "instalar.ps1"), "-SoVerificar"],
        capture_output=True, text=True, timeout=300,
    )
    saida = (proc.stdout or "") + (proc.stderr or "")
    conferir("roda sem estourar", proc.returncode == 0, f"exit {proc.returncode}")
    conferir("passa pelos blocos de conferencia",
             all(m in saida for m in ("Windows", "arquitetura", "Git", "ffmpeg", "disco")))
    conferir("detecta a GPU", "GPU:" in saida)
    # o defeito que mais assusta: pegar o python de um venv de OUTRO programa
    conferir("nao escolhe Python de venv alheio",
             "hermes-agent" not in saida and ".venvs" not in saida)
    conferir("diz o que falta ou que esta pronto",
             ("falta:" in saida) or ("tem tudo" in saida))

    print()
    print("=== 5. a sonda de saude, contra os servicos vivos ===")
    base = _status("http://127.0.0.1:3900/health")
    app = _status("http://127.0.0.1:7800/api/saude")
    if base is None and app is None:
        print("  [ -- ] servicos fora do ar: sonda fica pendente")
        print("         (nao e falha do instalador; suba com instalador/ABRIR.bat)")
    else:
        conferir("base /health responde",
                 base is not None and 200 <= base < 500, f"HTTP {base}")
        conferir("app /api/saude responde",
                 app is not None and 200 <= app < 500, f"HTTP {app}")
        raiz = _status("http://127.0.0.1:3900/", seguir=False)
        conferir("raiz da base redireciona (o caso que derrubava o launcher)",
                 raiz in (301, 302, 303, 307, 308), f"HTTP {raiz}")

    falhas = [nome for nome, ok, _ in resultado if not ok]
    print()
    print("=" * 66)
    if falhas:
        print(f"  {len(resultado) - len(falhas)} de {len(resultado)} ok  -  FALHAS:")
        for nome in falhas:
            print(f"    - {nome}")
    else:
        print(f"  {len(resultado)} de {len(resultado)} ok")
    print("=" * 66)
    print()
    print("  ESCOPO: isto e verificacao ad-hoc, nao suite verde. O instalador nao tem")
    print("  teste automatizado, e o caminho de INSTALACAO (clonar a base, criar os")
    print("  ambientes do zero, baixar os pesos) depende de maquina limpa. Coberto:")
    print("  sintaxe, deteccao de maquina, sonda de saude e os defeitos conhecidos.")
    print()
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
