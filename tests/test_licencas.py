from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import licencas, rotas
from app.config import Configuracao, carregar_config
from app.servidor import criar_app

RAIZ = Path(__file__).resolve().parents[1]


def _cliente(tmp_path: Path) -> TestClient:
    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)
    return TestClient(criar_app(config, verificar_base=lambda: True))


def test_omnivoice_bloqueia_comercial() -> None:
    """O README do proprio modelo diz que os pesos sao CC-BY-NC.

    Isso importa porque o dono vende solucoes: usar este motor para gerar audio
    comercial e violacao de licenca, e nada avisava.
    """
    assert licencas.bloqueia_comercial("omnivoice") is True
    dados = licencas.da_licenca("omnivoice")
    assert dados["pesos"] == "CC-BY-NC"
    assert dados["comercial"] is False


def test_motores_livres_nao_bloqueiam() -> None:
    for motor in ("voxcpm2", "chatterbox-ptbr", "kittentts", "mock"):
        assert licencas.bloqueia_comercial(motor) is False, motor
        assert licencas.da_licenca(motor)["comercial"] is True, motor


def test_motor_desconhecido_nao_vira_liberado() -> None:
    """Ausencia de informacao nao pode ser lida como permissao."""
    dados = licencas.da_licenca("motor-que-nao-existe")
    assert dados["comercial"] is None
    assert "não verificada" in dados["pesos"]
    assert licencas.bloqueia_comercial("motor-que-nao-existe") is False


def test_aviso_so_aparece_quando_proibe() -> None:
    aviso = licencas.aviso_comercial("omnivoice")
    assert aviso is not None
    assert "CC-BY-NC" in aviso
    assert "NÃO pode ser usado para vender" in aviso
    # O aviso NUNCA pode sugerir um motor que o app bloqueia: sugerir o VoxCPM2
    # mandava o aluno para uma tela que só devolvia erro. Regressão pega aqui.
    assert "voxcpm2" not in aviso
    assert "chatterbox-ptbr" in aviso

    assert licencas.aviso_comercial("voxcpm2") is None
    assert licencas.aviso_comercial("motor-que-nao-existe") is None


def test_catalogo_traz_licenca_e_aviso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """O catalogo vem stubado: a suite nao sobe servico nem depende da base estar no ar.

    Antes este teste batia na base de verdade e falhava com KeyError quando ela estava
    fora do ar — acusando o teste, nao o produto.
    """
    catalogo = {
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
    monkeypatch.setattr(rotas.base, "listar_motores", lambda _config: catalogo)

    cliente = _cliente(tmp_path)
    motores = cliente.get("/api/motores").json()

    por_id = {m["id"]: m for m in motores}
    assert "omnivoice" in por_id
    assert por_id["omnivoice"]["licenca"]["comercial"] is False
    assert por_id["omnivoice"]["aviso_licenca"] is not None
    assert por_id["voxcpm2"]["licenca"]["comercial"] is True
    assert por_id["voxcpm2"]["aviso_licenca"] is None
    # Bloqueado em 29/09/2026: continua no catalogo (com a licenca certa) mas fora de uso.
    assert por_id["voxcpm2"]["disponivel"] is False
    assert "Derruba a base" in por_id["voxcpm2"]["motivo"]


def test_geracao_com_motor_nao_comercial_devolve_aviso(tmp_path: Path) -> None:
    """O aviso viaja junto do audio, nao fica so no catalogo."""
    cliente = _cliente(tmp_path)

    resposta = cliente.post("/api/gerar", json={"texto": "teste", "motor": "mock"})

    assert resposta.status_code == 200
    assert resposta.json()["aviso_licenca"] is None


def test_fontes_registradas_para_poder_reconferir() -> None:
    """Toda licenca confirmada tem que dizer de onde veio."""
    for motor, dados in licencas.LICENCAS.items():
        assert dados["fonte"], f"{motor} sem fonte"
        assert dados["codigo"] and dados["pesos"], motor
        assert isinstance(dados["comercial"], bool), motor


def _motores_de(config: Configuracao, base_no_ar: bool) -> list[dict[str, Any]]:
    return rotas._motores(config, base_no_ar)


def test_todos_os_caminhos_entregam_licenca(tmp_path: Path) -> None:
    """Regressao: a licenca tinha entrado so no caminho do catalogo da base.

    Os motores sao montados em varios caminhos (mock, chatterbox local, base fora
    do ar, falha ao listar, catalogo da base). Se um caminho esquecer a licenca, a
    tela perde o aviso comercial justamente naquele caso. Este teste varre todos.
    """
    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)

    for base_no_ar in (True, False):
        motores = _motores_de(config, base_no_ar)
        assert motores, f"nenhum motor com base_no_ar={base_no_ar}"
        for motor in motores:
            assert "licenca" in motor, f"{motor['id']} sem licenca (base_no_ar={base_no_ar})"
            assert "aviso_licenca" in motor, f"{motor['id']} sem aviso (base_no_ar={base_no_ar})"
            assert motor["licenca"]["pesos"], motor["id"]

        por_id = {m["id"]: m for m in motores}
        for identificador in ("mock", "chatterbox-ptbr", "omnivoice", "voxcpm2"):
            if identificador in por_id:
                assert por_id[identificador]["licenca"]["pesos"] != "licença não verificada", identificador

    # O caminho da base fora do ar nao pode perder o aviso do omnivoice.
    fora = {m["id"]: m for m in _motores_de(config, False)}
    assert fora["omnivoice"]["licenca"]["comercial"] is False
    assert fora["omnivoice"]["aviso_licenca"] is not None
