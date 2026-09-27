from __future__ import annotations

import io
import json
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import ClassVar

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Configuracao
from app.rotas_desenhar import criar_router


def _wav() -> bytes:
    saida = io.BytesIO()
    with wave.open(saida, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8_000)
        audio.writeframes(b"\0\0" * 8_000)
    return saida.getvalue()


class _BaseFalsa(BaseHTTPRequestHandler):
    disponivel = True
    pedidos: ClassVar[list[tuple[str, bytes]]] = []

    def _json(self, valor: object, status: int = 200) -> None:
        corpo = json.dumps(valor).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:
        if self.path == "/engines/tts":
            self._json(
                {
                    "backends": [
                        {
                            "id": "voxcpm2",
                            "available": self.disponivel,
                            "reason": None if self.disponivel else "Pacote VoxCPM2 nao instalado.",
                            "effective_device": "cuda",
                        }
                    ]
                }
            )
        elif self.path == "/health":
            self._json({"device": "cuda (teste)"})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        corpo = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.pedidos.append((self.path, corpo))
        if self.path == "/design/describe":
            self._json(
                {
                    "attrs": {"Gender": "female", "Age": "elderly"},
                    "instruct": "female, elderly",
                }
            )
        elif self.path == "/profiles":
            self._json({"id": "perfil-base-1"})
        elif self.path == "/generate":
            corpo = _wav()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def _cliente(tmp_path: Path, disponivel: bool = True) -> tuple[TestClient, ThreadingHTTPServer]:
    _BaseFalsa.disponivel = disponivel
    _BaseFalsa.pedidos = []
    base = ThreadingHTTPServer(("127.0.0.1", 0), _BaseFalsa)
    Thread(target=base.serve_forever, daemon=True).start()
    config = Configuracao(
        porta=7804,
        motor="voxcpm2",
        dados=tmp_path / "dados",
        saidas=tmp_path / "saidas" / "audio",
        base_url=f"http://127.0.0.1:{base.server_address[1]}",
        timeout_s=5,
    )
    app = FastAPI()
    app.include_router(criar_router(config))
    return TestClient(app), base


def test_desenhar_cria_perfil_wav_e_registros(tmp_path: Path) -> None:
    cliente, base = _cliente(tmp_path)
    try:
        resposta = cliente.post(
            "/api/desenhar",
            json={
                "descricao": "Uma narradora idosa de voz grave.",
                "texto_previa": "A mesma frase para comparar as vozes.",
                "motor": "voxcpm2",
            },
        )
        assert resposta.status_code == 200, resposta.text
        resultado = resposta.json()
        assert set(resultado) == {
            "perfil_id",
            "id_na_base",
            "arquivo",
            "duracao_audio_s",
            "duracao_geracao_s",
        }
        assert resultado["id_na_base"] == "perfil-base-1"
        assert resultado["duracao_audio_s"] == 1.0
        assert (tmp_path / resultado["arquivo"]).is_file()

        assert [pedido[0] for pedido in _BaseFalsa.pedidos] == [
            "/design/describe",
            "/profiles",
            "/generate",
        ]
        assert b"female" in _BaseFalsa.pedidos[0][1]
        assert b"elderly" in _BaseFalsa.pedidos[0][1]
        assert b"low pitch" in _BaseFalsa.pedidos[0][1]
        assert b'name="kind"' in _BaseFalsa.pedidos[1][1]
        assert b"design" in _BaseFalsa.pedidos[1][1]
        assert b'name="vd_states"' in _BaseFalsa.pedidos[1][1]
        assert b'name="engine"' in _BaseFalsa.pedidos[2][1]

        desenhos = cliente.get("/api/desenhos").json()
        assert desenhos[0]["id"] == resultado["perfil_id"]
        assert desenhos[0]["descricao_desenho"] == "Uma narradora idosa de voz grave."
        assert desenhos[0]["total_geracoes"] == 1
    finally:
        base.shutdown()
        base.server_close()


def test_desenhar_devolve_motivo_literal_do_motor_indisponivel(tmp_path: Path) -> None:
    cliente, base = _cliente(tmp_path, disponivel=False)
    try:
        resposta = cliente.post(
            "/api/desenhar",
            json={"descricao": "Voz jovem", "texto_previa": "Teste", "motor": "voxcpm2"},
        )
        assert resposta.status_code == 409
        assert resposta.json()["detail"] == "Pacote VoxCPM2 nao instalado."
        assert _BaseFalsa.pedidos == []
    finally:
        base.shutdown()
        base.server_close()


def test_desenhar_rejeita_texto_vazio(tmp_path: Path) -> None:
    cliente, base = _cliente(tmp_path)
    try:
        resposta = cliente.post(
            "/api/desenhar",
            json={"descricao": "   ", "texto_previa": "Teste", "motor": "voxcpm2"},
        )
        assert resposta.status_code == 422
        assert _BaseFalsa.pedidos == []
    finally:
        base.shutdown()
        base.server_close()
