"""Histórico com configurações por geração e aba de Configurações.

Cobre: tempo relativo, migração da coluna nova, registro da configuração em cada
geração e as rotas /api/historico e /api/configuracoes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app import cofre, quando
from app.config import carregar_config
from app.servidor import criar_app


def _cliente(tmp_path: Path) -> TestClient:
    config = carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas", "ESTUDIO_MOTOR": "mock"},
        raiz=tmp_path,
    )
    return TestClient(criar_app(config, verificar_base=lambda: False))


def _gerar(cliente: TestClient, texto: str = "Frase para o histórico."):
    return cliente.post(
        "/api/gerar",
        json={
            "texto": texto,
            "perfil_id": None,
            "motor": "mock",
            "idioma": "pt",
            "velocidade": 1.5,
            "semente": 2026,
            "modo": "natural",
        },
    )


# ── tempo relativo ───────────────────────────────────────────────────────────


def test_relativo_fala_como_a_tela_do_elevenlabs() -> None:
    agora = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc).astimezone()
    assert quando.relativo(agora.isoformat(), referencia=agora) == "agora mesmo"
    assert quando.relativo((agora - timedelta(minutes=5)).isoformat(), referencia=agora) == "há 5 minutos"
    assert quando.relativo((agora - timedelta(minutes=1)).isoformat(), referencia=agora) == "há 1 minuto"
    assert quando.relativo((agora - timedelta(hours=3)).isoformat(), referencia=agora) == "há 3 horas"
    assert quando.relativo((agora - timedelta(hours=1)).isoformat(), referencia=agora) == "há 1 hora"
    assert quando.relativo((agora - timedelta(days=1)).isoformat(), referencia=agora) == "ontem"
    assert quando.relativo((agora - timedelta(days=4)).isoformat(), referencia=agora) == "há 4 dias"
    assert quando.relativo((agora - timedelta(days=70)).isoformat(), referencia=agora) == "há 2 meses"


def test_relativo_nunca_inventa() -> None:
    assert quando.relativo(None) == "sem data"
    assert quando.relativo("") == "sem data"
    assert quando.relativo("ontem de manhã") == "sem data"


# ── migração do banco ────────────────────────────────────────────────────────


def test_banco_antigo_ganha_a_coluna_sem_perder_geracao(tmp_path: Path) -> None:
    caminho = tmp_path / "estudio.db"
    antigo = sqlite3.connect(str(caminho))
    antigo.executescript(
        """
        CREATE TABLE geracao (
            id TEXT PRIMARY KEY,
            perfil_id TEXT,
            motor TEXT NOT NULL,
            texto_entrada TEXT NOT NULL,
            arquivo_saida TEXT NOT NULL,
            duracao_audio_s REAL NOT NULL,
            duracao_geracao_s REAL NOT NULL,
            dispositivo TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            status TEXT NOT NULL,
            erro TEXT
        );
        INSERT INTO geracao VALUES ('g-antigo', NULL, 'omnivoice', 'texto', 'saidas/a.wav', 1.0, 2.0, 'mock', 10, '2026-09-01T10:00:00-03:00', 'ok', NULL);
        """
    )
    antigo.commit()
    antigo.close()

    banco = cofre.abrir(caminho)
    try:
        colunas = {linha["name"] for linha in banco._conexao.execute("PRAGMA table_info(geracao)")}
        assert "config_json" in colunas
        registro = banco.geracao("g-antigo")
        assert registro is not None
        assert registro["texto_entrada"] == "texto"
        assert banco.configuracao_da_geracao(registro) is None
    finally:
        banco.fechar()


# ── geração guarda a configuração ───────────────────────────────────────────


def test_geracao_guarda_a_configuracao_usada(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    resposta = _gerar(cliente)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["configuracao"]["velocidade"] == 1.5
    assert corpo["configuracao"]["modo"] == "natural"
    assert corpo["configuracao"]["motor"] == "mock"
    assert corpo["configuracao"]["semente"] == 2026
    assert corpo["configuracao"]["preparo"] in (True, False)


def test_historico_lista_com_configuracao_e_tempo_relativo(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    assert _gerar(cliente, "Primeira frase do histórico.").status_code == 200
    assert _gerar(cliente, "Segunda frase do histórico.").status_code == 200

    lista = cliente.get("/api/historico")
    assert lista.status_code == 200
    corpo = lista.json()
    assert corpo["total"] == 2
    primeiro = corpo["itens"][0]
    assert primeiro["texto_entrada"] == "Segunda frase do histórico."
    assert primeiro["quando"] == "agora mesmo"
    assert primeiro["configuracao"]["modo"] == "natural"
    assert primeiro["audio_url"]


def test_historico_detalhe_e_404(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    identificador = _gerar(cliente).json()["geracao_id"]
    detalhe = cliente.get(f"/api/historico/{identificador}")
    assert detalhe.status_code == 200
    assert detalhe.json()["id"] == identificador
    assert cliente.get("/api/historico/g-nao-existe").status_code == 404


def test_historico_filtra_por_motor(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    _gerar(cliente)
    assert cliente.get("/api/historico?motor=mock").json()["total"] == 1
    assert cliente.get("/api/historico?motor=omnivoice").json()["total"] == 0


def test_historico_recusa_limite_fora_da_faixa(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    assert cliente.get("/api/historico?limite=0").status_code == 422
    assert cliente.get("/api/historico?limite=501").status_code == 422


# ── configurações ────────────────────────────────────────────────────────────


def test_configuracoes_leem_padrao_e_salvam(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    inicial = cliente.get("/api/configuracoes")
    assert inicial.status_code == 200
    assert inicial.json()["velocidade"] == 1.0
    assert inicial.json()["modo"] is None

    salvo = cliente.post("/api/configuracoes", json={"velocidade": 0.8, "modo": "detalhado", "semente": 4242})
    assert salvo.status_code == 200
    assert salvo.json()["velocidade"] == 0.8
    assert salvo.json()["modo"] == "detalhado"
    assert salvo.json()["semente"] == 4242

    # persiste entre chamadas
    outra = cliente.get("/api/configuracoes").json()
    assert outra["velocidade"] == 0.8
    assert outra["semente"] == 4242


def test_configuracoes_recusam_valores_invalidos(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    assert cliente.post("/api/configuracoes", json={"velocidade": 4}).status_code == 422
    assert cliente.post("/api/configuracoes", json={"modo": "turbinado"}).status_code == 422
    assert cliente.post("/api/configuracoes", json={"semente": -1}).status_code == 422
    assert cliente.post("/api/configuracoes", json={"semente": "abc"}).status_code == 422
    assert cliente.post("/api/configuracoes", json={}).status_code == 422


def test_configuracoes_aceitam_apenas_os_tres_modos(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)
    for modo in ("natural", "detalhado", "broadcast"):
        assert cliente.post("/api/configuracoes", json={"modo": modo}).status_code == 200


# ── tela ─────────────────────────────────────────────────────────────────────


def test_tela_tem_as_duas_abas_e_o_detalhe_igual_ao_pedido() -> None:
    javascript = Path("web/gerar.js").read_text(encoding="utf-8")
    assert 'data-acao="config"' in javascript
    assert "Configurações" in javascript
    assert 'data-acao="historico"' in javascript
    # detalhe do histórico
    assert "Voltar para o histórico" in javascript
    assert "ID da geração" in javascript
    assert "Reproduzir" in javascript
    assert "Restaurar tudo" in javascript
    assert "/historico?limite=50" in javascript
    assert "/configuracoes" in javascript
    # nada de caminho fixo: os valores vêm da API
    assert "busca-historico" in javascript
