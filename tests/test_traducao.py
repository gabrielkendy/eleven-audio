from __future__ import annotations

import io
import wave
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import dublar, traducao
from app.config import carregar_config
from app.rotas_traduzir import criar_router


def _config(tmp_path: Path):
    return carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas/audio",
            "ESTUDIO_BASE_URL": "http://127.0.0.1:3900",
        },
        raiz=tmp_path,
    )


def _wav(taxa: int = 24_000, decimos: int = 5) -> bytes:
    saida = io.BytesIO()
    with wave.open(saida, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(taxa)
        audio.writeframes(b"\0\0" * int(taxa * decimos / 10))
    return saida.getvalue()


# --------------------------------------------------------------- catálogo

def test_catalogo_bate_com_o_argos() -> None:
    """São 50 idiomas, nem um a mais: prometer idioma que não existe é mentir."""
    assert len(traducao.IDIOMAS) == 50
    assert len(traducao.catalogo()) == 50


def test_pt_e_pb_sao_idiomas_distintos() -> None:
    """Erro real: traduzir para pt devolvia 'como estás, a correr'."""
    assert traducao.normalizar("pt") == "pt"
    assert traducao.normalizar("pb") == "pb"
    assert "Portugal" in traducao.IDIOMAS["pt"]
    assert "Brasil" in traducao.IDIOMAS["pb"]


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("pt-BR", "pb"),
        ("pt_br", "pb"),
        ("BR", "pb"),
        ("pt-pt", "pt"),
        ("PT", "pt"),
        ("zh-CN", "zh"),
        ("zh-TW", "zt"),
        ("en-US", "en"),
        ("  fr  ", "fr"),
        ("auto", ""),
        ("", ""),
    ],
)
def test_normaliza_codigos(entrada: str, esperado: str) -> None:
    assert traducao.normalizar(entrada) == esperado


def test_catalogo_vem_ordenado_por_nome() -> None:
    nomes = [item["nome"] for item in traducao.catalogo()]
    assert nomes == sorted(nomes)


# ---------------------------------------------------------------- traduzir

def _transporte(respostas: dict[str, object]) -> httpx.MockTransport:
    """Transporte falso: casa pelo par origem->destino pedido no corpo.

    O httpx serializa JSON compacto (`"source_lang":"pt"`, sem espaço depois dos
    dois pontos), então casar com espaço nunca dá certo.
    """

    def handler(requisicao: httpx.Request) -> httpx.Response:
        corpo = requisicao.read().decode()
        chave = None
        for par in respostas:
            origem, destino = par.split("->")
            if f'"source_lang":"{origem}"' in corpo and f'"target_lang":"{destino}"' in corpo:
                chave = par
                break
        if chave is None:
            return httpx.Response(
                400,
                json={
                    "error": "no pack",
                    "code": "argos_pack_missing",
                    "pairs": [{"source_lang": "?", "target_lang": "?", "installed": False}],
                },
            )
        valor = respostas[chave]
        if isinstance(valor, str):
            return httpx.Response(200, json={
                "translated": [{"id": "0", "text": valor}],
                "target_lang": chave.split("->")[1],
            })
        return httpx.Response(200, json=valor)

    return httpx.MockTransport(handler)


def test_traduz_direto(tmp_path: Path) -> None:
    config = _config(tmp_path)
    transporte = _transporte({"pt->en": "Good morning."})

    r = traducao.traduzir("Bom dia.", "pt", "en", config, transporte)

    assert r["texto"] == "Good morning."
    assert r["caminho"] == ["pt", "en"]
    assert r["saltos"] == 1
    assert r["observacao"] is None


def test_traduz_em_cascata_quando_nao_existe_par_direto(tmp_path: Path) -> None:
    """Medido: de pt só saem 2 pares diretos, então cascata é o caminho normal."""
    config = _config(tmp_path)
    transporte = _transporte({"pt->en": "Good morning.", "en->ja": "おはよう"})

    r = traducao.traduzir("Bom dia.", "pt", "ja", config, transporte)

    assert r["texto"] == "おはよう"
    assert r["caminho"] == ["pt", "en", "ja"]
    assert r["saltos"] == 2
    assert r["intermediario"] == "Good morning."
    # a cascata tem que ser declarada, não escondida
    assert r["observacao"] and "inglês" in r["observacao"]


def test_erro_da_cascata_diz_os_dois_motivos(tmp_path: Path) -> None:
    config = _config(tmp_path)
    transporte = _transporte({})  # nada instalado

    with pytest.raises(traducao.ErroTraducao) as erro:
        traducao.traduzir("Bom dia.", "pt", "ja", config, transporte)

    mensagem = str(erro.value)
    assert "Direto:" in mensagem and "escala em inglês" in mensagem


def test_traduzir_nao_toca_na_rede_quando_e_o_mesmo_idioma(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def handler(requisicao: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria chamar a rede")

    r = traducao.traduzir(
        "Nada muda.", "pb", "pt-BR", config, httpx.MockTransport(handler)
    )

    assert r["texto"] == "Nada muda."
    assert r["saltos"] == 0
    assert r["observacao"]


def test_recusa_idioma_inexistente(tmp_path: Path) -> None:
    config = _config(tmp_path)
    with pytest.raises(traducao.ErroTraducao) as erro:
        traducao.traduzir("teste", "pt", "klingon", config)
    assert "desconhecido" in str(erro.value)


def test_recusa_texto_vazio(tmp_path: Path) -> None:
    config = _config(tmp_path)
    with pytest.raises(traducao.ErroTraducao) as erro:
        traducao.traduzir("   ", "pt", "en", config)
    assert "escreva" in str(erro.value).lower()


def test_usa_a_variante_irma_quando_falta_o_pacote_da_origem(tmp_path: Path) -> None:
    """Defeito real: o detector passou a acertar `pb`, mas só existia `pt->en`.

    Dublar áudio brasileiro para inglês quebrou. Como pt e pb são a mesma língua,
    a origem tem que aceitar a variante irmã quando o pacote exato falta.
    """
    config = _config(tmp_path)
    transporte = _transporte({"pt->en": "Good morning."})  # só pt->en existe

    r = traducao.traduzir("Bom dia.", "pb", "en", config, transporte)

    assert r["texto"] == "Good morning."
    assert r["origem"] == "pb", "a variante informada não pode ser trocada na resposta"


def test_variante_irma_nao_vale_para_o_destino(tmp_path: Path) -> None:
    """Trocar a variante no destino daria português de Portugal a quem pediu Brasil."""
    config = _config(tmp_path)
    transporte = _transporte({"en->pt": "Bom dia, como estás?"})  # falta en->pb

    with pytest.raises(traducao.ErroTraducao):
        traducao.traduzir("Good morning.", "en", "pb", config, transporte)


def test_fontes_candidatas() -> None:
    assert traducao._fontes_candidatas("pb") == ["pb", "pt"]
    assert traducao._fontes_candidatas("pt") == ["pt", "pb"]
    assert traducao._fontes_candidatas("en") == ["en"]


def test_pack_faltando_vira_mensagem_util(tmp_path: Path) -> None:
    config = _config(tmp_path)
    transporte = _transporte({})

    with pytest.raises(traducao.ErroTraducao) as erro:
        traducao.traduzir("Bom dia.", "pt", "en", config, transporte)

    # a mensagem precisa dizer qual par falta, não só "erro 400"
    assert "falta instalar" in str(erro.value)


# ------------------------------------------------------- detecção de idioma

@pytest.mark.parametrize(
    ("resposta", "esperado"),
    [
        ("en", "en"),
        ("EN.", "en"),
        ("pb", "pb"),
        ("The text is in Portuguese.", "pb"),
        ("This is English.", "en"),
        ("O texto está em português do Brasil.", "pb"),
        ("It is Italian.", "it"),
        ("It is Spanish.", "es"),
        ("Language: ja", "ja"),
        # caso real medido: o modelo delibera e menciona as duas variantes
        ((
            "The text is in Portuguese. Let me identify the language. "
            "Now I need to determine if it's Brazilian Portuguese or European Portuguese."
        ), "pb"),
    ],
)
def test_extrai_codigo_da_resposta_do_modelo(resposta: str, esperado: str) -> None:
    """O modelo às vezes responde em prosa; 'It is X' não pode virar italiano."""
    assert traducao._extrair_codigo(resposta) == esperado


def test_extrai_codigo_recusa_resposta_sem_idioma() -> None:
    assert traducao._extrair_codigo("I am not sure about that.") is None
    assert traducao._extrair_codigo("") is None


def test_deteccao_le_o_campo_thinking(tmp_path: Path) -> None:
    """Erro real: o modelo desta máquina escreve em `thinking`, não em `content`."""
    config = _config(tmp_path)

    def handler(requisicao: httpx.Request) -> httpx.Response:
        if requisicao.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "modelo-teste"}]})
        return httpx.Response(200, json={
            "message": {"role": "assistant", "content": "", "thinking": "The text is in Portuguese."}
        })

    r = traducao.detectar_idioma(
        "Bom dia, tudo bem?", config, transporte=httpx.MockTransport(handler)
    )

    assert r["detectado"] is True
    assert r["codigo"] == "pb"


def test_deteccao_sem_modelo_nao_inventa(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def handler(requisicao: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    r = traducao.detectar_idioma(
        "Bom dia", config, transporte=httpx.MockTransport(handler)
    )

    assert r["detectado"] is False
    assert "motivo" in r


# --------------------------------------------------------- divisão de texto

def test_texto_curto_nao_e_dividido() -> None:
    assert dublar.dividir_texto("Uma frase curta.") == ["Uma frase curta."]


def test_dividir_respeita_o_teto_e_nao_corta_palavra() -> None:
    texto = ("Esta é uma frase de teste para medir a divisão. " * 12).strip()

    pedacos = dublar.dividir_texto(texto, teto=120)

    assert len(pedacos) > 1
    assert all(len(p) <= 120 for p in pedacos)
    # nada pode sumir nem virar palavra cortada ao meio
    reconstruido = " ".join(pedacos)
    for palavra in texto.split():
        assert palavra in reconstruido


def test_dividir_frase_gigante_sem_pontuacao() -> None:
    texto = "palavra " * 100

    pedacos = dublar.dividir_texto(texto.strip(), teto=60)

    assert len(pedacos) > 1
    assert all(len(p) <= 60 for p in pedacos)
    assert " ".join(pedacos).split() == texto.split()


def test_dividir_texto_vazio_devolve_nada() -> None:
    assert dublar.dividir_texto("   ") == []


# ------------------------------------------------------------ juntar wavs

def test_juntar_wavs_soma_as_duracoes(tmp_path: Path) -> None:
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    a.write_bytes(_wav(decimos=3))
    b.write_bytes(_wav(decimos=4))
    destino = tmp_path / "final.wav"

    dublar.juntar_wavs([a, b], destino)

    with wave.open(str(destino), "rb") as leitor:
        assert leitor.getframerate() == 24_000
        assert leitor.getnframes() == 24_000 * 7 // 10


def test_juntar_wavs_com_um_so_copia(tmp_path: Path) -> None:
    a = tmp_path / "a.wav"
    a.write_bytes(_wav())
    destino = tmp_path / "final.wav"

    dublar.juntar_wavs([a], destino)

    assert destino.read_bytes() == a.read_bytes()


def test_juntar_wavs_recusa_taxas_diferentes(tmp_path: Path) -> None:
    """Misturar taxas num arquivo só produziria áudio em velocidade errada."""
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    a.write_bytes(_wav(taxa=24_000))
    b.write_bytes(_wav(taxa=16_000))

    with pytest.raises(dublar.ErroDublagem) as erro:
        dublar.juntar_wavs([a, b], tmp_path / "final.wav")

    assert "formatos diferentes" in str(erro.value)


def test_juntar_wavs_sem_arquivo_falha(tmp_path: Path) -> None:
    with pytest.raises(dublar.ErroDublagem):
        dublar.juntar_wavs([], tmp_path / "final.wav")


# ------------------------------------------------------------------ rotas

def _cliente(tmp_path: Path, transporte: httpx.MockTransport) -> TestClient:
    config = _config(tmp_path)
    app = FastAPI()
    app.include_router(criar_router(config))
    return TestClient(app)


def test_rota_idiomas_devolve_o_catalogo(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path, _transporte({}))

    corpo = cliente.get("/api/traduzir/idiomas").json()

    assert corpo["total"] == 50
    assert corpo["pivo"] == "en"
    codigos = {item["codigo"] for item in corpo["idiomas"]}
    assert {"pt", "pb", "en", "ja"} <= codigos


def test_rota_texto_recusa_pedido_vazio(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path, _transporte({}))

    assert cliente.post("/api/traduzir/texto", json={"texto": "", "destino": "en"}).status_code == 422


def test_rota_texto_recusa_idioma_inexistente(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path, _transporte({}))

    resposta = cliente.post(
        "/api/traduzir/texto", json={"texto": "oi", "origem": "pt", "destino": "klingon"}
    )

    assert resposta.status_code == 422
    assert "desconhecido" in resposta.json()["detail"]


def test_rota_audio_nao_serve_arquivo_de_fora(tmp_path: Path) -> None:
    """A rota recebe caminho da tela; sem trava viraria leitor de disco."""
    cliente = _cliente(tmp_path, _transporte({}))
    alvo = tmp_path.parent / "segredo.txt"
    alvo.write_text("conteudo privado")

    resposta = cliente.get("/api/audio", params={"caminho": str(alvo)})

    assert resposta.status_code == 403


def test_rota_audio_serve_arquivo_de_dentro(tmp_path: Path) -> None:
    config = _config(tmp_path)
    app = FastAPI()
    app.include_router(criar_router(config))
    cliente = TestClient(app)
    arquivo = config.saidas / "prova.wav"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(_wav())

    resposta = cliente.get("/api/audio", params={"caminho": str(arquivo)})

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("audio/wav")


def test_rota_dublar_recusa_idioma_inexistente(tmp_path: Path) -> None:
    """Antes isto devolvia 500, porque o erro do tradutor não era tratado.

    A validação acontece antes de tocar no áudio, então o teste é rápido e não
    depende de nenhum servidor.
    """
    cliente = _cliente(tmp_path, _transporte({}))

    resposta = cliente.post(
        "/api/dublar",
        files={"arquivo": ("teste.wav", _wav(), "audio/wav")},
        data={"destino": "klingon"},
    )

    assert resposta.status_code == 422
    assert "desconhecido" in resposta.json()["detail"]


def test_dublar_valida_antes_de_transcrever(tmp_path: Path) -> None:
    """Idioma errado tem que ser recusado sem nem abrir o áudio."""
    config = _config(tmp_path)

    def handler(requisicao: httpx.Request) -> httpx.Response:
        raise AssertionError(f"não deveria chamar a base: {requisicao.url}")

    with pytest.raises(dublar.ErroDublagem) as erro:
        dublar.dublar(
            arquivo=io.BytesIO(_wav()),
            nome_arquivo="teste.wav",
            destino_idioma="klingon",
            config=config,
            transporte=httpx.MockTransport(handler),
        )

    assert "desconhecido" in str(erro.value)


def test_dublar_exige_destino(tmp_path: Path) -> None:
    config = _config(tmp_path)

    with pytest.raises(dublar.ErroDublagem) as erro:
        dublar.dublar(
            arquivo=io.BytesIO(_wav()),
            nome_arquivo="teste.wav",
            destino_idioma="",
            config=config,
        )

    assert "destino" in str(erro.value)


def test_dublar_traducao_que_falha_vira_erro_tratado(tmp_path: Path) -> None:
    """Pacote de idioma faltando não pode subir como erro interno."""
    config = _config(tmp_path)

    def handler(requisicao: httpx.Request) -> httpx.Response:
        if requisicao.url.path == "/transcribe":
            return httpx.Response(200, json={
                "text": "Bom dia, tudo bem?", "language": "pt", "engine": "fake",
            })
        return httpx.Response(400, json={
            "error": "no pack", "code": "argos_pack_missing",
            "pairs": [{"source_lang": "pt", "target_lang": "ja", "installed": False}],
        })

    with pytest.raises(dublar.ErroDublagem) as erro:
        dublar.dublar(
            arquivo=io.BytesIO(_wav()),
            nome_arquivo="teste.wav",
            destino_idioma="ja",
            config=config,
            origem_idioma="pt",
            transporte=httpx.MockTransport(handler),
        )

    assert "não deu para traduzir" in str(erro.value)


def test_dublar_pede_auto_ao_transcritor_quando_nao_escolhem_origem(
    tmp_path: Path,
) -> None:
    """Medido: o `language` da base é eco do enviado, então não serve de detecção.

    O que importa aqui é o pedido que sai para o transcritor: sem origem escolhida,
    tem que ser "auto". A síntese no fim pode falhar ou não (depende da base), e
    isso não interessa a este teste.
    """
    config = _config(tmp_path)
    idiomas_enviados: list[str] = []

    def handler(requisicao: httpx.Request) -> httpx.Response:
        if requisicao.url.path == "/transcribe":
            corpo = requisicao.read().decode(errors="ignore")
            idiomas_enviados.append(
                "auto" if 'name="language"' in corpo and "auto" in corpo else corpo[-40:]
            )
            return httpx.Response(200, json={
                "text": "Good morning, this is a test.", "language": "pt", "engine": "fake",
            })
        if requisicao.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "modelo"}]})
        if requisicao.url.path == "/api/chat":
            return httpx.Response(200, json={
                "message": {"content": "en", "thinking": ""}
            })
        if requisicao.url.path == "/dub/translate":
            return httpx.Response(200, json={
                "translated": [{"id": "0", "text": "Bom dia, isto é um teste."}],
            })
        raise AssertionError(f"rota inesperada: {requisicao.url}")

    try:
        dublar.dublar(
            arquivo=io.BytesIO(_wav()),
            nome_arquivo="teste.wav",
            destino_idioma="pb",
            config=config,
            transporte=httpx.MockTransport(handler),
        )
    except dublar.ErroDublagem:
        # a síntese pode não ser alcançada neste teste; não é o ponto
        pass

    assert idiomas_enviados, "nem chamou o transcritor"
    assert idiomas_enviados[0] == "auto", idiomas_enviados
