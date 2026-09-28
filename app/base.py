from __future__ import annotations

import io
import wave
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import httpx

from app.config import Configuracao

# Saída crua do modelo, sem os retoques que a base aplica por conta própria.
# Ver a explicação dentro de montar_corpo para a medição que sustenta isto.
PADROES_FIEIS: dict[str, str] = {
    "effect_preset": "raw",
    "denoise": "false",
}


class ErroBase(RuntimeError):
    pass


def saudavel(config: Configuracao) -> bool:
    requisicao = Request(f"{config.base_url}/health", method="GET")
    try:
        with urlopen(requisicao, timeout=min(config.timeout_s, 3.0)) as resposta:
            return 200 <= resposta.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def listar_motores(config: Configuracao) -> dict[str, object]:
    with httpx.Client(timeout=min(config.timeout_s, 30.0)) as cliente:
        resposta = cliente.get(f"{config.base_url}/engines/tts")
        resposta.raise_for_status()
        return resposta.json()


def selecionar_motor(config: Configuracao, motor: str) -> None:
    try:
        with httpx.Client(timeout=min(config.timeout_s, 30.0)) as cliente:
            resposta = cliente.post(
                f"{config.base_url}/engines/select",
                json={"family": "tts", "backend_id": motor},
            )
            resposta.raise_for_status()
    except httpx.HTTPStatusError as erro:
        raise ErroBase(f"a base recusou o motor: {erro.response.text}") from erro
    except httpx.HTTPError as erro:
        raise ErroBase(f"falha ao falar com a base: {erro}") from erro


def montar_corpo(
    *,
    texto: str,
    motor: str,
    perfil_id: str | None,
    idioma: str,
    velocidade: float,
    semente: int | None,
    ajustes: dict[str, str] | None = None,
) -> dict[str, str]:
    """Monta o formulário que vai para o /generate da base. Puro e testável, sem rede."""
    corpo = {
        "text": texto,
        "engine": motor,
        "language": idioma,
        "speed": str(velocidade),
        "stream": "false",
        # Quando estes campos não vão, a base aplica os padrões DELA: limpeza de
        # ruído ligada e preset de efeito "broadcast", que comprime e equaliza.
        # Medido em 28/09/2026, mesma voz, texto e semente: fidelidade de 0,7751
        # com o padrão da base contra 0,7842 com a saída crua, e a diferença entre
        # os dois áudios é de -23 dBFS, ou seja, audível. Clonar bem quer o modelo
        # sem retoque, então o padrão daqui é cru, e quem quiser efeito pede.
        **PADROES_FIEIS,
    }
    if perfil_id:
        corpo["profile_id"] = perfil_id
    corpo.update(ajustes or {})
    # O argumento explícito é a fonte de verdade; zero também é uma semente.
    if semente is not None:
        corpo["seed"] = str(semente)
    return corpo


def validar_wav(dados: bytes) -> None:
    """Recusa respostas de sucesso sem WAV PCM completo, antes de persistir."""
    try:
        if (
            len(dados) < 12
            or dados[:4] != b"RIFF"
            or dados[8:12] != b"WAVE"
            or int.from_bytes(dados[4:8], "little") + 8 != len(dados)
        ):
            raise ValueError("cabecalho ou tamanho RIFF invalido")
        with wave.open(io.BytesIO(dados), "rb") as leitor:
            quadros = leitor.getnframes()
            esperado = quadros * leitor.getnchannels() * leitor.getsampwidth()
            if quadros <= 0 or leitor.getframerate() <= 0:
                raise ValueError("audio vazio ou taxa invalida")
            if len(leitor.readframes(quadros)) != esperado:
                raise ValueError("quadros truncados")
    except (wave.Error, EOFError, ValueError, TypeError, OSError) as erro:
        raise ErroBase("a base nao devolveu um WAV valido e completo") from erro


def gerar_audio(
    config: Configuracao,
    *,
    texto: str,
    motor: str,
    perfil_id: str | None,
    idioma: str,
    velocidade: float,
    semente: int | None,
    ajustes: dict[str, str] | None = None,
) -> bytes:
    corpo = montar_corpo(
        texto=texto,
        motor=motor,
        perfil_id=perfil_id,
        idioma=idioma,
        velocidade=velocidade,
        semente=semente,
        ajustes=ajustes,
    )
    try:
        with httpx.Client(timeout=config.timeout_s) as cliente:
            resposta = cliente.post(f"{config.base_url}/generate", data=corpo)
            resposta.raise_for_status()
            validar_wav(resposta.content)
            return resposta.content
    except httpx.HTTPStatusError as erro:
        motivo = erro.response.text.strip()
        raise ErroBase(f"a base recusou a geracao: {motivo}") from erro
    except httpx.HTTPError as erro:
        raise ErroBase(f"falha ao falar com a base: {erro}") from erro
