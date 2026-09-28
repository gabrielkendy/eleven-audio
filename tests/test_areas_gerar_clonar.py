from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import carregar_config
from app.servidor import criar_app


def test_gerar_contem_anatomia_contador_e_atalho() -> None:
    javascript = Path("web/gerar.js").read_text(encoding="utf-8")

    for classe in ("compositor", "rail", "player", "onda", "pílula"):
        assert f'class="{classe}' in javascript
    assert "Ctrl+Enter" in javascript
    assert "metaKey" in javascript
    assert "/ 14" in javascript
    assert "semente:" in javascript
    assert "/marcas" in javascript
    assert "estudio:area-visivel" in javascript


def test_clonar_contem_faixa_consentimento_e_comparacao() -> None:
    javascript = Path("web/clonar.js").read_text(encoding="utf-8")

    # Os limites vem de /api/estado, entao a tela nao repete numero fixo.
    assert "limites_clonagem" in javascript
    assert "limiteMax = 180" in javascript
    assert "rotuloLimites" in javascript
    assert "5 a 30 segundos" not in javascript
    assert "aceite_consentimento" in javascript
    assert 'class="duplo' in javascript
    assert javascript.count('class="player') >= 2
    assert "/api/transcrever" in javascript
    assert "MediaRecorder" in javascript


def test_app_publica_as_rotas_usadas_pelas_duas_telas(tmp_path: Path) -> None:
    config = carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas",
            "ESTUDIO_MOTOR": "mock",
        },
        raiz=tmp_path,
    )
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))

    assert cliente.get("/api/motores").status_code == 200
    assert cliente.post("/api/motores/ativo", json={"motor": "mock"}).status_code == 200
    assert cliente.get("/api/perfis").status_code == 200
    assert cliente.get("/api/saidas").status_code == 200
    assert cliente.get("/api/estado").status_code == 200

    gerado = cliente.post(
        "/api/gerar",
        json={
            "texto": "Prova da tela de geração.",
            "perfil_id": None,
            "motor": "mock",
            "idioma": "pt",
            "velocidade": 1,
        },
    )
    assert gerado.status_code == 200
    assert {"arquivo", "duracao_audio_s", "duracao_geracao_s"} <= gerado.json().keys()

    rotas = cliente.get("/openapi.json").json()["paths"]
    for caminho in ("/api/clonar", "/api/perfis/{perfil_id}", "/api/transcrever", "/api/saidas/abrir"):
        assert caminho in rotas
