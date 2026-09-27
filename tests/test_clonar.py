from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clonar import AVISO_CONSENTIMENTO, apagar_perfil, criar_perfil, listar_perfis
from app.config import carregar_config
from app.rotas_clonar import router


def _wav(caminho: Path, segundos: float = 10) -> Path:
    taxa = 8_000
    with wave.open(str(caminho), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa)
        arquivo.writeframes(
            b"".join(
                struct.pack("<h", int(4_000 * math.sin(2 * math.pi * 220 * i / taxa)))
                for i in range(int(taxa * segundos))
            )
        )
    return caminho


def _config(tmp_path: Path):
    return carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_BASE_URL": "http://base.local"},
        raiz=tmp_path,
    )


def test_router_bloqueia_sem_consentimento_e_nao_cria_nada(tmp_path: Path) -> None:
    config = _config(tmp_path)
    app = FastAPI()
    app.state.configuracao_clonar = config
    app.include_router(router)

    resposta = TestClient(app).post(
        "/api/clonar",
        data={"nome": "Minha voz", "origem_voz": "propria", "aceite_consentimento": "false"},
        files={"arquivo_referencia": ("voz.wav", _wav(tmp_path / "voz.wav").read_bytes(), "audio/wav")},
    )

    assert resposta.status_code == 409
    assert "consentimento" in resposta.json()["detail"].lower()
    assert not (config.dados / "referencias").exists()
    assert not (config.dados / "estudio.db").exists()


def test_cria_perfil_transcreve_grava_consentimento_e_apaga_dos_dois_lados(tmp_path: Path) -> None:
    config = _config(tmp_path)
    chamadas: list[tuple[str, str]] = []

    def base(request: httpx.Request) -> httpx.Response:
        chamadas.append((request.method, request.url.path))
        if request.url.path == "/transcribe":
            return httpx.Response(200, json={"text": "Esta e a transcricao automatica.", "engine": "mock-asr"})
        if request.method == "POST" and request.url.path == "/profiles":
            corpo = request.content.decode("latin1")
            assert 'name="kind"' in corpo and "clone" in corpo
            assert 'name="ref_text"' in corpo and "transcricao automatica" in corpo
            return httpx.Response(200, json={"id": "base-voz-1"})
        if request.url.path == "/profiles/base-voz-1/consent":
            corpo = request.content.decode("latin1")
            assert 'name="consent_audio"' in corpo
            assert 'name="consent_text"' in corpo
            return httpx.Response(200, json={"ok": True})
        if request.method == "DELETE" and request.url.path == "/profiles/base-voz-1":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(500, text="rota inesperada")

    with httpx.Client(transport=httpx.MockTransport(base), base_url=config.base_url) as cliente:
        criado = criar_perfil(
            config,
            nome="Minha voz",
            nome_arquivo="voz.wav",
            conteudo=_wav(tmp_path / "voz.wav").read_bytes(),
            transcricao="",
            origem_voz="propria",
            aceite_consentimento=True,
            cliente=cliente,
        )

        perfis = listar_perfis(config)
        assert criado["id_na_base"] == "base-voz-1"
        assert criado["aviso"] == AVISO_CONSENTIMENTO
        assert perfis[0]["transcricao_referencia"] == "Esta e a transcricao automatica."
        assert perfis[0]["consentimento_origem"] == "propria"
        referencia = config.dados / "referencias" / Path(perfis[0]["arquivo_referencia"]).name
        assert referencia.exists()

        apagado = apagar_perfil(config, criado["perfil_id"], cliente=cliente)
        assert apagado == {"apagado": criado["perfil_id"]}
        assert listar_perfis(config) == []
        assert not referencia.exists()

    assert chamadas == [
        ("POST", "/transcribe"),
        ("POST", "/profiles"),
        ("POST", "/profiles/base-voz-1/consent"),
        ("DELETE", "/profiles/base-voz-1"),
    ]


def test_rejeita_clipe_fora_de_cinco_a_quinze_segundos(tmp_path: Path) -> None:
    config = _config(tmp_path)
    app = FastAPI()
    app.state.configuracao_clonar = config
    app.include_router(router)

    resposta = TestClient(app).post(
        "/api/clonar",
        data={
            "nome": "Curta",
            "origem_voz": "autorizada",
            "aceite_consentimento": "true",
            "transcricao": "Oi",
        },
        files={"arquivo_referencia": ("curta.wav", _wav(tmp_path / "curta.wav", 4).read_bytes(), "audio/wav")},
    )

    assert resposta.status_code == 400
    assert "5 a 30 segundos" in resposta.json()["detail"]
    assert listar_perfis(config) == []


def test_interface_contem_area_clonar_e_texto_literal() -> None:
    javascript = Path("web/clonar.js").read_text(encoding="utf-8")

    assert 'id: "clonar"' in javascript
    assert "Antes de clonar, confirme: esta voz e sua" in javascript
    assert "/api/clonar" in javascript
    assert "/api/perfis" in javascript
    assert "MediaRecorder" in javascript
    assert "Carregando" in javascript
    assert "Nenhum perfil" in javascript
    assert "Erro" in javascript
