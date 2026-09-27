"""Regressões de integridade do pipeline; sem base, GPU ou dados reais."""

import io
import wave

import httpx
import pytest

from app import base, motor
from app.ajustes import normalizar
from app.config import carregar_config


def _pedido(semente=None, ajustes=None):
    return {
        "texto": "teste",
        "motor": "omnivoice",
        "perfil_id": None,
        "idioma": "pt",
        "velocidade": 1.0,
        "semente": semente,
        "ajustes": ajustes,
    }


@pytest.mark.parametrize(
    "semente,seed,esperado",
    [(7, "9", "7"), (0, "9", "0"), (None, "9", "9"), (7, "7", "7")],
)
def test_semente_explicita_tem_precedencia_sem_mutar_ajustes(semente, seed, esperado):
    ajustes = {"seed": seed, "num_step": "32"}
    assert base.montar_corpo(**_pedido(semente, ajustes))["seed"] == esperado
    assert ajustes == {"seed": seed, "num_step": "32"}


def _wav(quadros=240):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\0\0" * quadros)
    return buffer.getvalue()


def _config(tmp_path):
    return carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas"}, raiz=tmp_path
    )


@pytest.mark.parametrize(
    "conteudo", [b'{"audio_url":"/audio/a.wav"}', b"", b"RIFF", _wav()[:-2], _wav(0)]
)
def test_http_200_nao_basta_para_retornar_audio(monkeypatch, tmp_path, conteudo):
    cliente_original = httpx.Client
    transporte = httpx.MockTransport(
        lambda request: httpx.Response(200, content=conteudo)
    )
    monkeypatch.setattr(
        base.httpx,
        "Client",
        lambda **kwargs: cliente_original(transport=transporte, **kwargs),
    )
    with pytest.raises(base.ErroBase, match="WAV"):
        base.gerar_audio(_config(tmp_path), **_pedido())


def test_wav_valido_preserva_bytes_sem_exigir_content_type(monkeypatch, tmp_path):
    conteudo = _wav()
    cliente_original = httpx.Client
    transporte = httpx.MockTransport(
        lambda request: httpx.Response(200, content=conteudo)
    )
    monkeypatch.setattr(
        base.httpx,
        "Client",
        lambda **kwargs: cliente_original(transport=transporte, **kwargs),
    )
    assert base.gerar_audio(_config(tmp_path), **_pedido()) == conteudo


def test_motor_nao_grava_bytes_invalidos_mesmo_com_base_mockada(monkeypatch, tmp_path):
    monkeypatch.setattr(
        base, "gerar_audio", lambda *args, **kwargs: b'{"erro":"falhou"}'
    )
    with pytest.raises(base.ErroBase, match="WAV"):
        motor.sintetizar(
            "teste", motor="omnivoice", pasta_saida=tmp_path, config=_config(tmp_path)
        )
    assert not list(tmp_path.rglob("*.wav"))


def test_motor_nao_inventa_dispositivo_e_preserva_mock_bytes(monkeypatch, tmp_path):
    monkeypatch.setattr(base, "gerar_audio", lambda *args, **kwargs: _wav())
    resultado = motor.sintetizar(
        "teste", motor="omnivoice", pasta_saida=tmp_path, config=_config(tmp_path)
    )
    assert resultado["dispositivo"] == "nao_informado"
    assert resultado["duracao_audio_s"] == 0.01


@pytest.mark.parametrize("nome", ["num_step", "guidance_scale", "crossfade_ms", "seed"])
@pytest.mark.parametrize(
    "valor", [True, False, float("inf"), float("-inf"), float("nan"), "inf", "nan"]
)
def test_numericos_recusam_booleanos_e_nao_finitos(nome, valor):
    with pytest.raises(ValueError):
        normalizar({nome: valor})


@pytest.mark.parametrize(
    "nome", ["num_step", "max_chunk_chars", "crossfade_ms", "seed"]
)
@pytest.mark.parametrize("valor", [32.5, "32.5"])
def test_inteiros_nao_truncam(nome, valor):
    with pytest.raises(ValueError):
        normalizar({nome: valor})


def test_inteiros_preservam_precisao_e_aceitam_forma_decimal_exata():
    assert normalizar({"seed": "9007199254740993", "num_step": "32.0"}) == {
        "seed": "9007199254740993",
        "num_step": "32",
    }
