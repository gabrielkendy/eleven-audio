"""Regressões de segurança e integridade achadas na auditoria paralela tardia."""

from __future__ import annotations

import io
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import dublar, saidas
from app.cofre import abrir
from app.config import Configuracao, carregar_config
from app.servidor import criar_app
from app.transcricao import ErroTranscricao, ler_upload_limitado


def _config(tmp_path: Path) -> Configuracao:
    return carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas/audio",
            "ESTUDIO_MOTOR": "mock",
        },
        raiz=tmp_path,
    )


def _wav(caminho: Path, quadros: int = 80) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(8000)
        arquivo.writeframes(b"\x01\x00" * quadros)
    return caminho


def test_api_audio_nao_entrega_banco_nem_arquivo_nao_audio(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))
    banco = config.dados / "estudio.db"
    texto = config.saidas / "segredo.txt"
    texto.parent.mkdir(parents=True, exist_ok=True)
    texto.write_text("segredo", encoding="utf-8")

    assert cliente.get("/api/audio", params={"caminho": str(banco)}).status_code == 403
    assert cliente.get("/api/audio", params={"caminho": str(texto)}).status_code == 403


def test_api_audio_entrega_apenas_midia_dentro_das_saidas(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))
    audio = _wav(config.saidas / "permitido.wav")

    resposta = cliente.get("/api/audio", params={"caminho": str(audio)})

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("audio/wav")


def test_gravacao_concorrente_nunca_sobrescreve(tmp_path: Path) -> None:
    destino = tmp_path / "mesmo.wav"
    cargas = [f"audio-{indice}".encode() for indice in range(24)]

    with ThreadPoolExecutor(max_workers=12) as executor:
        caminhos = list(executor.map(lambda dados: saidas.gravar_bytes(destino, dados), cargas))

    assert len(set(caminhos)) == len(cargas)
    assert {caminho.read_bytes() for caminho in caminhos} == set(cargas)


def test_juncao_de_dublagem_nao_sobrescreve_destino_existente(tmp_path: Path) -> None:
    trecho = _wav(tmp_path / "trecho.wav")
    destino = tmp_path / "dublado.wav"

    primeiro = dublar.juntar_wavs([trecho], destino)
    segundo = dublar.juntar_wavs([trecho], destino)

    assert primeiro != segundo
    assert primeiro.is_file() and segundo.is_file()


def test_upload_limitado_interrompe_antes_de_aceitar_excesso() -> None:
    with pytest.raises(ErroTranscricao, match="limite"):
        ler_upload_limitado(io.BytesIO(b"12345"), limite_bytes=4)


def test_historico_de_dublagem_registra_arquivo_de_entrada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import rotas_traduzir

    config = _config(tmp_path)
    saida = _wav(config.saidas / "dublado.wav")

    def dublagem_controlada(**_kwargs: object) -> dict[str, object]:
        return {
            "arquivo": str(saida),
            "texto_traduzido": "hello",
            "origem": "pt",
        }

    monkeypatch.setattr(rotas_traduzir.dublagem, "dublar", dublagem_controlada)
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))

    resposta = cliente.post(
        "/api/dublar",
        files={"arquivo": ("minha-entrada.wav", b"audio", "audio/wav")},
        data={"destino": "en", "motor": "mock"},
    )

    assert resposta.status_code == 200, resposta.text
    historico = cliente.get("/api/transcricoes").json()
    assert historico[0]["arquivo_entrada"] == "minha-entrada.wav"


def test_dublagem_remove_upload_temporario_quando_transcricao_falha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)

    def falhar(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise ErroTranscricao("falha controlada")

    monkeypatch.setattr(dublar, "transcrever", falhar)

    with pytest.raises(dublar.ErroDublagem, match="falha controlada"):
        dublar.dublar(
            arquivo=io.BytesIO(b"audio"),
            nome_arquivo="entrada.wav",
            destino_idioma="en",
            config=config,
            motor="mock",
        )

    pasta = config.dados / "transcricoes"
    assert not pasta.exists() or not list(pasta.iterdir())


def test_perfil_e_consentimento_entram_ou_falham_juntos(tmp_path: Path) -> None:
    cofre = abrir(tmp_path / "estudio.db")
    try:
        cofre._conexao.execute(
            """
            CREATE TRIGGER falhar_consentimento
            BEFORE INSERT ON consentimento
            BEGIN SELECT RAISE(ABORT, 'falha controlada'); END
            """
        )
        with pytest.raises(Exception, match="falha controlada"):
            cofre.salvar_perfil_com_consentimento(
                nome="Teste",
                id_na_base="base-1",
                arquivo_referencia="referencia.wav",
                transcricao_referencia="texto",
                idioma="pt",
                texto_aceito="aceito",
                origem_voz="propria",
            )
        assert cofre.listar_perfis() == []
    finally:
        cofre.fechar()


def test_frontend_bloqueia_url_executavel_e_transporta_traducao() -> None:
    raiz = Path(__file__).parents[1]
    gerar = (raiz / "web" / "gerar.js").read_text(encoding="utf-8")
    traduzir = (raiz / "web" / "traduzir.js").read_text(encoding="utf-8")

    assert "url.origin !== window.location.origin" in gerar
    assert "urlAudioLocalSegura(item.audio_url)" in gerar
    assert "if (item.audio_url) baixar.href = item.audio_url" not in gerar
    assert "[data-alvo=\"gerar\"]" in traduzir
    assert "textoGerar.value = traduzidoAtual" in traduzir
