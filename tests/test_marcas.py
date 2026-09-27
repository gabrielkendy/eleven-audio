"""Marcas de expressão por motor: a lista certa e o aviso quando a marca não vale."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import carregar_config
from app.marcas import (
    PAUSAS,
    REACOES_PADRAO,
    conferir,
    marcas_do_motor,
    marcas_no_texto,
)
from app.servidor import criar_app


def _cliente(tmp_path: Path) -> TestClient:
    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)
    return TestClient(criar_app(config, verificar_base=lambda: True))


def test_motor_padrao_tem_as_treze_reacoes_e_as_pausas() -> None:
    marcas = marcas_do_motor("omnivoice")

    assert len(REACOES_PADRAO) == 13
    for marca in (*PAUSAS, *REACOES_PADRAO):
        assert marca in marcas


def test_motor_sem_lista_propria_so_aceita_pausas() -> None:
    assert marcas_do_motor("motor-que-nao-existe") == PAUSAS
    assert marcas_do_motor(None) == PAUSAS
    assert marcas_do_motor("voxcpm2") == PAUSAS
    assert "[breath]" in marcas_do_motor("cosyvoice")
    assert "[breath]" not in marcas_do_motor("omnivoice")


def test_marcas_no_texto_sem_repetir_e_na_ordem() -> None:
    texto = "Oi [laughter] de novo [pause 500ms] e [laughter] fim"

    assert marcas_no_texto(texto) == ["[laughter]", "[pause 500ms]"]


def test_conferir_avisa_quando_a_marca_nao_vale_para_o_motor() -> None:
    relatorio = conferir("Tudo certo [breath] agora", "omnivoice")

    assert relatorio["invalidas"] == ["[breath]"]
    assert relatorio["aviso"] is not None
    assert "[breath]" in relatorio["aviso"] or "voz alta" in relatorio["aviso"]


def test_conferir_sem_marca_invalida_nao_avisa() -> None:
    relatorio = conferir("Boa noite [pause 1s] e boa sorte", "omnivoice")

    assert relatorio["invalidas"] == []
    assert relatorio["aviso"] is None
    assert relatorio["validas"] == ["[pause 1s]"]


def test_rota_de_marcas_responde_com_o_motor_pedido(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)

    resposta = cliente.get("/api/marcas", params={"motor": "cosyvoice", "texto": "oi [breath]"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["motor"] == "cosyvoice"
    assert "[breath]" in corpo["marcas"]
    assert corpo["invalidas"] == []


def test_rota_de_marcas_usa_o_motor_ativo_quando_nao_pede_nenhum(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    cliente.post("/api/motores/ativo", json={"motor": "omnivoice"})

    corpo = cliente.get("/api/marcas").json()

    assert corpo["motor"] == "omnivoice"
    assert "[laughter]" in corpo["marcas"]
