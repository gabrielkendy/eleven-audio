from app import rotas
from app.config import carregar_config


def test_sidecar_omnivoice_quebrado_nao_e_oferecido(monkeypatch, tmp_path):
    config = carregar_config({"ESTUDIO_DADOS": "dados"}, raiz=tmp_path)
    monkeypatch.setattr(
        rotas.base,
        "listar_motores",
        lambda _config: {
            "backends": [
                {
                    "id": "omnivoice-subprocess",
                    "display_name": "OmniVoice isolado",
                    "available": True,
                    "supports_cloning": True,
                },
                {
                    "id": "omnivoice",
                    "display_name": "OmniVoice",
                    "available": True,
                    "supports_cloning": True,
                },
            ]
        },
    )

    catalogo = {item["id"]: item for item in rotas._motores(config, base_no_ar=True)}

    assert catalogo["omnivoice-subprocess"]["disponivel"] is False
    assert "Use OmniVoice direto" in catalogo["omnivoice-subprocess"]["motivo"]
    assert catalogo["omnivoice"]["disponivel"] is True