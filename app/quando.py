"""Tempo relativo em português, do jeito que a tela fala: "há 3 horas".

Isolado aqui para poder ser testado sem subir servidor: o histórico mostra a
mesma frase que o ElevenLabs mostra na lista e no detalhe.

Sinal de erro: sem data, devolve "sem data" em vez de inventar.
"""

from __future__ import annotations

from datetime import datetime, timezone


def agora() -> datetime:
    """Agora, com fuso local (mesma origem das datas gravadas no cofre)."""
    return datetime.now(timezone.utc).astimezone()


def _com_fuso(quando: datetime) -> datetime:
    return quando if quando.tzinfo else quando.replace(tzinfo=timezone.utc)


def relativo(iso: str | None, *, referencia: datetime | None = None) -> str:
    """Frase curta em português para uma data ISO. Nunca negativo."""
    if not iso:
        return "sem data"
    try:
        quando = datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return "sem data"

    referencia = _com_fuso(referencia or agora())
    # Data futura (relogio adiantado) nao vira "há -3 horas": satura em agora.
    segundos = max(int((referencia - _com_fuso(quando)).total_seconds()), 0)

    if segundos < 10:
        return "agora mesmo"
    if segundos < 60:
        return f"há {segundos} segundos"

    minutos = segundos // 60
    if minutos < 60:
        return "há 1 minuto" if minutos == 1 else f"há {minutos} minutos"

    horas = minutos // 60
    if horas < 24:
        return "há 1 hora" if horas == 1 else f"há {horas} horas"

    dias = horas // 24
    if dias == 1:
        return "ontem"
    if dias < 30:
        return f"há {dias} dias"

    meses = dias // 30
    if meses < 12:
        return "há 1 mês" if meses == 1 else f"há {meses} meses"

    anos = dias // 365
    return "há 1 ano" if anos <= 1 else f"há {anos} anos"
