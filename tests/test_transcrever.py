from __future__ import annotations

import io
import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cofre import abrir
from app.config import carregar_config
from app.rotas_transcrever import criar_router
from app.transcricao import ErroTranscricao, guardar_arquivo


class _BaseHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        tamanho = int(self.headers["Content-Length"])
        corpo = self.rfile.read(tamanho)
        assert self.path == "/transcribe"
        assert b'name="audio"; filename="' in corpo and b".wav" in corpo
        assert b'name="language"' in corpo and b"pt" in corpo
        if b"invalido.wav" in corpo:
            dados = b'{"detail":"formato WAV corrompido"}'
            self.send_response(415)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        resposta = {
            "text": "A fatia quatro transcreve audio de verdade.",
            "language": "pt",
            "engine": "pytorch-whisper",
        }
        dados = json.dumps(resposta).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _base_teste():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _BaseHandler)
    thread = Thread(target=servidor.serve_forever)
    thread.start()
    try:
        yield servidor.server_address[1]
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()


def _cliente(tmp_path: Path, porta: int) -> TestClient:
    config = carregar_config(
        {
            "ESTUDIO_BASE_URL": f"http://127.0.0.1:{porta}",
            "ESTUDIO_DADOS": "dados",
        },
        raiz=tmp_path,
    )
    app = FastAPI()
    app.include_router(criar_router(config))
    return TestClient(app)


def test_transcreve_grava_arquivo_e_historico(tmp_path: Path) -> None:
    with _base_teste() as porta, _cliente(tmp_path, porta) as cliente:
        resposta = cliente.post(
            "/api/transcrever",
            files={"arquivo": ("fala.wav", b"RIFF-audio-real", "audio/wav")},
            data={"idioma": "pt"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["texto"] == "A fatia quatro transcreve audio de verdade."
        assert resposta.json()["idioma_detectado"] == "pt"
        historico = cliente.get("/api/transcricoes")
        assert historico.status_code == 200
        assert historico.json()[0]["motor"] == "pytorch-whisper"

    cofre = abrir(tmp_path / "dados" / "estudio.db")
    try:
        registro = cofre.listar_transcricoes()[0]
        assert Path(registro["arquivo_entrada"]).is_file()
        assert registro["texto_saida"] == resposta.json()["texto"]
    finally:
        cofre.fechar()


def test_area_web_cobre_estados_e_acoes() -> None:
    script = (Path(__file__).parents[1] / "web" / "transcrever.js").read_text(encoding="utf-8")

    for trecho in (
        'id: "transcrever"',
        "/api/transcrever",
        "/api/transcricoes",
        "Transcrevendo",
        "Nenhuma transcrição",
        "Copiar",
        "navigator.clipboard",
    ):
        assert trecho in script


def test_erro_de_formato_fica_em_portugues_e_preserva_motivo(tmp_path: Path) -> None:
    with _base_teste() as porta, _cliente(tmp_path, porta) as cliente:
        resposta = cliente.post(
            "/api/transcrever",
            files={"arquivo": ("invalido.wav", b"nao-e-wav", "audio/wav")},
            data={"idioma": "pt"},
        )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Erro ao transcrever: formato WAV corrompido"


def test_upload_acima_do_limite_para_sem_deixar_arquivo_parcial(tmp_path: Path) -> None:
    with pytest.raises(ErroTranscricao, match="passa do limite"):
        guardar_arquivo(io.BytesIO(b"1234"), "grande.wav", tmp_path, limite_bytes=3)

    assert list((tmp_path / "transcricoes").glob("*")) == []
