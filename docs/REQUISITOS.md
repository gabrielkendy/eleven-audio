# O que a máquina precisa ter

Números **medidos** nesta máquina em 28/09/2026, não estimados. Onde a medição não
foi possível, está escrito que não foi, em vez de um número inventado.

## Resumo em uma linha

Um PC Windows com placa NVIDIA de **8 GB ou mais**, **16 GB de RAM**, e cerca de
**20 GB livres em disco**. Com 12 GB de placa fica confortável.

## Vídeo (o item que decide)

| situação | VRAM |
|---|---|
| Máquina com o estúdio fechado | 8.012 MiB |
| Máquina com o estúdio aberto e modelo carregado | 14.023 MiB |
| **O que o estúdio ocupa** | **≈ 6 GB** |

Como essa medição foi feita: fechei o estúdio, medi a placa, subi de novo, medi de
novo. A diferença é o consumo do estúdio. Não usei estimativa de tabela.

| placa | veredito |
|---|---|
| Sem placa NVIDIA | funciona, mas lento. Ver a seção de CPU abaixo. |
| 6 GB | apertado, o Windows já usa parte para o vídeo da tela |
| **8 GB** | **mínimo recomendado** |
| 12 GB | confortável |
| 16 GB | o que esta máquina tem, sobra espaço |

Detalhe que confunde: o Windows reserva VRAM para o vídeo da área de trabalho, e
navegador aberto também consome. O estúdio precisa dos ~6 GB **além** disso.

## Memória RAM

Medido: **1,3 GB** de pico durante uma geração. Qualquer máquina com 16 GB de RAM
sobra. Esta tem 128 GB, então não dá para dizer que precisava disso.

## Disco

| parte | tamanho | obrigatório? |
|---|---|---|
| Ambiente Python da base (quase tudo PyTorch com CUDA) | 9,0 GB | sim |
| Transcrição (Whisper large-v3) | 2,9 GB | sim, se quiser transcrever sozinho |
| Código da base e do app | menos de 0,2 GB | sim |
| Pesos do motor escolhido | baixam na primeira execução | sim |
| Qwen3-TTS (motor alternativo, experimental) | 4,3 GB | não |

**Estimativa realista de instalação: 15 a 20 GB**, mais espaço para os áudios
gerados.

Aviso de medição: os pesos dos motores baixam na primeira execução e ficam em
cache gerenciado pela própria base. Não consegui localizá-los para medir o tamanho
exato, então não afirmo um número aqui. O que dá para garantir é que o processo é
automático: na primeira geração ele baixa e guarda.

## Sistema

- **Windows 11** testado e funcionando (é o desta máquina).
- Windows 10 deve funcionar, mas **não foi testado aqui**. Não afirmo.
- Linux e macOS: a base é Python e provavelmente roda, mas **não foi testado** e os
  scripts de inicialização são PowerShell, então precisariam ser refeitos.

## Programas necessários

| programa | versão medida aqui | para quê |
|---|---|---|
| Python | 3.11 (base), 3.13 (app) | a base exige `>=3.11` |
| ffmpeg | 8.1.1 | preparar a referência: cortar silêncio e medir duração |
| Driver NVIDIA | 610.74 | falar com a placa |

O ffmpeg não é opcional. Sem ele, o preparo da referência falha, e o preparo é o
que mais melhora a clonagem (medido: 0,8025 com contra 0,7404 sem).

## Internet

Precisa **só na instalação**, para baixar as bibliotecas e os modelos. Depois
disso, o estúdio roda offline: os scripts de inicialização já ligam a base em modo
offline, e há medição de zero conexões externas durante geração e transcrição.

Ver `RODA-LOCAL.md` para essa medição.

## E sem placa NVIDIA?

Funciona. O motor Chatterbox roda em CPU nesta máquina e gerou áudio normalmente,
com licença MIT, e sem usar GPU. O custo é tempo, e é medido: **90 segundos para
gerar 7 segundos** de áudio, ou seja, cerca de 13 vezes o tempo do áudio. Na placa,
o mesmo trecho sai em 3 a 50 segundos dependendo do motor.

Quem não tem placa consegue usar, mas a paciência passa a ser o requisito.

## O que NÃO foi medido

Sou explícito para ninguém confundir ausência de dado com garantia:

- Consumo em placas diferentes desta (a única medida foi uma RTX 4080 de 16 GB).
- Tamanho exato em disco dos pesos de cada motor.
- Comportamento em Windows 10, Linux ou macOS.
- Desempenho com RAM abaixo de 16 GB.
