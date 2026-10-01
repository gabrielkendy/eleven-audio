"""Cofre local: SQLite com as SETE tabelas do PRD. Sem ORM, sem servidor, sem conta.

Contrato compartilhado: os agentes das fatias NAO reescrevem este arquivo, so chamam.
Banco em dados/estudio.db. Audio NUNCA entra no banco.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ESQUEMA = """
CREATE TABLE IF NOT EXISTS perfil_voz (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    origem TEXT NOT NULL CHECK (origem IN ('clonado', 'desenhado')),
    id_na_base TEXT NOT NULL,
    arquivo_referencia TEXT,
    transcricao_referencia TEXT,
    descricao_desenho TEXT,
    idioma TEXT NOT NULL DEFAULT 'pt',
    criado_em TEXT NOT NULL,
    observacao TEXT
);

CREATE TABLE IF NOT EXISTS consentimento (
    id TEXT PRIMARY KEY,
    perfil_id TEXT NOT NULL UNIQUE REFERENCES perfil_voz (id) ON DELETE CASCADE,
    texto_aceito TEXT NOT NULL,
    aceito_em TEXT NOT NULL,
    origem_voz TEXT NOT NULL CHECK (origem_voz IN ('propria', 'autorizada'))
);

CREATE TABLE IF NOT EXISTS geracao (
    id TEXT PRIMARY KEY,
    perfil_id TEXT REFERENCES perfil_voz (id) ON DELETE SET NULL,
    motor TEXT NOT NULL,
    texto_entrada TEXT NOT NULL,
    arquivo_saida TEXT NOT NULL,
    duracao_audio_s REAL NOT NULL,
    duracao_geracao_s REAL NOT NULL,
    dispositivo TEXT NOT NULL,
    tamanho_bytes INTEGER NOT NULL,
    criado_em TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'erro')),
    erro TEXT,
    config_json TEXT
);

CREATE TABLE IF NOT EXISTS transcricao (
    id TEXT PRIMARY KEY,
    arquivo_entrada TEXT NOT NULL,
    motor TEXT NOT NULL,
    texto_saida TEXT NOT NULL,
    idioma_detectado TEXT,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vinculo_agente (
    id TEXT PRIMARY KEY,
    cliente_id TEXT NOT NULL UNIQUE,
    perfil_id TEXT NOT NULL REFERENCES perfil_voz (id) ON DELETE CASCADE,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS configuracao (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evento (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    detalhe TEXT NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geracao_criado_em ON geracao (criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_geracao_perfil ON geracao (perfil_id);
CREATE INDEX IF NOT EXISTS idx_evento_criado_em ON evento (criado_em DESC);
"""


def agora() -> str:
    """Data e hora local com fuso, formato ISO."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def novo_id(prefixo: str = "") -> str:
    return f"{prefixo}{uuid.uuid4().hex[:12]}"


class Cofre:
    """Acesso ao banco local. Toda gravacao passa por aqui."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._conexao = sqlite3.connect(str(self.caminho))
        self._conexao.row_factory = sqlite3.Row
        self._conexao.execute("PRAGMA journal_mode=WAL")
        self._conexao.execute("PRAGMA foreign_keys=ON")
        self._conexao.executescript(ESQUEMA)
        self._migrar()
        self._conexao.commit()

    def _migrar(self) -> None:
        """Acrescenta colunas que nasceram depois, sem perder banco existente.

        O histórico do ElevenLabs mostra as configurações de cada geração; para
        isso o banco precisa guardá-las. Bancos criados antes disso não têm a
        coluna, então ela entra por ALTER TABLE na abertura.
        """
        colunas = {linha["name"] for linha in self._conexao.execute("PRAGMA table_info(geracao)")}
        if "config_json" not in colunas:
            self._conexao.execute("ALTER TABLE geracao ADD COLUMN config_json TEXT")

    def fechar(self) -> None:
        self._conexao.close()

    def _linhas(self, sql: str, parametros: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(linha) for linha in self._conexao.execute(sql, parametros).fetchall()]

    def _executar(self, sql: str, parametros: tuple[Any, ...] = ()) -> None:
        self._conexao.execute(sql, parametros)
        self._conexao.commit()

    # ---------------------------------------------------------------- evento
    def registrar_evento(self, tipo: str, detalhe: str) -> str:
        identificador = novo_id("ev-")
        self._executar(
            "INSERT INTO evento (id, tipo, detalhe, criado_em) VALUES (?, ?, ?, ?)",
            (identificador, tipo, detalhe, agora()),
        )
        return identificador

    def listar_eventos(self, limite: int = 50) -> list[dict[str, Any]]:
        return self._linhas("SELECT * FROM evento ORDER BY criado_em DESC LIMIT ?", (limite,))

    # ------------------------------------------------------------ perfil_voz
    def salvar_perfil(
        self,
        *,
        nome: str,
        origem: str,
        id_na_base: str,
        arquivo_referencia: str | None = None,
        transcricao_referencia: str | None = None,
        descricao_desenho: str | None = None,
        idioma: str = "pt",
        observacao: str | None = None,
        perfil_id: str | None = None,
    ) -> str:
        if origem not in {"clonado", "desenhado"}:
            raise ValueError("origem deve ser clonado ou desenhado")
        identificador = perfil_id or novo_id("vz-")
        self._executar(
            """
            INSERT INTO perfil_voz (
                id, nome, origem, id_na_base, arquivo_referencia, transcricao_referencia,
                descricao_desenho, idioma, criado_em, observacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identificador,
                nome,
                origem,
                id_na_base,
                arquivo_referencia,
                transcricao_referencia,
                descricao_desenho,
                idioma,
                agora(),
                observacao,
            ),
        )
        self.registrar_evento("clonar" if origem == "clonado" else "desenhar", f"perfil {identificador} ({nome})")
        return identificador

    def atualizar_perfil(self, perfil_id: str, **campos: Any) -> None:
        permitidos = {
            "nome",
            "id_na_base",
            "arquivo_referencia",
            "transcricao_referencia",
            "descricao_desenho",
            "idioma",
            "observacao",
        }
        usados = {chave: valor for chave, valor in campos.items() if chave in permitidos}
        if not usados:
            return
        trechos = ", ".join(f"{chave} = ?" for chave in usados)
        self._executar(
            f"UPDATE perfil_voz SET {trechos} WHERE id = ?",
            (*usados.values(), perfil_id),
        )

    def perfil(self, perfil_id: str) -> dict[str, Any] | None:
        linhas = self._linhas("SELECT * FROM perfil_voz WHERE id = ?", (perfil_id,))
        return linhas[0] if linhas else None

    def listar_perfis(self) -> list[dict[str, Any]]:
        return self._linhas(
            """
            SELECT p.*, c.aceito_em AS consentimento_em, c.origem_voz AS consentimento_origem,
                   (SELECT COUNT(*) FROM geracao g WHERE g.perfil_id = p.id) AS total_geracoes
            FROM perfil_voz p
            LEFT JOIN consentimento c ON c.perfil_id = p.id
            ORDER BY p.criado_em DESC
            """
        )

    def apagar_perfil(self, perfil_id: str) -> None:
        self._executar("DELETE FROM perfil_voz WHERE id = ?", (perfil_id,))
        self.registrar_evento("erro", f"perfil {perfil_id} apagado")

    # ---------------------------------------------------------- consentimento
    def salvar_consentimento(
        self,
        *,
        perfil_id: str,
        texto_aceito: str,
        origem_voz: str,
    ) -> str:
        if origem_voz not in {"propria", "autorizada"}:
            raise ValueError("origem_voz deve ser propria ou autorizada")
        identificador = novo_id("cs-")
        self._executar(
            """
            INSERT INTO consentimento (id, perfil_id, texto_aceito, aceito_em, origem_voz)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (perfil_id) DO UPDATE SET
                texto_aceito = excluded.texto_aceito,
                aceito_em = excluded.aceito_em,
                origem_voz = excluded.origem_voz
            """,
            (identificador, perfil_id, texto_aceito, agora(), origem_voz),
        )
        return identificador

    def consentimento(self, perfil_id: str) -> dict[str, Any] | None:
        linhas = self._linhas("SELECT * FROM consentimento WHERE perfil_id = ?", (perfil_id,))
        return linhas[0] if linhas else None

    def tem_consentimento(self, perfil_id: str) -> bool:
        return self.consentimento(perfil_id) is not None

    def salvar_perfil_com_consentimento(
        self,
        *,
        nome: str,
        id_na_base: str,
        arquivo_referencia: str,
        transcricao_referencia: str,
        idioma: str,
        texto_aceito: str,
        origem_voz: str,
    ) -> str:
        """Cria perfil clonado e consentimento numa única transação SQLite."""
        if origem_voz not in {"propria", "autorizada"}:
            raise ValueError("origem_voz deve ser propria ou autorizada")
        perfil_id = novo_id("vz-")
        consentimento_id = novo_id("cs-")
        criado_em = agora()
        with self._conexao:
            self._conexao.execute(
                """
                INSERT INTO perfil_voz (
                    id, nome, origem, id_na_base, arquivo_referencia,
                    transcricao_referencia, descricao_desenho, idioma,
                    criado_em, observacao
                ) VALUES (?, ?, 'clonado', ?, ?, ?, NULL, ?, ?, NULL)
                """,
                (
                    perfil_id,
                    nome,
                    id_na_base,
                    arquivo_referencia,
                    transcricao_referencia,
                    idioma,
                    criado_em,
                ),
            )
            self._conexao.execute(
                """
                INSERT INTO consentimento (
                    id, perfil_id, texto_aceito, aceito_em, origem_voz
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    consentimento_id,
                    perfil_id,
                    texto_aceito,
                    criado_em,
                    origem_voz,
                ),
            )
            self._conexao.execute(
                "INSERT INTO evento (id, tipo, detalhe, criado_em) VALUES (?, ?, ?, ?)",
                (novo_id("ev-"), "clonar", f"perfil {perfil_id} ({nome})", criado_em),
            )
        return perfil_id

    # --------------------------------------------------------------- geracao
    def registrar_geracao(
        self,
        *,
        motor: str,
        texto_entrada: str,
        arquivo_saida: str,
        duracao_audio_s: float,
        duracao_geracao_s: float,
        dispositivo: str,
        tamanho_bytes: int,
        perfil_id: str | None = None,
        status: str = "ok",
        erro: str | None = None,
        geracao_id: str | None = None,
        configuracao: dict[str, Any] | None = None,
    ) -> str:
        identificador = geracao_id or novo_id("g-")
        self._executar(
            """
            INSERT INTO geracao (
                id, perfil_id, motor, texto_entrada, arquivo_saida, duracao_audio_s,
                duracao_geracao_s, dispositivo, tamanho_bytes, criado_em, status, erro, config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identificador,
                perfil_id,
                motor,
                texto_entrada,
                arquivo_saida,
                float(duracao_audio_s),
                float(duracao_geracao_s),
                dispositivo,
                int(tamanho_bytes),
                agora(),
                status,
                erro,
                json.dumps(configuracao, ensure_ascii=False) if configuracao else None,
            ),
        )
        self.registrar_evento("gerar" if status == "ok" else "erro", f"geracao {identificador} com {motor}")
        return identificador

    def configuracao_da_geracao(self, registro: dict[str, Any]) -> dict[str, Any] | None:
        """Le a configuracao gravada na geracao (coluna TEXT, JSON)."""
        bruto = registro.get("config_json")
        if not bruto:
            return None
        try:
            dado = json.loads(bruto)
        except (TypeError, json.JSONDecodeError):
            return None
        return dado if isinstance(dado, dict) else None

    def geracao(self, geracao_id: str) -> dict[str, Any] | None:
        linhas = self._linhas("SELECT * FROM geracao WHERE id = ?", (geracao_id,))
        return linhas[0] if linhas else None

    def listar_geracoes(
        self,
        *,
        limite: int = 100,
        perfil_id: str | None = None,
        motor: str | None = None,
    ) -> list[dict[str, Any]]:
        condicoes: list[str] = []
        parametros: list[Any] = []
        if perfil_id:
            condicoes.append("perfil_id = ?")
            parametros.append(perfil_id)
        if motor:
            condicoes.append("motor = ?")
            parametros.append(motor)
        onde = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
        parametros.append(limite)
        # `criado_em` tem resolucao de segundo: duas geracoes no mesmo segundo
        # empatam e o SQLite devolve na ordem de insercao, o que fazia o
        # historico mostrar a mais antiga primeiro. O rowid desempata.
        return self._linhas(
            f"SELECT * FROM geracao {onde} ORDER BY criado_em DESC, rowid DESC LIMIT ?",
            tuple(parametros),
        )

    def ultima_geracao(self) -> dict[str, Any] | None:
        linhas = self._linhas("SELECT * FROM geracao ORDER BY criado_em DESC, rowid DESC LIMIT 1")
        return linhas[0] if linhas else None

    # ------------------------------------------------------------ transcricao
    def registrar_transcricao(
        self,
        *,
        arquivo_entrada: str,
        motor: str,
        texto_saida: str,
        idioma_detectado: str | None = None,
    ) -> str:
        identificador = novo_id("tr-")
        self._executar(
            """
            INSERT INTO transcricao (id, arquivo_entrada, motor, texto_saida, idioma_detectado, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (identificador, arquivo_entrada, motor, texto_saida, idioma_detectado, agora()),
        )
        return identificador

    def listar_transcricoes(self, limite: int = 50) -> list[dict[str, Any]]:
        return self._linhas("SELECT * FROM transcricao ORDER BY criado_em DESC LIMIT ?", (limite,))

    # --------------------------------------------------------- vinculo_agente
    def salvar_vinculo(self, *, cliente_id: str, perfil_id: str) -> str:
        identificador = novo_id("vg-")
        self._executar(
            """
            INSERT INTO vinculo_agente (id, cliente_id, perfil_id, criado_em)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (cliente_id) DO UPDATE SET
                perfil_id = excluded.perfil_id,
                criado_em = excluded.criado_em
            """,
            (identificador, cliente_id, perfil_id, agora()),
        )
        return identificador

    def remover_vinculo(self, cliente_id: str) -> None:
        self._executar("DELETE FROM vinculo_agente WHERE cliente_id = ?", (cliente_id,))

    def listar_vinculos(self) -> list[dict[str, Any]]:
        return self._linhas(
            """
            SELECT v.*, p.nome AS perfil_nome
            FROM vinculo_agente v
            LEFT JOIN perfil_voz p ON p.id = v.perfil_id
            ORDER BY v.criado_em DESC
            """
        )

    # ----------------------------------------------------------- configuracao
    def gravar_config(self, chave: str, valor: Any) -> None:
        self._executar(
            """
            INSERT INTO configuracao (chave, valor, atualizado_em) VALUES (?, ?, ?)
            ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor, atualizado_em = excluded.atualizado_em
            """,
            (chave, json.dumps(valor, ensure_ascii=False), agora()),
        )

    def ler_config(self, chave: str, padrao: Any = None) -> Any:
        linhas = self._linhas("SELECT valor FROM configuracao WHERE chave = ?", (chave,))
        if not linhas:
            return padrao
        try:
            return json.loads(linhas[0]["valor"])
        except json.JSONDecodeError:
            return linhas[0]["valor"]

    def listar_config(self) -> dict[str, Any]:
        return {linha["chave"]: linha["valor"] for linha in self._linhas("SELECT * FROM configuracao")}


def abrir(caminho: Path) -> Cofre:
    return Cofre(caminho)
