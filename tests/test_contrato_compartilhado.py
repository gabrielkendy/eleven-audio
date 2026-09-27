"""Contrato compartilhado: cofre (SQLite, sete tabelas) e saidas (nome e medicao)."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from app.cofre import abrir
from app.saidas import medir, medir_duracao, nome_arquivo, pasta_do_dia, sanitizar

TABELAS = {
    "perfil_voz",
    "consentimento",
    "geracao",
    "transcricao",
    "vinculo_agente",
    "configuracao",
    "evento",
}


def _wav_teste(caminho: Path, segundos: float = 1.5, taxa: int = 24_000) -> Path:
    quadros = int(taxa * segundos)
    with wave.open(str(caminho), "wb") as escritor:
        escritor.setnchannels(1)
        escritor.setsampwidth(2)
        escritor.setframerate(taxa)
        escritor.writeframes(
            b"".join(
                struct.pack("<h", int(8_000 * math.sin(2 * math.pi * 440 * i / taxa))) for i in range(quadros)
            )
        )
    return caminho


def test_cofre_cria_as_sete_tabelas(tmp_path: Path) -> None:
    cofre = abrir(tmp_path / "estudio.db")
    try:
        nomes = {
            linha["name"]
            for linha in cofre._conexao.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert TABELAS.issubset(nomes)
    finally:
        cofre.fechar()


def test_cofre_perfil_consentimento_geracao_e_vinculo(tmp_path: Path) -> None:
    cofre = abrir(tmp_path / "estudio.db")
    try:
        perfil_id = cofre.salvar_perfil(
            nome="Voz do Gabriel",
            origem="clonado",
            id_na_base="base-123",
            arquivo_referencia="dados/referencias/clipe.wav",
            transcricao_referencia="texto do clipe",
        )
        assert cofre.tem_consentimento(perfil_id) is False

        cofre.salvar_consentimento(
            perfil_id=perfil_id,
            texto_aceito="esta voz e minha",
            origem_voz="propria",
        )
        assert cofre.tem_consentimento(perfil_id) is True

        geracao_id = cofre.registrar_geracao(
            motor="mock",
            texto_entrada="bom dia",
            arquivo_saida="saidas/audio/x.wav",
            duracao_audio_s=1.5,
            duracao_geracao_s=0.2,
            dispositivo="cpu",
            tamanho_bytes=72_000,
            perfil_id=perfil_id,
        )
        assert cofre.geracao(geracao_id)["perfil_id"] == perfil_id
        assert cofre.ultima_geracao()["id"] == geracao_id

        cofre.salvar_vinculo(cliente_id="hermes", perfil_id=perfil_id)
        vinculos = cofre.listar_vinculos()
        assert vinculos[0]["cliente_id"] == "hermes"
        assert vinculos[0]["perfil_nome"] == "Voz do Gabriel"

        listados = cofre.listar_perfis()
        assert listados[0]["total_geracoes"] == 1
        assert listados[0]["consentimento_origem"] == "propria"
    finally:
        cofre.fechar()


def test_cofre_consentimento_unico_por_perfil(tmp_path: Path) -> None:
    cofre = abrir(tmp_path / "estudio.db")
    try:
        perfil_id = cofre.salvar_perfil(nome="Voz", origem="desenhado", id_na_base="base-9")
        cofre.salvar_consentimento(perfil_id=perfil_id, texto_aceito="primeiro", origem_voz="propria")
        cofre.salvar_consentimento(perfil_id=perfil_id, texto_aceito="segundo", origem_voz="autorizada")
        registro = cofre.consentimento(perfil_id)
        assert registro["texto_aceito"] == "segundo"
        assert registro["origem_voz"] == "autorizada"
    finally:
        cofre.fechar()


def test_cofre_guarda_configuracao_tipos(tmp_path: Path) -> None:
    cofre = abrir(tmp_path / "estudio.db")
    try:
        cofre.gravar_config("motor_padrao", "omnivoice")
        cofre.gravar_config("limite_lote", 7)
        assert cofre.ler_config("motor_padrao") == "omnivoice"
        assert cofre.ler_config("limite_lote") == 7
        assert cofre.ler_config("inexistente", "x") == "x"
    finally:
        cofre.fechar()


def test_nome_arquivo_segue_a_convencao_do_prd() -> None:
    nome = nome_arquivo("omnivoice", "Voz do Gabriel")
    partes = nome.split("_")
    assert len(partes) == 4
    assert partes[1].isdigit() and len(partes[1]) == 6
    assert partes[2] == "omnivoice"
    assert partes[3] == "voz-do-gabriel.wav"
    assert len(partes[0].split("-")) == 3


def test_sanitizar_remove_acento_e_espaco() -> None:
    assert sanitizar("Voz Ação Nº 2") == "voz-acao-no-2"
    assert sanitizar("") == "sem-perfil"


def test_medicao_de_audio_e_real(tmp_path: Path) -> None:
    arquivo = _wav_teste(tmp_path / "teste.wav", segundos=1.5)
    assert medir_duracao(arquivo) == 1.5
    pacote = medir(arquivo)
    assert pacote["duracao_audio_s"] == 1.5
    assert pacote["tamanho_bytes"] == arquivo.stat().st_size


def test_pasta_do_dia_e_criada(tmp_path: Path) -> None:
    destino = pasta_do_dia(tmp_path)
    assert destino.is_dir()
    assert destino.parent == tmp_path
