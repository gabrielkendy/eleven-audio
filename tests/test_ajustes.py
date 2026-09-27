"""Controles de qualidade: validação, formulário para a base e prova na rota /api/gerar."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ajustes import normalizar, resumo
from app.base import montar_corpo
from app.config import carregar_config
from app.servidor import criar_app


def _cliente(tmp_path: Path) -> TestClient:
    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)
    return TestClient(criar_app(config, verificar_base=lambda: True))


def test_sem_ajustes_vale_o_padrao_da_base() -> None:
    assert normalizar(None) == {}
    assert normalizar({}) == {}
    assert normalizar({"num_step": None}) == {}


def test_numero_vira_texto_de_formulario() -> None:
    saida = normalizar({"num_step": 32, "guidance_scale": "2.5", "position_temperature": 7})

    assert saida == {"num_step": "32", "guidance_scale": "2.5", "position_temperature": "7.0"}


def test_fora_da_faixa_recusa_mostrando_o_limite() -> None:
    with pytest.raises(ValueError) as erro:
        normalizar({"num_step": 300})

    assert "entre 4 e 64" in str(erro.value)


def test_efeito_inventado_recusado() -> None:
    with pytest.raises(ValueError, match="efeito deve ser"):
        normalizar({"effect_preset": "reverb-magico"})


def test_ajuste_desconhecido_recusado() -> None:
    with pytest.raises(ValueError, match="desconhecido"):
        normalizar({"turbo": True})


def test_ajustes_de_tipo_errado_recusado() -> None:
    with pytest.raises(TypeError, match="objeto"):
        normalizar("num_step=32")


def test_booleano_aceita_formas_humanas() -> None:
    assert normalizar({"denoise": "nao"}) == {"denoise": "false"}
    assert normalizar({"denoise": True}) == {"denoise": "true"}
    assert normalizar({"postprocess_output": "off"}) == {"postprocess_output": "false"}


def test_montar_corpo_leva_ajustes_e_omite_semente_vazia() -> None:
    corpo = montar_corpo(
        texto="oi",
        motor="omnivoice",
        perfil_id="vz-1",
        idioma="pt",
        velocidade=1.0,
        semente=None,
        ajustes={"num_step": "32", "effect_preset": "podcast"},
    )

    assert corpo["text"] == "oi"
    assert corpo["engine"] == "omnivoice"
    assert corpo["profile_id"] == "vz-1"
    assert corpo["num_step"] == "32"
    assert corpo["effect_preset"] == "podcast"
    assert "seed" not in corpo


def test_resumo_traduz_para_portugues() -> None:
    texto = resumo({"effect_preset": "podcast", "num_step": "32", "denoise": "false"}, 1.5)

    assert "podcast" in texto
    assert "passos 32" in texto
    assert "desligada" in texto
    assert "1.5" in texto


def test_rota_gerar_aceita_ajustes_e_devolve_resumo(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)

    resposta = cliente.post(
        "/api/gerar",
        json={"texto": "teste curto de ajuste", "motor": "mock", "ajustes": {"effect_preset": "podcast", "num_step": 32}},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ajustes"] == {"effect_preset": "podcast", "num_step": "32"}
    assert "podcast" in corpo["resumo_ajustes"]
    with wave.open(corpo["arquivo"], "rb") as leitor:
        assert leitor.getframerate() == 24_000


def test_rota_gerar_recusa_ajuste_invalido(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)

    resposta = cliente.post("/api/gerar", json={"texto": "teste", "motor": "mock", "ajustes": {"num_step": 999}})

    assert resposta.status_code == 422
    assert "entre 4 e 64" in resposta.json()["detail"]
