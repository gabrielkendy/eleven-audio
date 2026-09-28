"""Resolve o ffmpeg mesmo quando o PATH do processo está incompleto.

Existe por um defeito real encontrado em 28/09/2026: o ffmpeg está no PATH do
usuário, em `WinGet\\Links`, e o app não achava o programa quando iniciado por
caminhos que não herdam esse PATH. A rota de qualidade da referência devolvia
"não foi possível analisar" sem dizer o motivo, e o preparo da amostra degradava
em silêncio, que é justamente o que mais melhora a clonagem.

Agora procuramos em ordem: PATH do processo, caminhos conhecidos de instalação no
Windows, e por último o PATH do usuário lido do registro. Se não achar, o erro
diz exatamente o que instalar.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class ErroFfmpeg(RuntimeError):
    """Falta o ffmpeg, ou ele não responde."""


# Caminhos usados pelos instaladores mais comuns no Windows. A ordem importa:
# o primeiro que existir vence. Todos são montados a partir de variáveis de
# ambiente, nunca escritos como caminho absoluto fixo: o projeto tem teste que
# proíbe caminho chumbado, e a regra existe para o pacote não depender do layout
# da máquina de quem instalou.
CANDIDATOS_WINDOWS = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
    Path(os.environ.get("ProgramData", "")) / "chocolatey" / "bin" / "ffmpeg.exe",
    Path(os.environ.get("USERPROFILE", "")) / "scoop" / "shims" / "ffmpeg.exe",
    Path(os.environ.get("ProgramFiles", "")) / "ffmpeg" / "bin" / "ffmpeg.exe",
    Path(os.environ.get("ProgramFiles(x86)", "")) / "ffmpeg" / "bin" / "ffmpeg.exe",
)

INSTRUCAO = (
    "O ffmpeg não foi encontrado. Ele é obrigatório: é quem corta o silêncio e "
    "mede a duração da sua amostra de voz, e isso é o que mais melhora a clonagem. "
    "Instale com 'winget install Gyan.FFmpeg' e abra o estúdio de novo."
)

_cache: str | None = None


def _caminhos_de_busca() -> list[str]:
    """PATH do processo mais o PATH do usuário, para não depender de herança."""
    caminhos = [str(p) for p in (os.environ.get("PATH") or "").split(os.pathsep) if p]
    if os.name == "nt" and not any("WinGet" in c for c in caminhos):
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as chave:
                do_usuario, _ = winreg.QueryValueEx(chave, "Path")
            caminhos.extend(c for c in str(do_usuario).split(os.pathsep) if c)
        except (ImportError, OSError):
            pass
    return caminhos


def executavel() -> str:
    """Caminho do ffmpeg, com resultado guardado. Levanta ErroFfmpeg se faltar."""
    global _cache
    if _cache:
        return _cache

    achado = shutil.which("ffmpeg")
    if achado:
        _cache = achado
        return achado

    for candidato in CANDIDATOS_WINDOWS:
        if candidato.is_file():
            _cache = str(candidato)
            return _cache

    achado = shutil.which("ffmpeg", path=os.pathsep.join(_caminhos_de_busca()))
    if achado:
        _cache = achado
        return achado

    raise ErroFfmpeg(INSTRUCAO)


def disponivel() -> tuple[bool, str]:
    """Para a tela: se está achado, e o motivo em texto quando não está."""
    try:
        return True, executavel()
    except ErroFfmpeg as erro:
        return False, str(erro)


def versao() -> str | None:
    """Primeira linha da versão, ou None quando não dá para perguntar."""
    try:
        processo = subprocess.run([executavel(), "-version"], capture_output=True,
                                  timeout=30, check=False)
    except (ErroFfmpeg, OSError, subprocess.TimeoutExpired):
        return None
    if processo.returncode:
        return None
    return processo.stdout.decode("utf-8", "replace").splitlines()[0][:120] or None
