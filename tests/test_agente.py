from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agente import Agente, ErroAgente
from app.cofre import abrir
from app.config import carregar_config
from app.rotas_agente import criar_router


class _BaseHandler(BaseHTTPRequestHandler):
    vinculos: ClassVar[dict[str, dict[str, str | None]]] = {}
    ultimo_corpo: ClassVar[dict[str, str | None]] = {}

    def _json(self, status: int, corpo: object) -> None:
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self) -> None:
        if self.path == "/api/mcp/bindings":
            self._json(200, list(self.vinculos.values()))
        elif self.path == "/engines/tts":
            self._json(
                200,
                {
                    "active": "omnivoice",
                    "backends": [{"id": "omnivoice", "available": True}],
                },
            )
        else:
            self._json(404, {"detail": "rota ausente"})

    def do_PUT(self) -> None:
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).ultimo_corpo = corpo
        type(self).vinculos[corpo["client_id"]] = corpo
        self._json(200, corpo)

    def do_DELETE(self) -> None:
        cliente_id = self.path.rsplit("/", 1)[-1]
        removido = type(self).vinculos.pop(cliente_id, None)
        if removido is None:
            # Comportamento medido na base real em 28/09/2026: apagar vinculo
            # inexistente devolve 404, nao 200. A versao antiga deste simulador
            # respondia 200 sempre, e por isso a suite nunca pegou o defeito de o
            # desligar virar 502 na segunda tentativa. Simulador mais tolerante
            # que a realidade esconde erro.
            self._json(404, {"detail": "No binding for that client id"})
            return
        self._json(200, {"deleted": True})

    def log_message(self, format: str, *args: object) -> None:
        return


def _base() -> tuple[ThreadingHTTPServer, Thread]:
    _BaseHandler.vinculos = {}
    _BaseHandler.ultimo_corpo = {}
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _BaseHandler)
    thread = Thread(target=servidor.serve_forever)
    thread.start()
    return servidor, thread


def _servico(tmp_path: Path, base_url: str) -> tuple[Agente, str]:
    config = carregar_config(
        {
            "ESTUDIO_BASE_URL": base_url,
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_MOTOR": "omnivoice",
        },
        raiz=tmp_path,
    )
    cofre = abrir(config.dados / "estudio.db")
    try:
        perfil_id = cofre.salvar_perfil(
            nome="Voz local",
            origem="clonado",
            id_na_base="perfil-base-1",
        )
    finally:
        cofre.fechar()
    return Agente(config), perfil_id


def test_ligar_status_e_desligar_espelham_base_e_sqlite(tmp_path: Path) -> None:
    servidor, thread = _base()
    try:
        servico, perfil_id = _servico(
            tmp_path, f"http://127.0.0.1:{servidor.server_address[1]}"
        )

        ligado = servico.ligar("codex-local", perfil_id)
        assert ligado["estado"] == "ligado"
        assert _BaseHandler.ultimo_corpo == {
            "client_id": "codex-local",
            "label": "codex-local",
            "profile_id": "perfil-base-1",
            "default_engine": "omnivoice",
        }
        status = servico.status()
        assert status["mcp"]["estado"] == "ok"
        assert status["vinculos_base"][0]["client_id"] == "codex-local"
        assert status["vinculos_locais"][0]["perfil_id"] == perfil_id
        assert status["motores"]["active"] == "omnivoice"

        assert servico.desligar("codex-local")["estado"] == "desligado"
        assert servico.status()["vinculos_base"] == []
        assert servico.status()["vinculos_locais"] == []
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()


def test_desligar_duas_vezes_nao_e_erro(tmp_path: Path) -> None:
    """Regressao: desligar sem vinculo devolvia 502 Bad Gateway.

    Nada estava quebrado, so nao havia vinculo a desfazer, e a base responde 404
    nesse caso. Como o 404 era traduzido para 502, a segunda tentativa de desligar
    parecia falha de comunicacao e ainda deixava o vinculo local para tras. Agora
    desligar e idempotente, igual ao ligar, que ja usa PUT.
    """
    servidor, thread = _base()
    try:
        servico, perfil_id = _servico(
            tmp_path, f"http://127.0.0.1:{servidor.server_address[1]}"
        )

        servico.ligar("cliente-repetido", perfil_id)
        assert servico.desligar("cliente-repetido")["estado"] == "desligado"

        segunda = servico.desligar("cliente-repetido")
        assert segunda["estado"] == "desligado"
        assert segunda["cliente_id"] == "cliente-repetido"

        terceira = servico.desligar("cliente-repetido")
        assert terceira["estado"] == "desligado"
        assert servico.status()["vinculos_locais"] == []
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()


def test_erro_do_agente_carrega_o_codigo(tmp_path: Path) -> None:
    """Quem chama precisa decidir pelo codigo, nao por texto de mensagem."""
    servidor, thread = _base()
    try:
        servico, _ = _servico(
            tmp_path, f"http://127.0.0.1:{servidor.server_address[1]}"
        )

        with pytest.raises(ErroAgente) as capturado:
            servico._requisitar("GET", "/rota-que-nao-existe")

        assert capturado.value.status == 404
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()


def test_status_offline_mantem_vinculos_locais_e_motivo_em_portugues(
    tmp_path: Path,
) -> None:
    servico, perfil_id = _servico(tmp_path, "http://127.0.0.1:1")
    cofre = abrir(servico.config.dados / "estudio.db")
    try:
        cofre.salvar_vinculo(cliente_id="agente-offline", perfil_id=perfil_id)
    finally:
        cofre.fechar()

    status = servico.status()

    assert status["mcp"]["estado"] == "erro"
    assert status["mcp"]["motivo"].startswith("Servidor MCP da base indisponível:")
    assert status["vinculos_base"] == []
    assert status["vinculos_locais"][0]["cliente_id"] == "agente-offline"


def test_router_expoe_contrato_e_valida_perfil(tmp_path: Path) -> None:
    servidor, thread = _base()
    try:
        servico, perfil_id = _servico(
            tmp_path, f"http://127.0.0.1:{servidor.server_address[1]}"
        )
        app = FastAPI()
        app.include_router(criar_router(servico))
        cliente = TestClient(app)

        assert cliente.get("/api/agente/status").status_code == 200
        assert (
            cliente.post(
                "/api/agente/ligar", json={"cliente_id": "cli", "perfil_id": perfil_id}
            ).status_code
            == 200
        )
        assert (
            cliente.post("/api/agente/desligar", json={"cliente_id": "cli"}).status_code
            == 200
        )
        erro = cliente.post(
            "/api/agente/ligar", json={"cliente_id": "cli", "perfil_id": "inexistente"}
        )
        assert erro.status_code == 400
        assert (
            erro.json()["detail"] == "Perfil de voz local não encontrado: inexistente"
        )
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()


def test_area_web_tem_comandos_toml_json_e_estados() -> None:
    codigo = (Path(__file__).parents[1] / "web" / "agente.js").read_text(
        encoding="utf-8"
    )

    assert 'id: "agente"' in codigo
    assert "/api/agente/status" in codigo
    assert "/api/agente/ligar" in codigo
    assert "/api/agente/desligar" in codigo
    assert "X-OmniVoice-Client-Id" in codigo
    assert "http://127.0.0.1:3900/mcp/" in codigo
    assert "mcp_servers.estudio" in codigo
    assert '"mcpServers"' in codigo
    for estado in ("Carregando", "Nenhum vínculo ativo", "Erro"):
        assert estado in codigo
