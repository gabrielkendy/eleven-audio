from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.cofre import abrir
from app.config import Configuracao


class ErroAgente(RuntimeError):
    """Falha ao falar com a base do agente.

    Carrega o código HTTP quando houve resposta, para quem chama decidir pelo
    código em vez de casar texto de mensagem.
    """

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


class Agente:
    def __init__(self, config: Configuracao) -> None:
        self.config = config
        self._banco = config.dados / "estudio.db"

    def _requisitar(
        self, metodo: str, caminho: str, corpo: dict[str, Any] | None = None
    ) -> Any:
        dados = json.dumps(corpo).encode() if corpo is not None else None
        requisicao = Request(
            f"{self.config.base_url}{caminho}",
            data=dados,
            headers={"Content-Type": "application/json"} if dados else {},
            method=metodo,
        )
        try:
            with urlopen(
                requisicao, timeout=min(self.config.timeout_s, 3.0)
            ) as resposta:
                conteudo = resposta.read()
                return json.loads(conteudo) if conteudo else None
        except HTTPError as erro:
            detalhe = erro.read().decode(errors="replace")
            try:
                detalhe = json.loads(detalhe).get("detail", detalhe)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise ErroAgente(
                f"A base recusou a operação ({erro.code}): {detalhe}", erro.code
            ) from erro
        except (URLError, TimeoutError, OSError) as erro:
            motivo = getattr(erro, "reason", erro)
            raise ErroAgente(f"Servidor MCP da base indisponível: {motivo}") from erro

    def status(self) -> dict[str, Any]:
        cofre = abrir(self._banco)
        try:
            locais = cofre.listar_vinculos()
        finally:
            cofre.fechar()

        motivo = None
        try:
            base = self._requisitar("GET", "/api/mcp/bindings")
        except ErroAgente as erro:
            base, motivo = [], str(erro)
        try:
            motores = self._requisitar("GET", "/engines/tts")
        except ErroAgente as erro:
            motores = {"active": None, "backends": []}
            motivo = motivo or str(erro)

        return {
            "mcp": {"estado": "erro" if motivo else "ok", "motivo": motivo},
            "clientes_vinculados": len(
                {v.get("client_id") or v["cliente_id"] for v in [*base, *locais]}
            ),
            "vinculos_base": base,
            "vinculos_locais": locais,
            "motores": motores,
        }

    def ligar(self, cliente_id: str, perfil_id: str) -> dict[str, Any]:
        cliente_id = cliente_id.strip()
        perfil_id = perfil_id.strip()
        if not cliente_id or len(cliente_id) > 128:
            raise ValueError(
                "O identificador do cliente deve ter entre 1 e 128 caracteres"
            )

        cofre = abrir(self._banco)
        try:
            perfil = cofre.perfil(perfil_id)
            if perfil is None:
                raise ValueError(f"Perfil de voz local não encontrado: {perfil_id}")
            corpo = {
                "client_id": cliente_id,
                "label": cliente_id,
                "profile_id": perfil["id_na_base"],
                "default_engine": self.config.motor,
            }
            resposta = self._requisitar("PUT", "/api/mcp/bindings", corpo)
            cofre.salvar_vinculo(cliente_id=cliente_id, perfil_id=perfil_id)
        finally:
            cofre.fechar()
        return {
            "estado": "ligado",
            "cliente_id": cliente_id,
            "perfil_id": perfil_id,
            "perfil_id_base": perfil["id_na_base"],
            "vinculo_base": resposta,
        }

    def desligar(self, cliente_id: str) -> dict[str, str]:
        cliente_id = cliente_id.strip()
        if not cliente_id:
            raise ValueError("Informe o identificador do cliente")
        try:
            self._requisitar("DELETE", f"/api/mcp/bindings/{quote(cliente_id, safe='')}")
        except ErroAgente as erro:
            # Desligar precisa ser idempotente. A base responde 404 quando não há
            # vínculo, e isso não é falha de comunicação: é o estado desejado já
            # alcançado. Antes, clicar em desligar duas vezes devolvia 502 Bad
            # Gateway, como se algo tivesse quebrado, e ainda deixava o vínculo
            # local para trás.
            if erro.status != 404:
                raise
        cofre = abrir(self._banco)
        try:
            cofre.remover_vinculo(cliente_id)
        finally:
            cofre.fechar()
        return {"estado": "desligado", "cliente_id": cliente_id}
