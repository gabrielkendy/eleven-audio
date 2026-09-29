"""Tradução de texto, offline, com o catálogo de idiomas do Argos.

Por que existe: a base só traduz **par direto**. Medido em 28/09/2026, dos 50
idiomas do Argos, saindo de `pt` só existem dois pares (`en` e `es`), enquanto
saindo de `en` existem 47. Então "traduzir para qualquer língua" só funciona se
alguém costurar a cascata, e é isso que este módulo faz: tenta o par direto e,
quando não existe, passa pelo inglês.

Detalhe que quase passou: o Argos tem `pt` (português de Portugal) e `pb`
(português do Brasil) como códigos **separados**. Traduzir para `pt` devolve
"como estás, a correr", que soa errado para brasileiro. Quando o pedido é pt-BR,
usamos `pb`.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import Configuracao

# Catálogo do Argos: 50 idiomas, 100 pares. Nomes em português para a tela.
IDIOMAS: dict[str, str] = {
    "sq": "Albanês",
    "de": "Alemão",
    "ar": "Árabe",
    "az": "Azerbaijano",
    "bn": "Bengali",
    "bg": "Búlgaro",
    "ca": "Catalão",
    "zh": "Chinês (simplificado)",
    "zt": "Chinês (tradicional)",
    "ko": "Coreano",
    "cs": "Tcheco",
    "da": "Dinamarquês",
    "sk": "Eslovaco",
    "sl": "Esloveno",
    "es": "Espanhol",
    "eo": "Esperanto",
    "et": "Estoniano",
    "eu": "Basco",
    "fa": "Persa",
    "fi": "Finlandês",
    "fr": "Francês",
    "gl": "Galego",
    "el": "Grego",
    "he": "Hebraico",
    "hi": "Hindi",
    "nl": "Holandês",
    "hu": "Húngaro",
    "id": "Indonésio",
    "en": "Inglês",
    "ga": "Irlandês",
    "it": "Italiano",
    "ja": "Japonês",
    "ky": "Quirguiz",
    "lv": "Letão",
    "lt": "Lituano",
    "ms": "Malaio",
    "nb": "Norueguês",
    "pl": "Polonês",
    "pt": "Português (Portugal)",
    "pb": "Português (Brasil)",
    "ro": "Romeno",
    "ru": "Russo",
    "sv": "Sueco",
    "sw": "Suaíli",
    "tl": "Tagalo",
    "th": "Tailandês",
    "tr": "Turco",
    "uk": "Ucraniano",
    "ur": "Urdu",
    "vi": "Vietnamita",
}

# Código usado na cascata quando o par direto não existe. O inglês é o idioma
# com mais pares no Argos (47 de saída), então é o melhor intermediário.
PIVO = "en"


class ErroTraducao(Exception):
    """Falha ao traduzir."""


def normalizar(codigo: str) -> str:
    """Aceita 'pt-BR', 'pt_br', 'PT' e devolve o código do Argos."""
    limpo = (codigo or "").strip().lower().replace("_", "-")
    if not limpo:
        return ""
    apelidos = {
        "pt-br": "pb",
        "pt_br": "pb",
        "br": "pb",
        "brasil": "pb",
        "pt-pt": "pt",
        "zh-cn": "zh",
        "zh-hans": "zh",
        "zh-tw": "zt",
        "zh-hant": "zt",
        "auto": "",
    }
    if limpo in apelidos:
        return apelidos[limpo]
    # aceita o prefixo antes do hífen, para casos como "en-us"
    return limpo.split("-")[0]


def nome(codigo: str) -> str:
    """Nome legível; devolve o próprio código se não conhecer."""
    return IDIOMAS.get(normalizar(codigo), codigo or "desconhecido")


def catalogo() -> list[dict[str, str]]:
    """Lista para a tela, em ordem alfabética de nome."""
    return [
        {"codigo": codigo, "nome": rotulo}
        for codigo, rotulo in sorted(IDIOMAS.items(), key=lambda par: par[1])
    ]


def _pedir_traducao(
    textos: list[str],
    origem: str,
    destino: str,
    config: Configuracao,
    transporte: httpx.BaseTransport | None = None,
) -> list[str]:
    """Chama o tradutor da base para um par que já sabemos existir."""
    segmentos = [{"id": str(i), "text": texto} for i, texto in enumerate(textos)]
    corpo: dict[str, Any] = {
        "segments": segmentos,
        "target_lang": destino,
        "source_lang": origem,
        "provider": "argos",
    }
    try:
        with httpx.Client(timeout=config.timeout_s, transport=transporte) as cliente:
            resposta = cliente.post(
                f"{config.base_url}/dub/translate", json=corpo
            )
    except httpx.HTTPError as erro:
        raise ErroTraducao(f"tradutor fora do ar: {erro}") from erro

    if resposta.is_error:
        raise ErroTraducao(_detalhe(resposta))

    try:
        dados = resposta.json()
        traduzidos = dados["translated"]
    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        raise ErroTraducao("a base devolveu uma resposta inválida") from erro

    if not isinstance(traduzidos, list) or len(traduzidos) != len(textos):
        raise ErroTraducao("a base devolveu uma quantidade diferente de segmentos")

    por_id = {str(item.get("id")): item.get("text") for item in traduzidos}
    saida = [por_id.get(str(i), "") for i in range(len(textos))]
    if any(not texto.strip() for texto in saida):
        raise ErroTraducao("a base devolveu texto vazio")
    return saida


def _detalhe(resposta: httpx.Response) -> str:
    """Mensagem da base, com o código quando ela informa."""
    try:
        corpo = resposta.json()
    except (json.JSONDecodeError, ValueError):
        return f"HTTP {resposta.status_code}"
    if isinstance(corpo, dict):
        if corpo.get("code") == "argos_pack_missing":
            pares = corpo.get("pairs") or []
            faltando = ", ".join(
                f"{p.get('source_lang')} -> {p.get('target_lang')}" for p in pares
            )
            return f"falta instalar o idioma no tradutor ({faltando})"
        return str(corpo.get("error") or corpo.get("detail") or corpo)
    return str(corpo)


def _ollama_disponivel(
    endereco: str, transporte: httpx.BaseTransport | None = None
) -> bool:
    try:
        with httpx.Client(timeout=4, transport=transporte) as cliente:
            return cliente.get(f"{endereco.rstrip('/')}/api/tags").is_success
    except httpx.HTTPError:
        return False


# Nomes que o modelo costuma escrever, mapeados para o código do Argos.
# "Portuguese" sozinho vira pb, não pt: o app é brasileiro, e o modelo pequeno
# quase nunca distingue as duas variantes. Quem escreve em português de Portugal
# troca a origem na tela, que é mais honesto do que adivinhar errado o tempo todo.
_NOMES_PARA_CODIGO = {
    "european portuguese": "pt", "português de portugal": "pt",
    "portuguese": "pb", "português": "pb", "portugues": "pb", "brazilian": "pb",
    "english": "en", "inglês": "en", "ingles": "en",
    "spanish": "es", "espanhol": "es", "castilian": "es",
    "french": "fr", "francês": "fr", "frances": "fr",
    "german": "de", "alemão": "de", "alemao": "de",
    "italian": "it", "italiano": "it",
    "japanese": "ja", "japonês": "ja", "japones": "ja",
    "chinese": "zh", "chinês": "zh", "chines": "zh",
    "korean": "ko", "coreano": "ko",
    "russian": "ru", "russo": "ru",
    "arabic": "ar", "árabe": "ar", "arabe": "ar",
    "hindi": "hi", "dutch": "nl", "holandês": "nl",
    "polish": "pl", "polonês": "pl", "turkish": "tr", "turco": "tr",
    "swedish": "sv", "sueco": "sv", "greek": "el", "grego": "el",
    "hebrew": "he", "hebraico": "he", "thai": "th", "tailandês": "th",
    "vietnamese": "vi", "vietnamita": "vi", "indonesian": "id",
    "ukrainian": "uk", "ucraniano": "uk", "romanian": "ro", "romeno": "ro",
    "czech": "cs", "tcheco": "cs", "hungarian": "hu", "húngaro": "hu",
    "finnish": "fi", "finlandês": "fi", "danish": "da", "dinamarquês": "da",
    "norwegian": "nb", "norueguês": "nb", "bulgarian": "bg", "búlgaro": "bg",
    "catalan": "ca", "catalão": "ca",
    "slovak": "sk", "eslovaco": "sk", "slovenian": "sl", "esloveno": "sl",
    "estonian": "et", "estônio": "et", "latvian": "lv", "letão": "lv",
    "lithuanian": "lt", "lituano": "lt", "persian": "fa", "persa": "fa",
    "urdu": "ur", "bengali": "bn", "malay": "ms", "malaio": "ms",
    "tagalog": "tl", "swahili": "sw", "suaíli": "sw", "irish": "ga",
    "galician": "gl", "galego": "gl", "basque": "eu", "basco": "eu",
    "esperanto": "eo", "albanian": "sq", "albanês": "sq", "azerbaijani": "az",
    "kyrgyz": "ky", "quirguiz": "ky",
}


def detectar_idioma(
    texto: str,
    config: Configuracao,
    endereco_ollama: str | None = None,
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Idioma provável do texto, por IA local. Best-effort, nunca inventa.

    O Argos não detecta idioma e a base também não expõe detecção de texto. Então
    perguntamos ao Ollama local. Quando ele responde algo que não dá para mapear,
    devolvemos `detectado: False` e a tela pede a escolha na mão, em vez de
    chutar.
    """
    limpo = texto.strip()
    if not limpo:
        return {"detectado": False, "motivo": "texto vazio"}

    endereco = endereco_ollama or "http://127.0.0.1:11434"
    if not _ollama_disponivel(endereco, transporte):
        return {
            "detectado": False,
            "motivo": f"nenhum modelo local respondeu em {endereco}",
        }

    instrucao = (
        "Identify the language of the text below. Answer with ONLY the ISO 639-1 "
        "two-letter code. If it is Brazilian Portuguese, answer pb. "
        "Answer with nothing else."
    )
    try:
        with httpx.Client(timeout=120, transport=transporte) as cliente:
            resposta = cliente.post(
                f"{endereco.rstrip('/')}/api/chat",
                json={
                    "model": _modelo_ollama(cliente, endereco),
                    "messages": [
                        {"role": "system", "content": instrucao},
                        {"role": "user", "content": f"Text: {limpo[:1200]}"},
                    ],
                    "stream": False,
                    "options": {"temperature": 0, "num_predict": 64},
                },
            )
        mensagem = resposta.json().get("message") or {}
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError) as erro:
        return {"detectado": False, "motivo": f"modelo local falhou: {erro}"}

    # O campo `content` costuma vir vazio quando o modelo raciocina antes: o
    # modelo desta máquina escreve "The text is in Portuguese" em `thinking` e
    # deixa `content` em branco. Ler só o content dava "detecção falhou" sempre.
    candidatos = [str(mensagem.get("content") or ""), str(mensagem.get("thinking") or "")]
    for bruto in candidatos:
        codigo = _extrair_codigo(bruto)
        if codigo:
            return {
                "detectado": True,
                "codigo": codigo,
                "nome": nome(codigo),
                "bruto": bruto.strip()[:40],
            }
    return {
        "detectado": False,
        "motivo": "o modelo não disse o idioma em termos reconhecíveis",
        "bruto": " | ".join(c.strip()[:30] for c in candidatos if c.strip())[:80],
    }


def _modelo_ollama(cliente: httpx.Client, endereco: str) -> str:
    """Primeiro modelo disponível. Preferimos um pequeno, mas qualquer serve."""
    resposta = cliente.get(f"{endereco.rstrip('/')}/api/tags")
    modelos = [m["name"] for m in resposta.json().get("models", []) if m.get("name")]
    if not modelos:
        raise ErroTraducao("nenhum modelo instalado no Ollama")
    return modelos[0]


def _extrair_codigo(bruto: str) -> str | None:
    """Extrai o código do idioma da resposta do modelo.

    Vale a menção que aparece **primeiro no texto**, não a primeira que casa no
    dicionário. Motivo medido: quando o modelo raciocina, ele escreve
    "The text is in Portuguese. ... Now I need to determine if it's Brazilian or
    European Portuguese" — a conclusão inicial é a resposta, e o resto é
    deliberação. Pegando por ordem de dicionário, "European Portuguese" ganhava e
    o idioma saía como Portugal.
    """
    baixo = bruto.lower().strip()

    # 1) a resposta é só o código? caso ideal, e o mais comum
    so_codigo = re.sub(r"[^a-z]", "", baixo)
    if so_codigo in IDIOMAS:
        return so_codigo

    # 2) nomes de idioma primeiro, pelo mais cedo no texto. Nomes ganham dos
    #    códigos de duas letras porque "It is Spanish" tem "It" na posição 0, e
    #    por posição pura o resultado sairia italiano.
    nomes: list[tuple[int, str]] = []
    for nome_lingua, codigo in _NOMES_PARA_CODIGO.items():
        posicao = baixo.find(nome_lingua)
        if posicao >= 0:
            nomes.append((posicao, codigo))
    if nomes:
        nomes.sort()
        return nomes[0][1]

    # 3) nenhum nome: código solto, como "en." ou "Language: ja"
    codigos = [
        achado.group() for achado in re.finditer(r"\b[a-z]{2}\b", baixo)
        if achado.group() in IDIOMAS
    ]
    return codigos[0] if codigos else None


def traduzir(
    texto: str,
    origem: str,
    destino: str,
    config: Configuracao,
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Traduz um texto, com cascata pelo inglês quando o par direto não existe.

    Devolve o texto traduzido e por qual caminho passou, porque esconder a
    cascata seria esconder uma perda de qualidade de quem usa.
    """
    if not texto.strip():
        raise ErroTraducao("escreva algo para traduzir")

    alvo = normalizar(destino)
    fonte = normalizar(origem)
    if not alvo:
        raise ErroTraducao("escolha o idioma de destino")
    if alvo not in IDIOMAS:
        raise ErroTraducao(
            f"idioma de destino desconhecido: {destino}. "
            f"Disponíveis: {len(IDIOMAS)} idiomas."
        )

    # Sem origem informada: assume o inglês, que é o pivo, e avisa na resposta.
    if not fonte:
        fonte = PIVO
    if fonte not in IDIOMAS:
        raise ErroTraducao(f"idioma de origem desconhecido: {origem}")

    if fonte == alvo:
        return {
            "texto": texto,
            "origem": fonte,
            "destino": alvo,
            "caminho": [],
            "saltos": 0,
            "observacao": "origem e destino iguais, texto devolvido sem alteração",
        }

    # 1) tenta o par direto
    try:
        traduzido = _pedir_traducao([texto], fonte, alvo, config, transporte)[0]
        return {
            "texto": traduzido,
            "origem": fonte,
            "destino": alvo,
            "caminho": [fonte, alvo],
            "saltos": 1,
            "observacao": None,
        }
    except ErroTraducao as direto:
        if fonte == PIVO or alvo == PIVO:
            raise
        erro_direto = direto

    # 2) cascata pelo inglês
    try:
        intermediario = _pedir_traducao([texto], fonte, PIVO, config, transporte)[0]
        traduzido = _pedir_traducao([intermediario], PIVO, alvo, config, transporte)[0]
    except ErroTraducao as cascata:
        raise ErroTraducao(
            f"não deu para traduzir de {nome(fonte)} para {nome(alvo)}. "
            f"Direto: {erro_direto}. Com escala em inglês: {cascata}. "
            "Instale o par que falta no catálogo de idiomas."
        ) from cascata

    return {
        "texto": traduzido,
        "origem": fonte,
        "destino": alvo,
        "caminho": [fonte, PIVO, alvo],
        "saltos": 2,
        "intermediario": intermediario,
        "observacao": (
            f"não existe par direto de {nome(fonte)} para {nome(alvo)}; "
            f"o texto passou pelo inglês, o que pode reduzir a qualidade"
        ),
    }


def traduzir_lote(
    textos: list[str],
    origem: str,
    destino: str,
    config: Configuracao,
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Traduz vários trechos de uma vez, para dublagem de fala longa."""
    if not textos:
        raise ErroTraducao("nenhum trecho para traduzir")
    alvo = normalizar(destino)
    fonte = normalizar(origem) or PIVO
    if fonte == alvo:
        return {"textos": textos, "caminho": []}

    try:
        prontos = _pedir_traducao(textos, fonte, alvo, config, transporte)
        caminho = [fonte, alvo]
    except ErroTraducao:
        if fonte == PIVO or alvo == PIVO:
            raise
        meio = _pedir_traducao(textos, fonte, PIVO, config, transporte)
        prontos = _pedir_traducao(meio, PIVO, alvo, config, transporte)
        caminho = [fonte, PIVO, alvo]

    return {"textos": prontos, "caminho": caminho, "saltos": len(caminho) - 1}
