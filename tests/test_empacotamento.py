from __future__ import annotations

import importlib.util
import re
import wave
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "caminho",
    ["scripts/ligar-tudo.ps1", "scripts/ligar-tudo.bat"],
)
def test_arquivos_do_atalho_existem(caminho: str) -> None:
    assert (RAIZ / caminho).is_file()


def test_bat_chama_o_powershell() -> None:
    conteudo = (RAIZ / "scripts/ligar-tudo.bat").read_text(encoding="utf-8")
    assert "ligar-tudo.ps1" in conteudo
    assert "-ExecutionPolicy Bypass" in conteudo


def test_guia_existe_e_cita_as_duas_portas_e_agpl() -> None:
    conteudo = (RAIZ / "GUIA-DE-USO.md").read_text(encoding="utf-8")
    assert "7800" in conteudo
    assert "3900" in conteudo
    assert "AGPL" in conteudo


def test_app_e_web_nao_tem_caminho_absoluto_chumbado() -> None:
    arquivos = [
        arquivo
        for pasta in (RAIZ / "app", RAIZ / "web")
        if pasta.exists()
        for arquivo in pasta.rglob("*")
        if arquivo.suffix in {".py", ".js", ".css", ".html"}
    ]
    encontrados = {
        str(arquivo.relative_to(RAIZ)): correspondencia.group(0)
        for arquivo in arquivos
        if (
            correspondencia := re.search(
                r"(?i)[\"'][a-z]:[\\/]", arquivo.read_text(encoding="utf-8")
            )
        )
    }
    assert encontrados == {}


def test_lista_de_licencas_aparece_na_configuracao() -> None:
    conteudo = (RAIZ / "web/config.js").read_text(encoding="utf-8")
    assert "LICENCAS" in conteudo
    assert "VoiceStudio" in conteudo
    assert "AGPL-3.0" in conteudo


def test_verificador_normaliza_motores_e_mede_wav(tmp_path: Path) -> None:
    caminho = RAIZ / "scripts/verificar-tudo.py"
    spec = importlib.util.spec_from_file_location("verificar_tudo", caminho)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    arquivo = tmp_path / "teste.wav"
    with wave.open(str(arquivo), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8_000)
        wav.writeframes(b"\0\0" * 4_000)

    assert modulo._nomes_motores(
        {
            "active": "omnivoice",
            "backends": [{"id": "omnivoice"}, {"name": "VoxCPM2"}],
        }
    ) == [
        "omnivoice",
        "VoxCPM2",
    ]
    assert modulo._duracao_wav(arquivo) == 0.5
