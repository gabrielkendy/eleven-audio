# Chatterbox V3 pt-BR

Experimento isolado com o Single Language Pack oficial `ResembleAI/Chatterbox-Multilingual-pt-br`. O runner recebe JSON por arquivo ou stdin e gera WAV. Ele fixa locale `pt-BR`, passa `language_id="pt"`, usa seed reproduzível e mantém o watermarker PerTh do Chatterbox.

## Instalação

O caminho solicitado para o venv é `C:/caminho/para/o-venv-do-experimento`. Nesta sessão a sandbox negou escrita fora do workspace, então foi criado o fallback local `.venv`.

```powershell
$uv = 'C:/caminho/para/o-venv-do-comfy/Scripts/uv.exe'
$env:UV_CACHE_DIR = "$PWD/experimentos/chatterbox-ptbr/.uv-cache"
& $uv venv --python 3.11 C:/caminho/para/o-venv-do-experimento
& $uv pip install --python C:/caminho/para/o-venv-do-experimento/Scripts/python.exe -r experimentos/chatterbox-ptbr/requirements.txt
```

Se o caminho externo continuar bloqueado, substitua-o por `experimentos/chatterbox-ptbr/.venv`. Não defina `PYTHONPATH`; remova-o do subprocesso antes de executar.

## Uso

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
experimentos/chatterbox-ptbr/.venv/Scripts/python.exe experimentos/chatterbox-ptbr/runner.py experimentos/chatterbox-ptbr/request.json
```

Também aceita JSON em stdin. `--validate-only` valida o contrato sem carregar Torch ou baixar modelos. O modo `auto` só usa CUDA com pelo menos 7 GiB livres; `device: "cuda"` força a tentativa após medição consciente.

O Chatterbox usa no máximo 6 s da referência no encoder e 10 s no decoder. A referência entregue tem 13 s e veio diretamente do MOV autorizado. O original não foi alterado.

## Fontes e licença

- Código: `resemble-ai/chatterbox`, MIT, master observado em `5de7a54`.
- Loader oficial pt-BR: Space em `9e515821e826e207cd617a0fdd0223899ed108ea`.
- Modelo: `ResembleAI/Chatterbox-Multilingual-pt-br`, MIT, arquivo T3 SHA256 `074aaf65255eb9cb960288f7cc72e09d3b5008f6e0b14868c0d4e5b0bd7cbb6c`.
- Pacote: `chatterbox-tts==0.1.7`.

Não há pontuação automática de identidade. A comparação final deve ser auditiva e cega quando possível.
