from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import carregar_config
from app.servidor import criar_app


def _cliente(tmp_path: Path) -> tuple[TestClient, Path]:
    config = carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas/audio",
            "ESTUDIO_MOTOR": "mock",
        },
        raiz=tmp_path,
    )
    return TestClient(criar_app(config, verificar_base=lambda: False)), config.dados


def test_migracao_cria_as_sete_tabelas(tmp_path: Path) -> None:
    _, dados = _cliente(tmp_path)

    with sqlite3.connect(dados / "estudio.db") as banco:
        tabelas = {
            linha[0]
            for linha in banco.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "perfil_voz",
        "consentimento",
        "geracao",
        "transcricao",
        "vinculo_agente",
        "configuracao",
        "evento",
    } <= tabelas


def test_gerar_mock_valida_grava_arquivo_e_banco(tmp_path: Path) -> None:
    cliente, dados = _cliente(tmp_path)

    invalida = cliente.post("/api/gerar", json={"texto": "", "motor": "mock"})
    resposta = cliente.post(
        "/api/gerar",
        json={"texto": "Prova real da fatia um.", "motor": "mock", "velocidade": 1},
    )

    assert invalida.status_code == 422
    assert "portugu" not in invalida.text.lower()  # mensagem em português, não rótulo
    assert "texto deve ter entre 1 e 5000 caracteres" in invalida.text
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert Path(corpo["arquivo"]).exists()
    assert corpo["audio_url"].startswith("/saidas/")
    assert corpo["duracao_audio_s"] > 0
    assert corpo["duracao_geracao_s"] >= 0
    detalhe = cliente.get(f"/api/gerar/{corpo['geracao_id']}")
    assert detalhe.status_code == 200
    with sqlite3.connect(dados / "estudio.db") as banco:
        assert banco.execute("SELECT COUNT(*) FROM geracao").fetchone()[0] == 1
        assert banco.execute("SELECT COUNT(*) FROM evento").fetchone()[0] == 1


def test_motor_indisponivel_preserva_motivo(tmp_path: Path) -> None:
    cliente, _ = _cliente(tmp_path)

    resposta = cliente.post(
        "/api/gerar",
        json={"texto": "Teste", "motor": "voxcpm2", "velocidade": 1},
    )

    assert resposta.status_code == 409
    assert "motor indisponivel" in resposta.text
    assert "base esta fora do ar" in resposta.text


def test_contrato_da_fatia_um_e_shell_de_areas(tmp_path: Path) -> None:
    cliente, _ = _cliente(tmp_path)
    rotas = {rota.path for rota in cliente.app.routes}

    assert {
        "/api/estado",
        "/api/motores",
        "/api/motores/ativo",
        "/api/gerar",
        "/api/gerar/{geracao_id}",
        "/api/saidas",
        "/api/saude",
    } <= rotas
    raiz = Path(__file__).resolve().parents[1]
    assert "window.AREAS" in (raiz / "web/index.html").read_text(encoding="utf-8")
    assert "Object.entries" in (raiz / "web/app.js").read_text(encoding="utf-8")
    assert "Array.isArray" in (raiz / "web/app.js").read_text(encoding="utf-8")
    assert "window.AREAS.gerar" in (raiz / "web/gerar.js").read_text(
        encoding="utf-8"
    )
