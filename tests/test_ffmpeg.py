from __future__ import annotations

from pathlib import Path

import pytest

from app import ffmpeg


@pytest.fixture(autouse=True)
def limpar_cache():
    """O resolvedor guarda o resultado; sem limpar, um teste contamina o outro."""
    ffmpeg._cache = None
    yield
    ffmpeg._cache = None


def test_acha_o_ffmpeg_nesta_maquina() -> None:
    achado = ffmpeg.executavel()

    assert achado
    assert Path(achado).is_file() or achado == "ffmpeg"
    assert "ffmpeg" in Path(achado).name.lower()


def test_disponivel_devolve_caminho_quando_ha() -> None:
    tem, detalhe = ffmpeg.disponivel()

    assert tem is True
    assert detalhe


def test_versao_responde() -> None:
    versao = ffmpeg.versao()

    assert versao is not None
    assert "ffmpeg" in versao.lower()


def test_quando_falta_o_erro_diz_o_que_instalar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ausência não pode virar um erro genérico: tem que dizer o comando."""
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda *a, **k: None)
    monkeypatch.setattr(ffmpeg, "CANDIDATOS_WINDOWS", ())
    monkeypatch.setattr(ffmpeg, "_caminhos_de_busca", list)

    with pytest.raises(ffmpeg.ErroFfmpeg) as erro:
        ffmpeg.executavel()

    mensagem = str(erro.value)
    assert "winget install" in mensagem
    assert "obrigatório" in mensagem


def test_disponivel_nao_levanta_quando_falta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda *a, **k: None)
    monkeypatch.setattr(ffmpeg, "CANDIDATOS_WINDOWS", ())
    monkeypatch.setattr(ffmpeg, "_caminhos_de_busca", list)

    tem, detalhe = ffmpeg.disponivel()

    assert tem is False
    assert "winget install" in detalhe


def test_acha_por_caminho_conhecido_quando_o_path_falha(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """O defeito real: PATH incompleto, mas o programa existe no lugar de sempre."""
    falso = tmp_path / "ffmpeg.exe"
    falso.write_bytes(b"binario falso")

    monkeypatch.setattr(ffmpeg.shutil, "which", lambda *a, **k: None)
    monkeypatch.setattr(ffmpeg, "CANDIDATOS_WINDOWS", (falso,))

    assert ffmpeg.executavel() == str(falso)


def test_usa_o_path_do_usuario_quando_o_do_processo_nao_tem(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Segundo caminho de socorro: ler o PATH do usuário do registro."""
    pasta = tmp_path / "bin"
    pasta.mkdir()
    (pasta / "ffmpeg.exe").write_bytes(b"binario falso")

    monkeypatch.setattr(ffmpeg, "CANDIDATOS_WINDOWS", ())

    chamadas: list[str] = []

    def which(nome: str, path: str | None = None) -> str | None:
        chamadas.append(path or "")
        if path and str(pasta) in path:
            return str(pasta / "ffmpeg.exe")
        return None

    monkeypatch.setattr(ffmpeg.shutil, "which", which)
    monkeypatch.setattr(ffmpeg, "_caminhos_de_busca", lambda: [str(pasta)])

    assert ffmpeg.executavel() == str(pasta / "ffmpeg.exe")
    assert any(str(pasta) in c for c in chamadas), chamadas


def test_resultado_fica_guardado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Não pode reler o disco a cada chamada."""
    chamadas = {"n": 0}

    def qual(*a, **k):
        chamadas["n"] += 1
        return "/falso/ffmpeg"

    monkeypatch.setattr(ffmpeg.shutil, "which", qual)

    assert ffmpeg.executavel() == "/falso/ffmpeg"
    assert ffmpeg.executavel() == "/falso/ffmpeg"
    assert chamadas["n"] == 1


def test_saude_do_app_reporta_o_ffmpeg(tmp_path: Path) -> None:
    """A tela precisa saber disso antes de o usuário tentar clonar."""
    from fastapi.testclient import TestClient

    from app.config import carregar_config
    from app.servidor import criar_app

    config = carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path
    )
    cliente = TestClient(criar_app(config, verificar_base=lambda: True))

    corpo = cliente.get("/api/saude").json()

    assert corpo["ffmpeg"] == "ok"
    assert corpo["ffmpeg_detalhe"]
