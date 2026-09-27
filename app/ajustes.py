"""Controles de qualidade que a base aceita, com limite honesto em cada um.

Todos são opcionais: sem eles, vale o padrão da base. Com eles, o pedido chega no /generate.
Fonte dos nomes e dos padrões: `openapi.json` da própria base (lido em 27/09/2026).
"""

from __future__ import annotations

from typing import Any

# nome do campo -> (minimo, maximo, tipo, padrao da base, explicacao em portugues)
NUMERICOS: dict[str, tuple[float, float, type, str]] = {
    "num_step": (4, 64, int, "16 (rápido) ou 32 (mais limpo)"),
    "guidance_scale": (0.5, 5.0, float, "2,0"),
    "position_temperature": (0.0, 10.0, float, "5,0 (maior é mais expressivo e mais artefato)"),
    "class_temperature": (0.0, 5.0, float, "0,0 (zero é guloso)"),
    "max_chunk_chars": (200, 2000, int, "800"),
    "crossfade_ms": (0, 500, int, "50"),
}

BOOLEANOS = ("denoise", "postprocess_output", "pronounce")

EFEITOS = ("broadcast", "cinematic", "podcast", "raw")

ROTULO = {
    "num_step": "passos",
    "guidance_scale": "guia",
    "position_temperature": "expressividade",
    "class_temperature": "variação de classe",
    "max_chunk_chars": "bloco máximo",
    "crossfade_ms": "transição",
    "denoise": "limpeza de ruído",
    "postprocess_output": "corte de silêncio",
    "pronounce": "pronúncia",
    "effect_preset": "efeito",
}


def _booleano(nome: str, valor: Any) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    texto = str(valor).strip().lower()
    if texto in ("true", "1", "sim", "on"):
        return "true"
    if texto in ("false", "0", "nao", "não", "off"):
        return "false"
    raise ValueError(f"{ROTULO.get(nome, nome)} deve ser verdadeiro ou falso")


def normalizar(bruto: Any) -> dict[str, str]:
    """Valida os ajustes e devolve o que vai para a base. Vazio significa: usa o padrão dela."""
    if bruto in (None, {}):
        return {}
    if not isinstance(bruto, dict):
        raise TypeError("ajustes deve ser um objeto com os controles de qualidade")

    saida: dict[str, str] = {}
    for nome, valor in bruto.items():
        if valor in (None, ""):
            continue
        if nome in NUMERICOS:
            minimo, maximo, tipo, _ = NUMERICOS[nome]
            try:
                numero = tipo(float(valor))
            except (TypeError, ValueError) as erro:
                raise ValueError(f"{ROTULO[nome]} deve ser um número") from erro
            if not minimo <= numero <= maximo:
                raise ValueError(f"{ROTULO[nome]} deve estar entre {minimo} e {maximo}")
            saida[nome] = str(numero)
        elif nome in BOOLEANOS:
            saida[nome] = _booleano(nome, valor)
        elif nome == "effect_preset":
            efeito = str(valor).strip().lower()
            if efeito not in EFEITOS:
                raise ValueError(f"efeito deve ser um destes: {', '.join(EFEITOS)}")
            saida[nome] = efeito
        elif nome == "seed":
            try:
                saida["seed"] = str(int(valor))
            except (TypeError, ValueError) as erro:
                raise ValueError("semente deve ser um número inteiro") from erro
        else:
            raise ValueError(f"ajuste desconhecido: {nome}")
    return saida


def resumo(ajustes: dict[str, str], velocidade: float = 1.0) -> str:
    """Frase curta para mostrar na tela o que foi realmente pedido."""
    if not ajustes and velocidade == 1.0:
        return "padrão do motor"
    partes = []
    for nome, valor in ajustes.items():
        if nome == "effect_preset":
            partes.append(valor)
        elif nome in BOOLEANOS:
            partes.append(f"{ROTULO[nome]} {'ligada' if valor == 'true' else 'desligada'}")
        else:
            partes.append(f"{ROTULO.get(nome, nome)} {valor}")
    if velocidade != 1.0:
        partes.append(f"velocidade {velocidade:g}")
    return ", ".join(partes)
