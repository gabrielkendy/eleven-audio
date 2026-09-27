"""Adaptador isolado do Chatterbox PT-BR. Nenhuma alteração na base VoiceStudio."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

from app import base, cofre, saidas
from app.config import Configuracao

RAIZ = Path(__file__).resolve().parents[1] / "experimentos" / "chatterbox-ptbr"
PYTHON = RAIZ / ".venv" / "Scripts" / "python.exe"
TRAVA = threading.Lock()


def disponivel() -> bool:
    return PYTHON.is_file() and (RAIZ / "READY.json").is_file() and (RAIZ / "runner.py").is_file()


def sintetizar_chatterbox(texto: str, *, config: Configuracao, perfil_id: str, semente: int = 2026) -> dict:
    if not disponivel():
        raise base.ErroBase("Chatterbox PT-BR ainda não passou pela validação local.")
    if not perfil_id:
        raise base.ErroBase("Selecione um perfil clonado com referência original.")
    banco = cofre.abrir(config.dados / "estudio.db")
    try:
        perfil = banco.perfil(perfil_id)
        consentido = banco.tem_consentimento(perfil_id)
    finally:
        banco.fechar()
    if not perfil or perfil["origem"] != "clonado" or not consentido:
        raise base.ErroBase("Chatterbox requer uma voz clonada com consentimento registrado.")
    pasta = (config.dados / "referencias").resolve()
    nome = str(perfil.get("arquivo_referencia") or "").replace("\\", "/").rsplit("/", 1)[-1]
    referencia = (pasta / nome).resolve()
    if not referencia.is_relative_to(pasta) or not referencia.is_file():
        raise base.ErroBase("Referência original não encontrada.")
    if not TRAVA.acquire(blocking=False):
        raise base.ErroBase("O Chatterbox já está gerando. Aguarde terminar antes de enviar outra solicitação.")
    inicio = time.perf_counter()
    try:
        arquivo = saidas.pasta_do_dia(config.saidas) / f"chatterbox_ptbr_{uuid4().hex[:12]}.wav"
        pedido = {"text": texto, "locale": "pt-BR", "reference_audio": str(referencia),
                  "output": str(arquivo), "seed": semente, "cfg_weight": 0.3,
                  "exaggeration": 0.35, "temperature": 0.7, "device": "auto"}
        ambiente = dict(os.environ)
        ambiente.pop("PYTHONPATH", None)
        ambiente.update(PYTHONUTF8="1", HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1",
                        HF_HUB_DISABLE_TELEMETRY="1")
        try:
            processo = subprocess.run([str(PYTHON), str(RAIZ / "runner.py")],
                                      input=json.dumps(pedido, ensure_ascii=False), text=True,
                                      encoding="utf-8", capture_output=True, env=ambiente,
                                      timeout=min(config.timeout_s, 600), cwd=RAIZ, check=False)
        except subprocess.TimeoutExpired as erro:
            raise base.ErroBase("O Chatterbox excedeu o tempo máximo e foi encerrado. Nenhum áudio foi registrado.") from erro
        if processo.returncode:
            detalhe = processo.stderr.strip().splitlines()[-1:] or ["Erro sem diagnóstico do motor."]
            raise base.ErroBase("Chatterbox: " + detalhe[0][:500])
        try:
            metadados = json.loads(processo.stdout.strip().splitlines()[-1])
            base.validar_wav(arquivo.read_bytes())
        except (ValueError, OSError, IndexError) as erro:
            raise base.ErroBase("O motor não devolveu um WAV íntegro e metadados válidos.") from erro
        if metadados.get("status") != "ok":
            raise base.ErroBase("O motor não confirmou a geração.")
        return {"arquivo": str(arquivo), **saidas.medir(arquivo), "motor": "chatterbox-ptbr",
                "duracao_geracao_s": round(time.perf_counter() - inicio, 6),
                "dispositivo": metadados.get("device_used", "nao_informado"),
                "modelo": metadados.get("model_revisions"), "marca_dagua": "PerTh"}
    finally:
        TRAVA.release()
