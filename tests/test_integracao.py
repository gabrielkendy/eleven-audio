"""Prova da integracao: as 20 rotas das fatias vivas no mesmo app e a tela monta as 7 areas."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.config import carregar_config
from app.servidor import criar_app

WEB = Path(__file__).resolve().parents[1] / "web"

ROTAS_ESPERADAS = {
    "/api/estado",
    "/api/motores",
    "/api/motores/ativo",
    "/api/gerar",
    "/api/gerar/{geracao_id}",
    "/api/saidas",
    "/api/saude",
    "/api/clonar",
    "/api/perfis",
    "/api/perfis/{perfil_id}",
    "/api/comparar",
    "/api/comparar/{grupo_id}",
    "/api/comparar/{grupo_id}/audio/{geracao_id}",
    "/api/desenhar",
    "/api/desenhos",
    "/api/transcrever",
    "/api/transcricoes",
    "/api/agente/status",
    "/api/agente/ligar",
    "/api/agente/desligar",
}

AREAS = ["gerar", "clonar", "comparar", "desenhar", "transcrever", "agente", "config"]


def _app(tmp_path: Path):
    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)
    return criar_app(config, verificar_base=lambda: True)


def test_app_expoe_as_vinte_rotas_das_fatias(tmp_path: Path) -> None:
    caminhos = {rota.path for rota in _app(tmp_path).routes}

    faltando = ROTAS_ESPERADAS - caminhos
    assert not faltando, f"rotas ausentes: {sorted(faltando)}"


def test_a_tela_serve_index_e_os_recursos_estaticos(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    cliente = TestClient(_app(tmp_path))
    pagina = cliente.get("/")

    assert pagina.status_code == 200
    assert "Estúdio de Voz Local" in pagina.text
    assert cliente.get("/web/app.js").status_code == 200


def test_index_inicaliza_areas_como_lista_e_carrega_todas_as_areas() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert "window.AREAS = window.AREAS || []" in html
    for arquivo in [*AREAS, "app"]:
        assert f'src="/web/{arquivo}.js"' in html, f"index.html nao carrega {arquivo}.js"


def test_app_js_monta_as_duas_formas_de_registro_e_respeita_a_ordem() -> None:
    js = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Array.isArray" in js, "app.js precisa aceitar a forma em lista"
    assert "Object.entries" in js, "app.js precisa aceitar a forma em objeto"
    for area in AREAS:
        assert f'"{area}"' in js, f"app.js nao conhece a area {area}"


def test_todo_javascript_da_tela_tem_sintaxe_valida() -> None:
    """Um erro de sintaxe em qualquer area derruba a tela inteira em silencio. Este teste pega isso."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node nao disponivel neste computador")

    arquivos = sorted(WEB.glob("*.js"))
    assert arquivos, "nenhum javascript encontrado em web/"

    quebrados = {}
    for arquivo in arquivos:
        resultado = subprocess.run(
            [node, "--check", str(arquivo)], capture_output=True, text=True, errors="replace", check=False
        )
        if resultado.returncode != 0:
            ultima = resultado.stderr.strip().splitlines()[-1] if resultado.stderr.strip() else "erro sem mensagem"
            quebrados[arquivo.name] = ultima

    assert not quebrados, f"javascript com erro de sintaxe: {quebrados}"
