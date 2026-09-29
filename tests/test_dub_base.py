"""Testes da dublagem pela pipeline da base.

O que estes testes protegem, aprendido lendo o codigo da base e medindo ao vivo:

  - o upload e assincrono; transcrever antes do `ready` devolve "Job not found"
  - o `source_lang` que a base devolve NAO e confiavel (marcou 'en' em portugues)
  - `start`/`end` chegam como TEXTO, nao numero
  - `/dub/audio` devolve a ENTRADA; o dublado esta em `/dub/download-audio`
  - `profile_id` precisa ir em TODOS os segmentos, senao a base clona o falante
    original em vez de usar a voz escolhida
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app import dub_base
from app.config import carregar_config


def _config(tmp_path: Path):
    return carregar_config(
        {
            "ESTUDIO_DADOS": str(tmp_path / "dados"),
            "ESTUDIO": str(tmp_path / "saidas"),
            "ESTUDIO_BASE_URL": "http://base-falsa:3900",
        },
        raiz=tmp_path,
    )


def _sse(*eventos: dict) -> bytes:
    return b"".join(
        f"data: {json.dumps(e)}\n\n".encode() for e in eventos
    )


def _transporte(**rotas):
    """Transporte falso. Cada chave e um trecho do caminho que responde."""
    chamadas: list[dict] = []

    def handler(requisicao: httpx.Request) -> httpx.Response:
        caminho = requisicao.url.path
        chamadas.append(
            {
                "metodo": requisicao.method,
                "caminho": caminho,
                "corpo": requisicao.read().decode("utf-8", "replace"),
            }
        )
        for trecho, resposta in rotas.items():
            if trecho in caminho:
                if isinstance(resposta, httpx.Response):
                    return resposta
                return httpx.Response(200, **resposta)
        return httpx.Response(404, json={"detail": f"rota nao prevista: {caminho}"})

    transporte = httpx.MockTransport(handler)
    transporte.chamadas = chamadas  # type: ignore[attr-defined]
    return transporte


# ─── envio ──────────────────────────────────────────────────────────────────


def test_envio_aceita_o_audio_e_devolve_os_identificadores(tmp_path: Path) -> None:
    transporte = _transporte(**{"/dub/upload": {"json": {"job_id": "abc123", "task_id": "prep_abc123"}}})

    envio = dub_base.enviar_audio(b"RIFF", "entrada.wav", _config(tmp_path), "pt", transporte)

    assert envio == {"job_id": "abc123", "task_id": "prep_abc123"}


def test_envio_sem_identificador_vira_erro_claro(tmp_path: Path) -> None:
    """Sem job_id nao ha o que acompanhar: melhor parar aqui do que seguir e falhar longe."""
    transporte = _transporte(**{"/dub/upload": {"json": {"filename": "x.wav"}}})

    with pytest.raises(dub_base.ErroDublagemBase, match="identificador"):
        dub_base.enviar_audio(b"RIFF", "x.wav", _config(tmp_path), "", transporte)


def test_envio_mostra_o_motivo_que_a_base_deu(tmp_path: Path) -> None:
    transporte = _transporte(
        **{"/dub/upload": httpx.Response(400, json={"detail": "input_type must be 'video' or 'audio'"})}
    )

    with pytest.raises(dub_base.ErroDublagemBase, match="input_type"):
        dub_base.enviar_audio(b"RIFF", "x.wav", _config(tmp_path), "", transporte)


# ─── acompanhamento do preparo ──────────────────────────────────────────────


def test_acompanhar_para_no_ready(tmp_path: Path) -> None:
    """`ready` e o que libera a transcricao. Passar dele seria esperar para sempre."""
    transporte = _transporte(
        **{
            "/tasks/stream/prep_abc": {
                "content": _sse(
                    {"type": "extract_start"},
                    {"type": "extract_done", "duration": 10.0},
                    {"type": "ready", "job_id": "abc"},
                    {"type": "nunca_deveria_chegar"},
                )
            }
        }
    )

    evento = dub_base.acompanhar("prep_abc", _config(tmp_path), 60, transporte)

    assert evento["type"] == "ready"


def test_acompanhar_reconhece_o_done_da_geracao(tmp_path: Path) -> None:
    transporte = _transporte(
        **{
            "/tasks/stream/dub_x": {
                "content": _sse(
                    {"type": "progress", "current": 0, "total": 2},
                    {"type": "done", "segments_processed": 2, "sync_scores": [1.05, 0.98]},
                )
            }
        }
    )

    evento = dub_base.acompanhar("dub_x", _config(tmp_path), 60, transporte)

    assert evento["type"] == "done"
    assert evento["sync_scores"] == [1.05, 0.98]


def test_acompanhar_ignora_linhas_que_nao_sao_evento(tmp_path: Path) -> None:
    """O SSE manda comentarios de keep-alive e linhas vazias no meio."""
    transporte = _transporte(
        **{
            "/tasks/stream/t": {
                "content": b": keep-alive\n\nqualquer coisa\n\ndata: {\"type\": \"ready\"}\n\n"
            }
        }
    )

    evento = dub_base.acompanhar("t", _config(tmp_path), 60, transporte)

    assert evento["type"] == "ready"


def test_acompanhar_sem_tarefa_avisa(tmp_path: Path) -> None:
    with pytest.raises(dub_base.ErroDublagemBase, match="tarefa"):
        dub_base.acompanhar("", _config(tmp_path), 60, _transporte())


def test_acompanhar_sem_evento_nenhum_nao_finge_sucesso(tmp_path: Path) -> None:
    transporte = _transporte(**{"/tasks/stream/t": {"content": b""}})

    with pytest.raises(dub_base.ErroDublagemBase, match="nenhum evento"):
        dub_base.acompanhar("t", _config(tmp_path), 60, transporte)


# ─── transcricao ────────────────────────────────────────────────────────────


def test_transcricao_sem_fala_vira_erro(tmp_path: Path) -> None:
    transporte = _transporte(**{"/dub/transcribe": {"json": {"job_id": "a", "segments": []}}})

    with pytest.raises(dub_base.ErroDublagemBase, match="nao encontrou fala"):
        dub_base.transcrever("a", _config(tmp_path), transporte)


# ─── geracao ────────────────────────────────────────────────────────────────


def test_profile_id_vai_em_todos_os_segmentos(tmp_path: Path) -> None:
    """Sem isto, a base clona o falante original em vez de usar a voz escolhida.

    E o ponto do recurso: quem quer a voz original usa o padrao da base, quem
    escolheu uma voz precisa que ela chegue em cada trecho.
    """
    transporte = _transporte(**{"/dub/generate": {"json": {"task_id": "dub_1"}}})
    segmentos = [
        {"id": "s1", "text": "one", "start": 0.0, "end": 2.0, "speaker_id": "Speaker 1"},
        {"id": "s2", "text": "two", "start": 2.0, "end": 4.0, "speaker_id": "Speaker 2"},
    ]

    dub_base.gerar("job1", segmentos, "en", "vz-abc", _config(tmp_path), transporte=transporte)

    enviados = json.loads(transporte.chamadas[0]["corpo"])["segments"]
    assert [s["profile_id"] for s in enviados] == ["vz-abc", "vz-abc"]


def test_geracao_recusa_estrategia_de_tempo_desconhecida(tmp_path: Path) -> None:
    """Estrategia invalida faria a base escolher sozinha, sem a pessoa saber."""
    with pytest.raises(dub_base.ErroDublagemBase, match="estrategia de tempo"):
        dub_base.gerar(
            "j", [{"id": "s", "text": "x"}], "en", "vz", _config(tmp_path), tempo="inventado"
        )


def test_geracao_sem_trecho_nao_chama_a_base(tmp_path: Path) -> None:
    with pytest.raises(dub_base.ErroDublagemBase, match="trechos"):
        dub_base.gerar("j", [], "en", "vz", _config(tmp_path))


@pytest.mark.parametrize("tempo", dub_base.ESTRATEGIAS_DE_TEMPO)
def test_todas_as_estrategias_de_tempo_sao_aceitas(tmp_path: Path, tempo: str) -> None:
    transporte = _transporte(**{"/dub/generate": {"json": {"task_id": "dub_1"}}})

    dub_base.gerar(
        "j", [{"id": "s", "text": "x", "start": 0.0, "end": 1.0}], "en", "vz",
        _config(tmp_path), tempo=tempo, transporte=transporte,
    )

    assert json.loads(transporte.chamadas[0]["corpo"])["timing_strategy"] == tempo


# ─── tempo como texto ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("0.87", 0.87), (4.28, 4.28), ("", 0.0), (None, 0.0), ("nao e numero", 0.0)],
)
def test_tempo_vem_como_texto_e_vira_numero(entrada: object, esperado: float) -> None:
    """Medido: a base devolve `start`/`end` como TEXTO ('0.87').

    Sem converter, o tempo vai como string e o encaixe da fala no tempo falha sem
    avisar, entregando audio fora de sincronia.
    """
    assert dub_base._numero(entrada) == esperado


def test_juntar_tempo_com_texto_traduzido() -> None:
    segmentos = [
        {"id": "a", "start": "0.87", "end": "4.28", "speaker_id": "Speaker 1"},
        {"id": "b", "start": "4.28", "end": "9.98", "speaker_id": "Speaker 2"},
    ]

    prontos = dub_base._segmentos_para_gerar(segmentos, ["one", "two"])

    assert prontos[0] == {
        "id": "a", "text": "one", "start": 0.87, "end": 4.28, "speaker_id": "Speaker 1"
    }
    assert prontos[1]["end"] == 9.98


def test_segmento_sem_id_ganha_um() -> None:
    prontos = dub_base._segmentos_para_gerar([{"start": 0, "end": 1}], ["x"])
    assert prontos[0]["id"] == "seg_0"


# ─── download ───────────────────────────────────────────────────────────────


def test_baixar_usa_download_audio_e_nao_audio(tmp_path: Path) -> None:
    """`/dub/audio` devolve o material de ENTRADA, nao o dublado.

    Confundir os dois entrega o audio original com nome de dublado, e o erro so
    aparece quando a pessoa ouve.
    """
    transporte = _transporte(**{"/dub/download-audio": {"content": b"X" * 4096}})
    destino = tmp_path / "saida" / "dub.wav"

    tamanho = dub_base.baixar("abc", destino, _config(tmp_path), transporte)

    assert tamanho == 4096
    assert destino.read_bytes() == b"X" * 4096
    assert transporte.chamadas[0]["caminho"] == "/dub/download-audio/abc"


def test_dublado_vazio_vira_erro(tmp_path: Path) -> None:
    transporte = _transporte(**{"/dub/download-audio": {"content": b"curto"}})

    with pytest.raises(dub_base.ErroDublagemBase, match="vazio"):
        dub_base.baixar("abc", tmp_path / "d.wav", _config(tmp_path), transporte)


# ─── fluxo completo ─────────────────────────────────────────────────────────


def _fluxo_completo(**extras) -> httpx.MockTransport:
    rotas = {
        "/dub/upload": {"json": {"job_id": "job1", "task_id": "prep_job1"}},
        "/tasks/stream/prep_job1": {"content": _sse({"type": "ready", "duration": 10.0})},
        "/dub/transcribe": {
            "json": {
                "job_id": "job1",
                "source_lang": "en",  # mentira de proposito: o audio esta em portugues
                "full_transcript": "Bom dia, tudo bem com voce?",
                "segments": [
                    {
                        "id": "s1",
                        "text": "Bom dia, tudo bem com voce?",
                        "start": "0.87",
                        "end": "4.28",
                        "speaker_id": "Speaker 1",
                        "words": [{"text": "Bom", "start": 0.0, "end": 1.0}],
                    }
                ],
            }
        },
        "/dub/generate": {"json": {"task_id": "dub_job1"}},
        # O tradutor da base (Argos) responde aqui e devolve `translated`.
        # Entra no mock porque o fluxo cai nele quando o modelo local nao responde.
        "/dub/translate": {
            "json": {"translated": [{"id": "0", "text": "Good morning, how are you?"}]}
        },
        "/tasks/stream/dub_job1": {
            "content": _sse({"type": "done", "segments_processed": 1, "sync_scores": [1.02]})
        },
        "/dub/download-audio": {"content": b"R" * 8192},
    }
    rotas.update(extras)
    return _transporte(**rotas)


def _config_com_ollama(tmp_path: Path, resposta_idioma: str = "Portuguese"):
    """Config mais um Ollama falso, para a deteccao de idioma pelo texto."""
    rotas = {
        "/api/tags": {"json": {"models": [{"name": "modelo"}]}},
        "/api/chat": {"json": {"message": {"content": resposta_idioma, "thinking": ""}}},
    }
    return rotas


def test_fluxo_completo_entrega_o_audio_e_a_conta_do_processo(tmp_path: Path) -> None:
    transporte = _fluxo_completo(**_config_com_ollama(tmp_path))

    r = dub_base.dublar_pela_base(
        conteudo=b"RIFF",
        nome_arquivo="entrada.wav",
        destino_idioma="en",
        perfil_id="vz-abc",
        config=_config(tmp_path),
        transporte=transporte,
    )

    assert r["origem"] == "pb", "o 'en' que a base devolveu foi ignorado"
    assert r["destino"] == "en"
    assert r["falantes"] == ["Speaker 1"]
    assert r["varios_falantes"] is False
    assert r["tamanho_bytes"] == 8192
    assert r["timing"] == dub_base.TEMPO_PADRAO
    assert r["sync_scores"] == [1.02]
    assert Path(r["arquivo"]).exists()


def test_fluxo_completo_nao_confia_no_idioma_da_base(tmp_path: Path) -> None:
    """Medido: a base marcou 'en' num audio claramente em portugues.

    Seguir esse campo faria o audio sair traduzido do idioma errado, e a pessoa
    so descobriria ouvindo o resultado.
    """
    transporte = _fluxo_completo(**_config_com_ollama(tmp_path))

    r = dub_base.dublar_pela_base(
        conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="en",
        perfil_id="vz", config=_config(tmp_path), transporte=transporte,
    )

    assert r["origem"] == "pb"


def test_fluxo_para_quando_o_audio_ja_esta_no_idioma_pedido(tmp_path: Path) -> None:
    transporte = _fluxo_completo(**_config_com_ollama(tmp_path, resposta_idioma="English"))

    with pytest.raises(dub_base.ErroDublagemBase, match="ja esta em"):
        dub_base.dublar_pela_base(
            conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="en",
            perfil_id="vz", config=_config(tmp_path), transporte=transporte,
        )


def test_fluxo_sem_deteccao_pede_a_origem_na_mao(tmp_path: Path) -> None:
    """Sem saber o idioma, seguir produziria audio errado. Melhor parar com recado."""
    transporte = _fluxo_completo(
        **{
            "/api/tags": {"json": {"models": [{"name": "m"}]}},
            "/api/chat": {"json": {"message": {"content": "nao sei", "thinking": ""}}},
        }
    )

    with pytest.raises(dub_base.ErroDublagemBase, match="na mao"):
        dub_base.dublar_pela_base(
            conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="en",
            perfil_id="vz", config=_config(tmp_path), transporte=transporte,
        )


def test_fluxo_aceita_origem_informada_na_mao(tmp_path: Path) -> None:
    """Com a origem escolhida, nem consulta o detector."""
    transporte = _fluxo_completo()

    r = dub_base.dublar_pela_base(
        conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="en",
        perfil_id="vz", config=_config(tmp_path), origem_idioma="pb",
        transporte=transporte,
    )

    assert r["origem"] == "pb"


def test_fluxo_recusa_idioma_de_destino_desconhecido(tmp_path: Path) -> None:
    with pytest.raises(dub_base.ErroDublagemBase, match="destino desconhecido"):
        dub_base.dublar_pela_base(
            conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="klingon",
            perfil_id="vz", config=_config(tmp_path), transporte=_transporte(),
        )


def test_fluxo_para_quando_o_preparo_falha(tmp_path: Path) -> None:
    transporte = _fluxo_completo(
        **{
            "/tasks/stream/prep_job1": {
                "content": _sse({"type": "error", "message": "codec nao suportado"})
            }
        }
    )

    with pytest.raises(dub_base.ErroDublagemBase, match="preparo"):
        dub_base.dublar_pela_base(
            conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="en",
            perfil_id="vz", config=_config(tmp_path), origem_idioma="pb",
            transporte=transporte,
        )


def test_fluxo_para_quando_a_geracao_falha(tmp_path: Path) -> None:
    transporte = _fluxo_completo(
        **{
            "/tasks/stream/dub_job1": {
                "content": _sse({"type": "error", "message": "voz sumiu"})
            }
        }
    )

    with pytest.raises(dub_base.ErroDublagemBase, match="geracao"):
        dub_base.dublar_pela_base(
            conteudo=b"RIFF", nome_arquivo="e.wav", destino_idioma="en",
            perfil_id="vz", config=_config(tmp_path), origem_idioma="pb",
            transporte=transporte,
        )


def test_limpeza_do_job_nao_derruba_o_que_ja_foi_entregue(tmp_path: Path) -> None:
    """Falhar ao apagar o job nao pode invalidar a dublagem ja baixada."""
    transporte = _transporte(**{"/dub/history": httpx.Response(500, json={"detail": "boom"})})

    assert dub_base.limpar_job("j", _config(tmp_path), transporte) is False
