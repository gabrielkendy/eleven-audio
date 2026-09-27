from __future__ import annotations

import array
import subprocess
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cofre import abrir
from app.config import carregar_config
from app.referencia import diagnosticar
from app.rotas_clonar import router


def test_diagnostico_silencio_nao_inventa_fidelidade(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=array.array("f", [0.0] * 16000).tobytes()))
    result = diagnosticar(tmp_path / "silencio.wav")
    assert result["duracao_s"] == 1
    assert result["pico_dbfs"] == -160
    assert result["onda"] == [0] * 48
    assert any("silenciosa" in item for item in result["avisos"])
    assert "fidelidade" not in result


def test_diagnostico_avisa_saturacao(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=array.array("f", [1.0] * 16000).tobytes()))
    result = diagnosticar(tmp_path / "clip.wav")
    assert result["amostras_no_limite_pct"] == 100
    assert any("saturação" in item for item in result["avisos"])


def test_previa_serve_so_referencia_registrada(tmp_path: Path):
    config = carregar_config({}, raiz=tmp_path)
    pasta = config.dados / "referencias"
    pasta.mkdir(parents=True)
    arquivo = pasta / "voz.wav"
    arquivo.write_bytes(b"RIFFreference-test")
    banco = abrir(config.dados / "estudio.db")
    try:
        perfil = banco.salvar_perfil(nome="Original", origem="clonado", id_na_base="ref",
                                    arquivo_referencia="dados/referencias/voz.wav",
                                    transcricao_referencia="Oi", idioma="pt")
    finally:
        banco.fechar()
    app = FastAPI()
    app.state.configuracao_clonar = config
    app.include_router(router)
    client = TestClient(app)
    rows = client.get("/api/perfis").json()
    assert rows[0]["audio_url"] == f"/api/perfis/{perfil}/audio"
    assert client.get(rows[0]["audio_url"]).content == arquivo.read_bytes()
    assert client.get("/api/perfis/inexistente/audio").status_code == 404
    assert client.get("/api/perfis/inexistente/qualidade").status_code == 404
