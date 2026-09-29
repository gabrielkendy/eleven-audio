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

def test_versao_da_tela_existe_e_e_estavel(tmp_path: Path) -> None:
    """O carimbo que faz a aba velha se recarregar sozinha.

    Medido em 29/09/2026: conserto de JS nao chegava em quem ja estava com a aba
    aberta, porque o navegador nao busca o arquivo de novo. A pessoa via o
    defeito antigo e reportava de novo. O carimbo e a base do conserto: sem ele,
    o vigia do `app.js` nao tem o que comparar e a tela volta a mentir em
    silencio.
    """
    cliente, _ = _cliente(tmp_path)

    primeira = cliente.get("/api/versao").json()["versao"]
    segunda = cliente.get("/api/versao").json()["versao"]

    assert primeira, "sem carimbo, o vigia da tela nao tem o que comparar"
    assert len(primeira) == 12
    assert all(c in "0123456789abcdef" for c in primeira)
    assert primeira == segunda, "o carimbo nao pode mudar sozinho entre duas leituras"


def test_versao_muda_quando_a_tela_muda(tmp_path: Path) -> None:
    """Se o carimbo nao muda, o vigia nunca dispara e o defeito volta a ser invisivel."""
    cliente, _ = _cliente(tmp_path)
    antes = cliente.get("/api/versao").json()["versao"]

    marca = Path(__file__).resolve().parents[1] / "web" / "_carimbo-de-teste.tmp"
    try:
        marca.write_text("teste", encoding="utf-8")
        durante = cliente.get("/api/versao").json()["versao"]
    finally:
        marca.unlink(missing_ok=True)

    depois = cliente.get("/api/versao").json()["versao"]
    assert durante != antes, "carimbo igual depois de mexer na tela: o vigia nao dispara"
    assert depois != durante, "a volta do arquivo precisa mexer no carimbo tambem"

