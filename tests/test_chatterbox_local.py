"""Regressao da mensagem de erro do Chatterbox e da escolha de dispositivo.

Defeito de 29/09/2026: quando o processo do motor morria por falta de memoria de
video, o Windows nao escrevia nada no stderr, e o adaptador transformava isso em
"Chatterbox: Erro sem diagnostico do motor" — a tela nao dava nada para investigar.
O dono viu essa mensagem e nao havia como saber que o motor estava funcionando.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import chatterbox_local
from app.config import carregar_config

PERFIL = "vz-teste"


class _BancoFalso:
    """Perfil clonado com consentimento, sem tocar no banco real do dono."""

    def perfil(self, _perfil_id: str) -> dict[str, str]:
        return {"origem": "clonado", "arquivo_referencia": "dados/referencias/ref.wav"}

    def tem_consentimento(self, _perfil_id: str) -> bool:
        return True

    def fechar(self) -> None:
        return None


class _ProcessoFalso:
    def __init__(self, returncode: int, stderr: str = "", stdout: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


def _preparar(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, processo: _ProcessoFalso):
    referencias = tmp_path / "dados" / "referencias"
    referencias.mkdir(parents=True)
    (referencias / "ref.wav").write_bytes(b"RIFF....WAVE")

    config = carregar_config({"ESTUDIO_DADOS": "dados", "ESTUDIO_SAIDAS": "saidas/audio"}, raiz=tmp_path)
    monkeypatch.setattr(chatterbox_local, "disponivel", lambda: True)
    monkeypatch.setattr(chatterbox_local.cofre, "abrir", lambda *_a, **_k: _BancoFalso())
    monkeypatch.setattr(chatterbox_local.subprocess, "run", lambda *_a, **_k: processo)
    return config


def test_stderr_vazio_diz_que_morreu_sem_erro_e_nao_engole_o_codigo(monkeypatch, tmp_path) -> None:
    """O caso pior (morto por memoria) e o que mais precisa de mensagem util."""
    config = _preparar(monkeypatch, tmp_path, _ProcessoFalso(returncode=3221225477))
    monkeypatch.setattr(chatterbox_local, "memoria_livre_mib", lambda: 1143)

    with pytest.raises(Exception) as capturado:
        chatterbox_local.sintetizar_chatterbox("texto", config=config, perfil_id=PERFIL)

    texto = str(capturado.value)
    assert "sem diagnóstico do motor" not in texto
    assert "3221225477" in texto
    assert "1143 MiB" in texto
    assert "memória" in texto


def test_stderr_com_conteudo_preserva_o_motivo_real(monkeypatch, tmp_path) -> None:
    """Antes sobrevivia so a ultima linha; o miolo do traceback era descartado."""
    erro_do_motor = (
        "Traceback (most recent call last):\n"
        "  File \"runner.py\", line 169, in generate\n"
        "    model, revisions = load_ptbr_model(device)\n"
        "ValueError: reference_audio invalido\n"
    )
    config = _preparar(monkeypatch, tmp_path, _ProcessoFalso(returncode=1, stderr=erro_do_motor))

    with pytest.raises(Exception) as capturado:
        chatterbox_local.sintetizar_chatterbox("texto", config=config, perfil_id=PERFIL)

    texto = str(capturado.value)
    assert "código 1" in texto
    assert "reference_audio invalido" in texto


def test_dispositivo_e_cpu_quando_falta_memoria_e_cuda_com_folga(monkeypatch) -> None:
    """Nunca 'auto': com a base na GPU o motor escolhia CUDA e morria por OOM."""
    monkeypatch.setattr(chatterbox_local, "memoria_livre_mib", lambda: 900)
    assert chatterbox_local.dispositivo_seguro() == "cpu"

    monkeypatch.setattr(chatterbox_local, "memoria_livre_mib", lambda: 12_000)
    assert chatterbox_local.dispositivo_seguro() == "cuda"

    monkeypatch.setattr(chatterbox_local, "memoria_livre_mib", lambda: None)
    assert chatterbox_local.dispositivo_seguro() == "cpu"
