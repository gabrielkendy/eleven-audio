from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import carregar_config
from app.servidor import criar_app

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"


def _codigo(nome: str) -> str:
    return (WEB / nome).read_text(encoding="utf-8")


def test_as_quatro_areas_usam_as_classes_da_interface_alvo() -> None:
    desenhar = _codigo("desenhar.js")
    transcrever = _codigo("transcrever.js")
    comparar = _codigo("comparar.js")
    agente = _codigo("agente.js")
    todos = f"{desenhar}\n{transcrever}\n{comparar}\n{agente}"

    for classe in (
        "pílulas",
        "pílula",
        "player",
        "onda",
        "duplo",
        "grade-cartoes",
        "solte",
        "aviso",
    ):
        assert f'class="{classe}' in todos, f"classe ausente nas áreas de apoio: {classe}"

    assert 'class="pílulas"' in desenhar
    assert 'class="solte"' in transcrever
    assert 'class="duplo"' in comparar
    assert comparar.count('class="player"') >= 2
    assert 'class="grade-cartoes"' in comparar
    assert 'class="aviso"' in agente


def test_agente_exibe_passos_e_comandos_copiaveis() -> None:
    codigo = _codigo("agente.js")

    for passo in ("1. Escolher cliente e voz", "2. Ligar", "3. Colar o comando no agente"):
        assert passo in codigo
    assert "Codex (TOML)" in codigo
    assert "JSON" in codigo
    assert codigo.count(">Copiar<") >= 2
    assert "navigator.clipboard" in codigo


def test_app_responde_nas_rotas_usadas_pelas_areas(tmp_path: Path) -> None:
    config = carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"},
        raiz=tmp_path,
    )
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))

    for recurso in ("desenhar.js", "transcrever.js", "comparar.js", "agente.js"):
        assert cliente.get(f"/web/{recurso}").status_code == 200

    for rota in ("/api/motores", "/api/perfis", "/api/desenhos", "/api/transcricoes"):
        assert cliente.get(rota).status_code == 200

    for rota in (
        "/api/desenhar",
        "/api/transcrever",
        "/api/comparar",
        "/api/agente/ligar",
        "/api/agente/desligar",
    ):
        assert cliente.post(rota).status_code == 422

    caminhos = {rota.path for rota in cliente.app.routes}
    assert "/api/agente/status" in caminhos
