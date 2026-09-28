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


@pytest.mark.parametrize("caminho", ["scripts/subir-base.ps1", "scripts/ligar-tudo.ps1"])
def test_base_sobe_em_modo_offline(caminho: str) -> None:
    """Regressao: sem isto a base consulta o HuggingFace a cada geracao.

    Medido em 28/09/2026 com as conexoes do Windows sendo observadas: no modo
    padrao a geracao abre uma conexao HTTPS externa, e com as tres variaveis
    ficam zero, com a geracao identica. Em ligar-tudo a definicao precisa estar
    dentro do Start-Job, senao nao chega no processo filho.
    """
    texto = (RAIZ / caminho).read_text(encoding="utf-8")
    uvicorn = texto.find("uvicorn backend.main:app")
    assert uvicorn > 0, f"nao achei o uvicorn em {caminho}"

    inicio = texto.find("Start-Job") if "ligar-tudo" in caminho else 0
    assert inicio >= 0, f"nao achei o Start-Job em {caminho}"

    for variavel in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
        posicao = texto.find(f"$env:{variavel}", inicio)
        assert posicao > inicio, f"{variavel} ausente em {caminho}"
        assert posicao < uvicorn, f"{variavel} precisa vir antes do uvicorn em {caminho}"
