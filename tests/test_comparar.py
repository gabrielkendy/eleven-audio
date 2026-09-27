from __future__ import annotations

import wave
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cofre import abrir
from app.comparar import comparar
from app.config import carregar_config
from app.rotas_comparar import criar_router


def _config(tmp_path: Path):
    return carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas/audio",
            "ESTUDIO_BASE_URL": "http://127.0.0.1:3900",
        },
        raiz=tmp_path,
    )


def _perfil(config) -> str:
    cofre = abrir(config.dados / "estudio.db")
    try:
        return cofre.salvar_perfil(nome="Voz teste", origem="desenhado", id_na_base="base-voz-1")
    finally:
        cofre.fechar()


def _wav() -> bytes:
    import io

    saida = io.BytesIO()
    with wave.open(saida, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24_000)
        audio.writeframes(b"\0\0" * 2_400)
    return saida.getvalue()


def test_compara_mock_e_real_e_liga_os_registros(tmp_path: Path) -> None:
    config = _config(tmp_path)
    perfil_id = _perfil(config)

    def base(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/engines/tts":
            return httpx.Response(
                200,
                json={
                    "backends": [
                        {"id": "omnivoice", "available": True, "effective_device": "cuda"}
                    ]
                },
            )
        if request.url.path == "/generate":
            corpo = request.read().decode(errors="ignore")
            assert 'name="text"' in corpo
            assert 'name="profile_id"' in corpo and "base-voz-1" in corpo
            assert 'name="engine"' in corpo and "omnivoice" in corpo
            return httpx.Response(200, json={"audio_url": "/audio/prova.wav"})
        if request.url.path == "/audio/prova.wav":
            return httpx.Response(200, content=_wav(), headers={"content-type": "audio/wav"})
        raise AssertionError(request.url)

    resultado = comparar(
        texto="A mesma frase nos dois motores.",
        perfil_id=perfil_id,
        motores=["mock", "omnivoice"],
        config=config,
        transporte=httpx.MockTransport(base),
    )

    assert len(resultado["arquivos"]) == 2
    assert {item["motor"] for item in resultado["arquivos"]} == {"mock", "omnivoice"}
    assert all(Path(item["caminho_absoluto"]).is_file() for item in resultado["arquivos"])
    assert all(item["duracao_audio_s"] > 0 for item in resultado["arquivos"])

    cofre = abrir(config.dados / "estudio.db")
    try:
        ids = cofre.ler_config(f"grupo_comparacao:{resultado['grupo_id']}")
        registros = [cofre.geracao(item) for item in ids]
        assert len(registros) == 2
        assert {item["texto_entrada"] for item in registros} == {"A mesma frase nos dois motores."}
        assert {item["perfil_id"] for item in registros} == {perfil_id}
    finally:
        cofre.fechar()


def test_router_preserva_motivo_literal_de_motor_indisponivel(tmp_path: Path) -> None:
    config = _config(tmp_path)
    perfil_id = _perfil(config)
    motivo = "This engine's package isn't installed yet."

    def base(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/engines/tts"
        return httpx.Response(
            200,
            json={"backends": [{"id": "voxcpm2", "available": False, "reason": motivo}]},
        )

    app = FastAPI()
    app.include_router(criar_router(config, transporte=httpx.MockTransport(base)))
    resposta = TestClient(app).post(
        "/api/comparar",
        json={"texto": "Uma frase.", "perfil_id": perfil_id, "motores": ["mock", "voxcpm2"]},
    )

    assert resposta.status_code == 409
    assert motivo in resposta.json()["detail"]


def test_get_devolve_o_par_salvo(tmp_path: Path) -> None:
    config = _config(tmp_path)
    perfil_id = _perfil(config)
    resultado = comparar(
        texto="Dois mocks seriam inválidos, então usamos nomes reais simulados.",
        perfil_id=perfil_id,
        motores=["mock", "omnivoice"],
        config=config,
        transporte=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"backends": [{"id": "omnivoice", "available": True, "effective_device": "cpu"}]},
            )
            if request.url.path == "/engines/tts"
            else httpx.Response(200, content=_wav(), headers={"content-type": "audio/wav"})
        ),
    )

    app = FastAPI()
    app.include_router(criar_router(config))
    resposta = TestClient(app).get(f"/api/comparar/{resultado['grupo_id']}")

    assert resposta.status_code == 200
    assert len(resposta.json()["arquivos"]) == 2


def test_area_web_registra_comparar_e_estados() -> None:
    codigo = Path("web/comparar.js").read_text(encoding="utf-8")
    assert 'id: "comparar"' in codigo
    assert "Carregando" in codigo
    assert "Nenhuma comparação" in codigo
    assert "erro" in codigo.lower()
    assert "/api/comparar" in codigo
