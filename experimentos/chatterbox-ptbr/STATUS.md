# Status

Bloqueado antes da inferência real.

Concluído:

- API e loader oficiais lidos.
- Runner JSON para WAV implementado com locale pt-BR fixo.
- Validação do runner testada em venv Python 3.11 isolado.
- Referência original de Gabriel extraída do MOV autorizado em 13 s, 24 kHz mono.
- Hardware e configuração registrados em `REPORT.json`.

Bloqueios desta sessão:

- A sandbox negou escrita em `C:/caminho/para/o-venv-do-experimento`; o fallback `.venv` foi criado dentro do experimento.
- A sandbox negou conexões do shell para PyPI, GitHub e Hugging Face.
- O navegador bloqueou os endpoints binários de download.
- Sem pacote e checkpoints locais, não houve geração de WAV nem medição de tempo de inferência.

Próximo passo mínimo: liberar rede para o shell e escrita no caminho do venv, rodar a instalação do README e executar `runner.py request.json`. A RTX tinha 5.925 MiB livres, abaixo do limiar conservador de 7 GiB do modo automático; liberar VRAM exige coordenação com o usuário.
