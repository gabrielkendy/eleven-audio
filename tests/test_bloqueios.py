"""Motores bloqueados de propósito: o app recusa antes de derrubar a base.

Medido em 29/09/2026: carregar o KittenTTS ou gerar com o VoxCPM2 derrubava a base
VoiceStudio inteira; o usuário só via "WinError 10054" e "base esta fora do ar". A
decisão do dono foi tirar os dois do caminho e deixar o que funciona.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import bloqueios, rotas
from app.config import carregar_config
from app.servidor import criar_app

CATALOGO = {
    "active": "omnivoice",
    "backends": [
        {
            "id": "omnivoice",
            "display_name": "OmniVoice",
            "available": True,
            "supports_cloning": True,
            "max_ref_seconds": 20.0,
            "ref_strategy": "best_window",
            "effective_device": "cuda",
        },
        {
            "id": "kittentts",
            "display_name": "KittenTTS",
            "available": True,
            "supports_cloning": False,
            "max_ref_seconds": None,
            "ref_strategy": None,
            "effective_device": "cpu",
        },
        {
            "id": "voxcpm2",
            "display_name": "VoxCPM2",
            "available": True,
            "supports_cloning": True,
            "max_ref_seconds": 30.0,
            "ref_strategy": "head",
            "effective_device": "cuda",
        },
    ],
}


def _cliente(tmp_path: Path) -> TestClient:
    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)
    return TestClient(criar_app(config, verificar_base=lambda: True))


def test_motivo_existe_para_os_problematicos_e_nao_para_o_bom() -> None:
    assert bloqueios.motivo("kittentts")
    assert bloqueios.motivo("voxcpm2")
    assert bloqueios.motivo("omnivoice") is None
    assert bloqueios.motivo("chatterbox-ptbr") is None


def test_catalogo_marca_os_bloqueados_como_indisponiveis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eles continuam listados (com licença), só que fora de uso e com o motivo."""
    monkeypatch.setattr(rotas.base, "listar_motores", lambda _config: CATALOGO)

    por_id = {m["id"]: m for m in _cliente(tmp_path).get("/api/motores").json()}

    assert por_id["omnivoice"]["disponivel"] is True
    for identificador in ("kittentts", "voxcpm2"):
        assert por_id[identificador]["disponivel"] is False, identificador
        assert por_id[identificador]["motivo"] == bloqueios.motivo(identificador)


def test_gerar_recusa_motor_bloqueado_sem_chamar_a_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def nao_deveria_ser_chamada(*_a, **_k):  # pragma: no cover - só falha o teste
        raise AssertionError("motor bloqueado chegou na base")

    monkeypatch.setattr(rotas.base, "listar_motores", lambda _config: CATALOGO)
    monkeypatch.setattr(rotas.base, "selecionar_motor", nao_deveria_ser_chamada)

    resposta = _cliente(tmp_path).post(
        "/api/gerar", json={"texto": "teste", "motor": "voxcpm2"}
    )

    assert resposta.status_code == 409
    assert "Derruba a base" in resposta.json()["detail"]


def test_desenhar_recusa_voxcpm2_em_vez_de_derrubar_a_base(tmp_path: Path) -> None:
    """O desenho de voz era a outra porta para o motor que mata a base."""
    resposta = _cliente(tmp_path).post(
        "/api/desenhar",
        json={"descricao": "narradora grave", "texto_previa": "teste", "motor": "voxcpm2"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == bloqueios.motivo("voxcpm2")
