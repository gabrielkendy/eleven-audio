from pathlib import Path

from ferramentas.protocolo_seguranca import varrer_codigo


def test_varredura_exclui_apenas_o_proprio_scanner() -> None:
    raiz = Path(__file__).resolve().parents[1]

    arquivos = {rel for rel, _, _ in varrer_codigo(raiz)}

    assert "ferramentas/protocolo_seguranca.py" not in arquivos
    assert "app/servidor.py" in arquivos
