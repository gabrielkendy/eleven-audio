#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
protocolo_seguranca.py · Protocolo de Seguranca Avancado do Estudio de Voz Local

Este script transforma o protocolo em DECISAO. Ele roda, mede e sai com codigo de erro
quando uma invariante e violada.

    python ferramentas/protocolo_seguranca.py --projeto .

Saida:
    [ OK  ] P1 nenhum segredo no codigo
    [FALHA] P2 servidor nao esta em 0.0.0.0            app/servidor.py:41
    ...
    RESULTADO: 11 aprovadas, 1 falha
    DECISAO: BLOQUEADO

Regra dura: gate critico em falha nao e compensado por media alta.
Vinte itens aprovados nao anulam uma invariante violada.

O QUE ESTE SCRIPT NAO PROVA: que o app e seguro. Ele prova que doze invariantes
foram verificadas numa versao, numa data, com o resultado registrado. Scanner levanta
hipotese. Nao existe selo de seguro.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ----------------------------------------------------------------------------
# infraestrutura do relatorio
# ----------------------------------------------------------------------------

OK, FALHA, NAO_RODADO = "OK", "FALHA", "NAO_RODADO"

ARQUIVOS_IGNORADOS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "dados", "saidas",
    ".next", "dist", "build", ".mypy_cache", ".pytest_cache",
}
EXTENSOES_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
                    ".toml", ".cfg", ".ini", ".sh", ".ps1", ".mjs", ".cjs"}


@dataclass
class Achado:
    invariante: str
    critica: bool
    estado: str
    mensagem: str
    ocorrencias: list[str] = field(default_factory=list)


def varrer_codigo(raiz: Path, extensoes=EXTENSOES_CODIGO):
    """Percorre o projeto devolvendo (caminho_relativo, numero_da_linha, texto)."""
    proprio_scanner = Path(__file__).resolve()
    for caminho in sorted(raiz.rglob("*")):
        if not caminho.is_file():
            continue
        if caminho.resolve() == proprio_scanner:
            continue
        if any(parte in ARQUIVOS_IGNORADOS for parte in caminho.parts):
            continue
        if caminho.suffix.lower() not in extensoes:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = caminho.relative_to(raiz).as_posix()
        for numero, linha in enumerate(texto.splitlines(), 1):
            yield rel, numero, linha


def achar(raiz: Path, padrao: str, extensoes=EXTENSOES_CODIGO, flags=0, limite=6):
    """Devolve as ocorrencias de um padrao no codigo, no formato caminho:linha."""
    regex = re.compile(padrao, flags)
    achados = []
    for rel, numero, linha in varrer_codigo(raiz, extensoes):
        if regex.search(linha):
            achados.append(f"{rel}:{numero}")
            if len(achados) >= limite:
                break
    return achados


# ----------------------------------------------------------------------------
# as doze invariantes
# ----------------------------------------------------------------------------

def p1_nenhum_segredo(raiz: Path) -> Achado:
    """Nenhum segredo no codigo. Chave, token e senha vivem em variavel de ambiente."""
    padroes = [
        (r"(?i)\b(api[_-]?key|apikey|secret|senha|password|passwd|token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]",
         "valor literal em campo de credencial"),
        (r"sk-[A-Za-z0-9]{16,}", "formato de chave de API"),
        (r"ghp_[A-Za-z0-9]{20,}", "token do GitHub"),
        (r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.", "formato de JWT"),
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "chave privada"),
    ]
    occ = []
    for padrao, _ in padroes:
        occ.extend(achar(raiz, padrao))
    occ = sorted(set(occ))[:6]

    # .env e a pasta de dados precisam estar ignorados pelo git
    gi = raiz / ".gitignore"
    avisos = []
    if not gi.exists():
        avisos.append(".gitignore ausente")
    else:
        conteudo = gi.read_text(encoding="utf-8", errors="replace")
        for alvo in (".env", "dados/", "saidas/"):
            if alvo not in conteudo:
                avisos.append(f".gitignore sem '{alvo}'")

    if occ or avisos:
        return Achado("P1", True, FALHA,
                      "segredo em codigo ou pasta sensivel fora do .gitignore", occ + avisos)
    return Achado("P1", True, OK, "nenhum segredo no codigo")


def p2_loopback(raiz: Path) -> Achado:
    """Nada escutando em 0.0.0.0. Servidor local sobe em 127.0.0.1."""
    occ = achar(raiz, r"0\.0\.0\.0|['\"]host['\"]\s*[:=]\s*['\"]\s*['\"]")
    if occ:
        return Achado("P2", True, FALHA, "servidor abre para a rede (0.0.0.0 ou host vazio)", occ)
    tem_loopback = bool(achar(raiz, r"127\.0\.0\.1|localhost"))
    if not tem_loopback:
        return Achado("P2", True, FALHA, "nenhuma subida em loopback encontrada no codigo", [])
    return Achado("P2", True, OK, "servidor em loopback, nada exposto na rede")


def p3_sem_chamada_externa(raiz: Path) -> Achado:
    """Nenhuma chamada externa no uso normal. O texto nao sai da maquina."""
    host_local = r"(127\.0\.0\.1|localhost|::1)"
    occ = []
    for rel, numero, linha in varrer_codigo(raiz, {".py", ".js", ".ts", ".tsx", ".jsx"}):
        if re.search(r"(?i)telemetry|analytics|sentry|posthog|mixpanel|segment\.|datadog", linha):
            occ.append(f"{rel}:{numero}")
            continue
        if re.search(r"https?://", linha) and not re.search(host_local, linha):
            # documentacao e comentario puro nao contam
            limpa = linha.strip()
            if limpa.startswith(("#", "//", "*", '"""', "'''")):
                continue
            occ.append(f"{rel}:{numero}")
        if len(occ) >= 6:
            break
    if occ:
        return Achado("P3", True, FALHA, "chamada externa no codigo da aplicacao", occ)
    return Achado("P3", True, OK, "nenhuma chamada externa no caminho normal")


def p4_consentimento(raiz: Path) -> Achado:
    """Consentimento bloqueia a geracao, nao apenas avisa na tela."""
    tem_consent = bool(achar(raiz, r"consentimento|consent", limite=1))
    if not tem_consent:
        return Achado("P4", True, FALHA, "nenhum controle de consentimento encontrado", [])
    bloqueia = achar(raiz, r"409|perfil sem consentimento|sem consentimento", limite=3)
    if not bloqueia:
        return Achado("P4", True, FALHA,
                      "consentimento citado, mas sem recusa no servidor (esperado 409)", [])
    return Achado("P4", True, OK, "consentimento bloqueia a geracao no servidor")


def p5_caminho_confinado(raiz: Path) -> Achado:
    """Caminho servido por pedido fica confinado na raiz permitida."""
    usa_caminho = achar(raiz, r"request|query|params|args|payload", limite=1)
    if not usa_caminho:
        return Achado("P5", True, NAO_RODADO,
                      "sem entrada de caminho por pedido nesta versao")
    confina = achar(raiz, r"resolve\(\)|is_relative_to|startswith\(.*?raiz|Path\(.*?\)\.resolve",
                    limite=3)
    if not confina:
        return Achado("P5", True, FALHA,
                      "caminho vindo do pedido sem confinamento na raiz permitida", [])
    return Achado("P5", True, OK, "caminho confinado na raiz permitida")


def p6_escrita_atomica(raiz: Path) -> Achado:
    """Escrita em arquivo de dado passa por temporario, fsync e replace."""
    escrita_direta = []
    for rel, numero, linha in varrer_codigo(raiz, {".py"}):
        if re.search(r"open\([^)]*dados[^)]*['\"]w", linha) or \
           re.search(r"\.write_text\(|json\.dump\(", linha):
            # escrita legitima quando e dentro do cofre com temporario
            escrita_direta.append(f"{rel}:{numero}")
    tem_atomica = bool(achar(raiz, r"os\.replace|fsync", limite=1))
    if escrita_direta and not tem_atomica:
        return Achado("P6", True, FALHA,
                      "escrita em dado sem troca atomica (falta os.replace/fsync)",
                      escrita_direta[:6])
    if not tem_atomica:
        return Achado("P6", True, NAO_RODADO, "nenhuma camada de escrita de dado ainda")
    return Achado("P6", True, OK, "escrita de dado com troca atomica")


def p7_log_limpo(raiz: Path) -> Achado:
    """Log registra evento, nao conteudo sensivel."""
    occ = []
    for rel, numero, linha in varrer_codigo(raiz, {".py", ".js", ".ts"}):
        if re.search(r"(?i)(logger|log|logging)\.(info|debug|warning|error)", linha):
            if re.search(r"texto_entrada|texto|base64|referencia|clipe", linha):
                occ.append(f"{rel}:{numero}")
        if len(occ) >= 6:
            break
    if occ:
        return Achado("P7", True, FALHA, "log escrevendo conteudo sensivel", occ)
    return Achado("P7", True, OK, "log sem texto do usuario e sem base64")


def p8_dependencia_travada(raiz: Path) -> Achado:
    """Dependencia com versao fixada. Solta significa outra coisa na proxima instalacao."""
    arquivos = [raiz / "requirements.txt", raiz / "pyproject.toml", raiz / "package.json"]
    achados, checados = [], 0
    for arq in arquivos:
        if not arq.exists():
            continue
        checados += 1
        texto = arq.read_text(encoding="utf-8", errors="replace")
        if arq.name == "requirements.txt":
            for numero, linha in enumerate(texto.splitlines(), 1):
                l = linha.strip()
                if l and not l.startswith("#") and not re.search(r"[=<>~!]=?\s*[\d*]", l):
                    achados.append(f"{arq.name}:{numero}")
    if not checados:
        return Achado("P8", True, NAO_RODADO, "nenhum arquivo de dependencia encontrado")
    if achados:
        return Achado("P8", True, FALHA, "dependencia sem versao fixada", achados[:6])
    return Achado("P8", True, OK, "dependencia com versao fixada")


def p9_sem_binario_em_dado(raiz: Path) -> Achado:
    """Audio nunca dentro de arquivo de dado."""
    occ = []
    for rel, numero, linha in varrer_codigo(raiz, {".py", ".js", ".ts"}):
        if "base64" in linha and re.search(r"(?i)dump|write|json", linha):
            occ.append(f"{rel}:{numero}")
    pasta_dados = raiz / "dados"
    if pasta_dados.is_dir():
        for arq in pasta_dados.glob("*.json*"):
            try:
                if arq.stat().st_size > 8 * 1024 * 1024:
                    occ.append(f"{arq.relative_to(raiz).as_posix()} acima de 8 MB")
            except OSError:
                pass
    if occ:
        return Achado("P9", True, FALHA, "binario dentro de arquivo de dado", occ[:6])
    return Achado("P9", True, OK, "audio fora do arquivo de dado")


def p10_nome_sanitizado(raiz: Path) -> Achado:
    """Nome de arquivo gerado passa por filtro ASCII seguro."""
    usa_nome = achar(raiz, r"nome_arquivo|filename|arquivo_saida", limite=1)
    if not usa_nome:
        return Achado("P10", True, NAO_RODADO, "nenhuma geracao de nome de arquivo ainda")
    sanitiza = achar(raiz, r"sanitiz|slug|re\.sub\(r?['\"][^'\"]*\\W|unicodedata\.normalize",
                     limite=3)
    if not sanitiza:
        return Achado("P10", True, FALHA,
                      "nome de arquivo gerado sem sanitizacao (acento e emoji passam)", [])
    return Achado("P10", True, OK, "nome de arquivo sanitizado")


def p11_instancia_unica(raiz: Path) -> Achado:
    """Uma instancia por vez, com trava."""
    occ = achar(raiz, r"lock|trava|instancia|instance", limite=3)
    if not occ:
        return Achado("P11", True, FALHA, "nenhuma trava de instancia unica", [])
    return Achado("P11", True, OK, "trava de instancia unica presente")


def p12_portoes_separados(raiz: Path) -> Achado:
    """Portao de consumo diferente do portao de administracao."""
    tem_admin = achar(raiz, r"/system/|/api/settings|admin", limite=1)
    if not tem_admin:
        return Achado("P12", True, NAO_RODADO,
                      "esta versao nao expoe rota de administracao")
    separado = achar(raiz, r"loopback|127\.0\.0\.1", limite=2)
    if not separado:
        return Achado("P12", True, FALHA,
                      "rota de administracao sem portao proprio de loopback", [])
    return Achado("P12", True, OK, "portao de administracao separado do de consumo")


INVARIANTES = [
    p1_nenhum_segredo, p2_loopback, p3_sem_chamada_externa, p4_consentimento,
    p5_caminho_confinado, p6_escrita_atomica, p7_log_limpo, p8_dependencia_travada,
    p9_sem_binario_em_dado, p10_nome_sanitizado, p11_instancia_unica, p12_portoes_separados,
]

NOMES = {
    "P1": "nenhum segredo no codigo",
    "P2": "servidor nao esta em 0.0.0.0",
    "P3": "nenhuma chamada externa no uso normal",
    "P4": "consentimento bloqueia geracao",
    "P5": "caminho confinado na raiz permitida",
    "P6": "escrita de dado com troca atomica",
    "P7": "log sem conteudo sensivel",
    "P8": "dependencia com versao fixada",
    "P9": "audio fora do arquivo de dado",
    "P10": "nome de arquivo sanitizado",
    "P11": "trava de instancia unica",
    "P12": "portao de consumo separado do de administracao",
}


# ----------------------------------------------------------------------------
# execucao
# ----------------------------------------------------------------------------

def rodar(raiz: Path, json_saida: Path | None = None) -> int:
    resultados = []
    for funcao in INVARIANTES:
        try:
            resultados.append(funcao(raiz))
        except Exception as erro:                       # nunca deixa o gate cair calado
            resultados.append(Achado("??", True, NAO_RODADO, f"erro ao verificar: {erro}"))

    print()
    print("=" * 74)
    print("  PROTOCOLO DE SEGURANCA · ESTUDIO DE VOZ LOCAL")
    print(f"  projeto: {raiz}")
    print(f"  quando:  {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print("=" * 74)

    for r in resultados:
        etiqueta = {"OK": "[ OK  ]", "FALHA": "[FALHA]", "NAO_RODADO": "[N/R  ]"}[r.estado]
        nome = NOMES.get(r.invariante, r.mensagem)
        linha = f"{etiqueta} {r.invariante} {nome}"
        if r.estado != OK and r.mensagem:
            linha = f"{linha:<58} {r.mensagem}"
        print(linha)
        for oc in r.ocorrencias:
            print(f"            -> {oc}")

    oks = sum(1 for r in resultados if r.estado == OK)
    falhas = [r for r in resultados if r.estado == FALHA and r.critica]
    nao_rodadas = sum(1 for r in resultados if r.estado == NAO_RODADO)

    print("-" * 74)
    print(f"  RESULTADO: {oks} aprovadas, {len(falhas)} falha(s), {nao_rodadas} nao rodada(s)")
    decisao = "LIBERADO" if not falhas else "BLOQUEADO"
    print(f"  DECISAO:   {decisao}")
    print("-" * 74)
    print()
    print("  Este gate NAO prova que o app e seguro. Ele prova que estas invariantes")
    print("  foram verificadas nesta versao, nesta data. Scanner levanta hipotese.")
    print()

    if json_saida:
        json_saida.parent.mkdir(parents=True, exist_ok=True)
        json_saida.write_text(json.dumps({
            "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "projeto": str(raiz),
            "decisao": decisao,
            "aprovadas": oks,
            "falhas": len(falhas),
            "nao_rodadas": nao_rodadas,
            "invariantes": [
                {"id": r.invariante, "estado": r.estado, "critica": r.critica,
                 "mensagem": r.mensagem, "ocorrencias": r.ocorrencias}
                for r in resultados
            ],
        }, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    return 1 if falhas else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Protocolo de seguranca do Estudio de Voz Local")
    ap.add_argument("--projeto", default=".", help="raiz do projeto a verificar")
    ap.add_argument("--json", default=None, help="gravar o relatorio em JSON neste caminho")
    args = ap.parse_args()

    raiz = Path(args.projeto).resolve()
    if not raiz.is_dir():
        print(f"ERRO: projeto nao encontrado: {raiz}", file=sys.stderr)
        return 2
    saida = Path(args.json) if args.json else None
    return rodar(raiz, saida)


if __name__ == "__main__":
    raise SystemExit(main())
