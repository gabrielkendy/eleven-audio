from __future__ import annotations

import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from fastapi.testclient import TestClient

from app.base import saudavel
from app.config import carregar_config
from app.motor import sintetizar
from app.servidor import criar_app


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def log_message(self, format: str, *args: object) -> None:
        return


def test_configuracao_resolve_pastas_relativas_dentro_do_projeto(
    tmp_path: Path,
) -> None:
    config = carregar_config(
        {
            "ESTUDIO_DADOS": "estado",
            "ESTUDIO_SAIDAS": "renders",
            "ESTUDIO_MOTOR": "mock",
        },
        raiz=tmp_path,
    )

    assert config.dados == (tmp_path / "estado").resolve()
    assert config.saidas == (tmp_path / "renders").resolve()
    assert config.motor == "mock"
    assert config.base_url == "http://127.0.0.1:3900"
    assert config.porta == 7800


def test_motor_mock_grava_wav_pcm_valido_e_medido(tmp_path: Path) -> None:
    resultado = sintetizar(
        "Teste local da fatia zero.",
        motor="mock",
        pasta_saida=tmp_path,
    )
    arquivo = Path(resultado["arquivo"])

    assert arquivo.exists()
    assert "_mock_" in arquivo.name
    assert resultado["duracao_geracao_s"] >= 0
    assert resultado["tamanho_bytes"] == arquivo.stat().st_size
    with wave.open(str(arquivo), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 24_000
        assert wav.getnframes() / wav.getframerate() == resultado["duracao_audio_s"]


def test_cliente_da_base_consulta_health_em_loopback(tmp_path: Path) -> None:
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = Thread(target=servidor.serve_forever)
    thread.start()
    try:
        porta = servidor.server_address[1]
        config = carregar_config(
            {"ESTUDIO_BASE_URL": f"http://127.0.0.1:{porta}"},
            raiz=tmp_path,
        )

        assert saudavel(config) is True
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()


def test_api_saude_informa_app_base_e_disco(tmp_path: Path) -> None:
    config = carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"},
        raiz=tmp_path,
    )
    app = criar_app(config, verificar_base=lambda: True)

    resposta = TestClient(app).get("/api/saude")

    assert resposta.status_code == 200
    assert resposta.json()["nosso_app"] == "ok"
    assert resposta.json()["base"] == "ok"
    assert resposta.json()["disco_livre_gb"] >= 0


def test_fatia_zero_nao_expoe_clonagem_ou_consentimento_409(tmp_path: Path) -> None:
    config = carregar_config({}, raiz=tmp_path)
    app = criar_app(config, verificar_base=lambda: False)

    rotas = {rota.path for rota in app.routes}

    assert "/api/clonar" not in rotas
