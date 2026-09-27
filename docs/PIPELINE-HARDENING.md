# Hardening técnico do pipeline ELEVEN_AUDIO

## Escopo executado

Somente `app/ajustes.py`, `app/base.py`, `app/motor.py`, o novo `tests/test_qualidade_pipeline.py` e este relatório. VoiceStudio/base externa, dados, venv, segredos e servidor não foram modificados. Sem commit, push ou reinício. `.hermes/` já estava não rastreado ao iniciar; `experimentos/` apareceu durante a execução paralela e não foi tocado.

## Correções

- Normalização numérica rejeita bool, NaN e infinitos com `ValueError` (inclusive evitando o `OverflowError` anterior). Campos inteiros não truncam frações. Decimal permite verificar integralidade sem perder precisão de sementes grandes representadas por string. Formas integrais como `32.0` continuam aceitas; booleanos verdadeiros e aliases humanos continuam válidos nos campos booleanos.
- `semente` explícita tem precedência sobre `ajustes.seed`, inclusive quando vale zero. Sem semente explícita, preserva-se o ajuste. Nenhum dicionário fornecido pelo chamador é mutado. Não houve mudança de assinatura.
- Resposta HTTP 200 não equivale a áudio. Validação de assinatura RIFF/WAVE, tamanho declarado, abertura por `wave`, quadros não vazios, taxa positiva e leitura completa antes de retornar bytes da base. `motor.sintetizar` repete a barreira antes de salvar, inclusive com `base.gerar_audio` substituída por mock. JSON, vazio, cabeçalho incompleto e áudio truncado não viram arquivo WAV persistido.
- Motor real informa `dispositivo: nao_informado`: bytes de áudio não comprovam CUDA. O mock continua CPU. Não foi adicionada consulta de hardware local que confundiria hardware disponível com dispositivo efetivamente usado pela base.

## Achados e limites

### Colisão de nomes confirmada, não corrigida neste escopo

`saidas.nome_arquivo` usa precisão de segundos e `gravar_bytes` usa `Path.write_bytes`, que sobrescreve. Duas gerações do mesmo motor/perfil no mesmo segundo podem colidir, inclusive concorrentes. O contrato existente exige quatro partes e horário de seis dígitos. `saidas.py` foi apenas lido: a correção exige decisão explícita sobre unicidade, criação exclusiva e compatibilidade de nomes.

Prova local, sem escrever arquivo (datetime fixo de teste):

```text
2026-09-27_120000_omnivoice_perfil.wav
2026-09-27_120000_omnivoice_perfil.wav
colisao: True
```

### Limites da validação

- O contrato deste caminho permanece `gerar_audio(...) -> bytes`. JSON com `audio_url` é rejeitado com `ErroBase`, não seguido automaticamente. Outros caminhos, como comparação, possuem seu próprio adaptador; não foram alterados. Se a base real retornar JSON neste caminho, é necessário implementar download controlado numa tarefa posterior, não salvar o JSON como WAV.
- Validação cobre WAV RIFF PCM suportado pelo `wave` do Python, coerente com a medição já usada em `saidas.py`. Não adiciona suporte a OGG, RF64, WAV float/comprimido ou conversão. Tamanho RIFF deve corresponder ao corpo recebido; formato de stream com tamanho indefinido é rejeitado (`stream=false` já é enviado).
- Integridade estrutural não é qualidade perceptiva. Silêncio PCM válido continua válido. Não mede identidade vocal, inteligibilidade, clipping ou naturalidade, não compara F0/MFCC e não demonstra melhora sobre a avaliação de 6/10.
- `nao_informado` é deliberado até existir telemetria vinculada à geração; não significa CPU nem falha de GPU.
- Testes são locais com WAV sintético, temporários e MockTransport; nenhum modelo foi acionado. Não houve prova ponta a ponta com a base em execução.

## TDD e verificação real

Antes das correções: regressões numéricas produziram `18 failed, 19 passed`; a precedência produziu `2 failed, 39 passed`; integridade de WAV e dispositivo produziram `7 failed, 42 passed`. Erros de lint introduzidos durante desenvolvimento foram corrigidos apenas nos arquivos autorizados.

Comandos finais, no repositório `C:/caminho/para/eleven-audio`:

```bash
env -u PYTHONPATH C:/caminho/para/o-venv-do-projeto/Scripts/python.exe -m pytest
env -u PYTHONPATH C:/caminho/para/o-venv-do-projeto/Scripts/python.exe -m ruff check app tests scripts
git diff --check
```

Saída real da suíte final (resumo de execução):

```text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.0, pluggy-1.6.0
rootdir: C:\caminho\para\eleven-audio
plugins: anyio-4.15.1
collected 123 items

============================== warnings summary ===============================
..\..\.venvs\eleven-audio\Lib\site-packages\starlette\testclient.py:45
  C:\caminho\para\o-venv-do-projeto\Lib\site-packages\starlette\testclient.py:45: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

======================= 123 passed, 1 warning in 19.72s =======================
```

Ruff (código de saída 0):

```text
All checks passed!
```

`git diff --check` retornou código 0; apenas aviso do Git sobre normalização futura LF para CRLF em `app/ajustes.py`. A advertência de depreciação Starlette/AnyIO permanece; nenhuma dependência foi alterada para escondê-la.
