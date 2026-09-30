"""Defeitos achados na revisão de 29/09/2026, virados em teste.

Cada teste aqui existe porque o defeito ACONTECEU. Nenhum foi escrito por
simpatia a cobertura. Se algum destes falhar, alguém reintroduziu algo que já
mordeu de verdade.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import carregar_config
from app.servidor import criar_app


def _cliente(tmp_path: Path) -> TestClient:
    config = carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas/audio",
            "ESTUDIO_MOTOR": "mock",
        },
        raiz=tmp_path,
    )
    return TestClient(criar_app(config, verificar_base=lambda: False))


# ---------------------------------------------------------------------------
# 1. A rota /api/config nao existia.
#
# O front (web/config.js) chamava /api/config desde sempre; o back so tinha
# /api/configuracoes, que devolve os ajustes de geracao, nao a infraestrutura.
# O 404 morria num console.warn e a tela mostrava porta 7800 e pasta de dados
# CHUMBADAS. Trocasse a porta no .env e a tela continuaria mentindo.
# ---------------------------------------------------------------------------


def test_api_config_existe_e_conta_a_infraestrutura(tmp_path: Path) -> None:
    cliente = _cliente(tmp_path)

    resposta = cliente.get("/api/config")

    assert resposta.status_code == 200, (
        "web/config.js chama /api/config: se esta rota sumir, a tela volta a "
        "mostrar porta e pastas chumbadas e nao avisa ninguem"
    )
    corpo = resposta.json()
    assert {"porta", "dados", "saidas", "motor"} <= set(corpo)


def test_api_config_devolve_as_pastas_reais_nao_valores_chumbados(
    tmp_path: Path,
) -> None:
    config = carregar_config(
        {
            "ESTUDIO_DADOS": "dados",
            "ESTUDIO_SAIDAS": "saidas/audio",
            "ESTUDIO_MOTOR": "mock",
            "ESTUDIO_PORT": 7999,
        },
        raiz=tmp_path,
    )
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))

    corpo = cliente.get("/api/config").json()

    assert corpo["porta"] == 7999, "a tela tem que ler a porta do config, nao chumbar"
    assert str(tmp_path) in corpo["dados"]
    assert str(tmp_path) in corpo["saidas"]

    # web/config.js le estes nomes exatos. Se a rota devolver so base_url, a tela
    # cai no 3900 chumbado e acerta por sorte. Com a base em outra porta, mente.
    assert corpo["porta_base"] == 3900, corpo
    outro = TestClient(
        criar_app(
            carregar_config(
                {"ESTUDIO_PORT": 7801, "ESTUDIO_BASE_URL": "http://127.0.0.1:4999"},
                raiz=tmp_path,
            ),
            verificar_base=lambda: False,
        )
    )
    dados_outro = outro.get("/api/config").json()
    assert dados_outro["porta_base"] == 4999, dados_outro
    assert dados_outro["porta"] == 7801, dados_outro


def test_api_config_nao_e_confundida_com_configuracoes(tmp_path: Path) -> None:
    """/api/config = onde o app mora. /api/configuracoes = como ele gera.

    Sao coisas diferentes de proposito: juntar as duas foi o que deixou a tela
    de configuracao mostrando dado de infraestrutura errado.
    """
    config = carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_MOTOR": "mock"}, raiz=tmp_path
    )
    cliente = TestClient(criar_app(config, verificar_base=lambda: False))

    infra = cliente.get("/api/config").json()
    geracao = cliente.get("/api/configuracoes").json()

    assert "motor" in infra
    assert not {"velocidade", "idioma", "modo"} & set(infra), (
        "/api/config virou copia de /api/configuracoes; a tela de infra voltaria "
        "a ler ajuste de geracao"
    )
    assert {"velocidade", "idioma", "modo"} <= set(geracao)


# ---------------------------------------------------------------------------
# 2. Toda geracao era gravada por cima da anterior quando caia no mesmo segundo.
#
# nome_arquivo() monta o nome com carimbo de SEGUNDO. Cinco geracoes com o mesmo
# motor e o mesmo perfil no mesmo segundo davam o MESMO caminho, e a quinta
# apagava as quatro anteriores. A garantia passou para gravar_bytes, que e' quem
# escreve de verdade.
# ---------------------------------------------------------------------------


def test_nome_de_saida_nao_engole_duas_geracoes_no_mesmo_segundo(tmp_path: Path) -> None:
    from app import saidas

    config = carregar_config(
        {"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio", "ESTUDIO_MOTOR": "mock"},
        raiz=tmp_path,
    )

    gravados = [
        saidas.gravar_bytes(
            config.saidas / saidas.nome_arquivo("omnivoice", "vz-abc"),
            f"audio-{indice}".encode(),
        )
        for indice in range(5)
    ]

    assert len(set(gravados)) == 5, (
        "duas geracoes caíram no mesmo arquivo: a segunda apagou a primeira. "
        "Este e' o defeito que 'nome_arquivo' + 'gravar_bytes' existem para impedir"
    )
    for indice, destino in enumerate(gravados):
        assert destino.read_bytes() == f"audio-{indice}".encode(), (
            "o conteudo do arquivo nao e' o da geracao dele: houve sobrescrita"
        )


def test_gravar_bytes_devolve_o_caminho_que_gravou(tmp_path: Path) -> None:
    """O banco guarda o caminho que a funcao devolve.

    Se ela devolvesse o nome pedido em vez do nome final (com -2), o histórico
    apontaria para um arquivo que nao existe.
    """
    from app import saidas

    alvo = tmp_path / "mesmo-nome.wav"
    saidas.gravar_bytes(alvo, b"primeiro")
    segundo = saidas.gravar_bytes(alvo, b"segundo")

    assert segundo != alvo
    assert segundo.exists()
    assert segundo.read_bytes() == b"segundo"
    assert alvo.read_bytes() == b"primeiro"


def test_geracao_pela_api_nao_perde_audio(tmp_path: Path) -> None:
    """O mesmo defeito, pela porta da frente: a rota de gerar.

    Este e' o teste que interessa ao usuario: se ele gerar tres vezes seguidas
    com o mesmo perfil, os tres audios tem que existir e ter o som deles.
    """
    cliente = _cliente(tmp_path)

    caminhos = []
    for indice in range(3):
        resposta = cliente.post(
            "/api/gerar",
            json={"texto": f"Frase numero {indice}", "perfil_id": None},
        )
        assert resposta.status_code == 200, resposta.text
        caminhos.append(resposta.json()["arquivo"])

    assert len(set(caminhos)) == 3, f"a API reaproveitou caminho: {caminhos}"
    for caminho in caminhos:
        assert Path(caminho).exists()


def test_historico_nao_aponta_para_arquivo_que_nao_existe(tmp_path: Path) -> None:
    """Fecha o ciclo: o que o banco registra tem que estar no disco.

    Sobrescrever arquivo quebraria aqui tambem: o historico guardaria tres
    caminhos, dois deles apagados pela geracao seguinte, e o botao de ouvir
    daria 404 num item que a tela mostra como pronto.
    """
    cliente = _cliente(tmp_path)

    for indice in range(3):
        cliente.post("/api/gerar", json={"texto": f"Frase {indice}", "perfil_id": None})

    historico = cliente.get("/api/historico").json()
    assert len(historico["itens"]) == 3, "gerou tres vezes e o historico nao tem tres"

    for item in historico["itens"]:
        detalhe = cliente.get(f"/api/historico/{item['id']}")
        assert detalhe.status_code == 200, f"item do historico sem arquivo: {item}"
        assert Path(detalhe.json()["arquivo_saida"]).exists(), (
            "o historico mostra um item cujo audio nao existe mais no disco"
        )
