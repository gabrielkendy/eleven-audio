# Modelos que dá para instalar

> Para o foco específico de qualidade de clonagem, com ranking medido nesta
> máquina, veja também `docs/CLONAGEM-ALTO-NIVEL.md`.

Análise dos motores de voz que a base oferece mas que ainda não estão instalados
nesta máquina, feita para responder a uma pergunta prática: quais deles valem a
pena para um estúdio que fala português do Brasil e roda numa RTX 4080 de 16 GB.

Verificado em 28/09/2026, em fontes oficiais: READMEs e arquivos de licença dos
repositórios no GitHub, cards e metadados da API do HuggingFace, e as tabelas de
benchmark publicadas pelos próprios autores.

## O que a base oferece hoje

A base anuncia **17 motores**. Quatro estão disponíveis nesta máquina:
`omnivoice`, `voxcpm2`, `kittentts` e o `chatterbox-ptbr` do lado de cá.
Os outros treze aparecem no catálogo com o motivo da indisponibilidade.

## Os três critérios

1. **Falar português.** É o critério que elimina mais candidatos.
2. **Poder usar comercialmente.** Licença de pesos que proíbe uso comercial é
   bandeira vermelha, mesmo quando o código é livre.
3. **Caber na GPU.** Uma 4080 de 16 GB já divide espaço com os motores
   instalados.

## Descartados por não falarem português

| Motor | Idiomas | Licença | Por que saiu |
|---|---|---|---|
| CosyVoice 3 | chinês, inglês, francês, espanhol, japonês, coreano, italiano, russo, alemão | Apache-2.0 | não tem português |
| GPT-SoVITS | inglês, japonês, coreano, cantonês, chinês | MIT | não tem português |
| IndexTTS 2.5 | chinês, inglês, japonês, espanhol, árabe | bilibili Model Use | não tem português |

O IndexTTS 2.5 tem controle de emoção e uma licença menos restritiva do que
parecia: o limite é 100 milhões de usuários ativos mensais ou 1 bilhão de RMB
de receita anual, bem acima do nosso caso. Ele sai só pelo idioma.

## Descartado por licença

| Motor | Licença do código | Licença dos pesos |
|---|---|---|
| OmniVoice GGUF | Apache-2.0 | **CC-BY-NC-4.0** |

O OmniVoice tem código Apache-2.0 mas pesos CC-BY-NC, e as versões quantizadas
herdam a mesma restrição. Quantizar não limpa a licença. Isso já está tratado no
código: `MOTORES_BLOQUEADOS`, em `app/rotas.py`, impede que o catálogo ofereça
esse caminho para uso comercial.

## Recomendados

| Motor | pt-BR | Licença | Disco | VRAM | Clona |
|---|---|---|---|---|---|
| Confucius4-TTS | sim | Apache-2.0 (código e pesos) | 3,1 GB | 5 a 6 GB (estimado) | sim |
| dots.tts | sim | Apache-2.0 (código e pesos) | ~9 GB | 5,3 a 6,5 GB de pico | sim |
| MOSS-TTS-Nano | sim | Apache-2.0 (pesos sem arquivo de licença) | ~0,5 GB | CPU, não usa GPU | sim |
| PocketTTS | sim | MIT código, CC-BY-4.0 pesos | ~0,5 GB | CPU, não usa GPU | sim |

Detalhes que importam:

- **Confucius4-TTS** tem português entre os 14 idiomas, e o benchmark do próprio
  autor mede WER 2,48 em português. Clona em modo cross-lingual e mantém a
  identidade do locutor ao trocar de idioma. É o mais leve dos que usam GPU.
- **dots.tts** lista português entre os 24 idiomas e é Apache-2.0 no código e nos
  checkpoints. O pico de memória declarado vai de 5,3 GB em áudios curtos até
  10,5 GB no balde de 80 segundos.
- **MOSS-TTS-Nano** roda inteiro na CPU, então não disputa a GPU com nada. Tem
  português entre os 20 idiomas. Ressalva honesta: o metadado do card diz
  Apache-2.0, mas o repositório de pesos não tem arquivo de licença publicado, e
  o próprio card pede para tratar o repositório como ainda não licenciado para
  redistribuição.
- **PocketTTS** é o mais leve. Código MIT, pesos CC-BY-4.0, que permite uso
  comercial com atribuição. Os pesos são liberados com aceite de termos no
  HuggingFace, então exige login.

## Só se sobrar VRAM

| Motor | pt-BR | Licença | Disco | Por que não é a primeira escolha |
|---|---|---|---|---|
| MOSS-TTS-v1.5 | sim | Apache-2.0 | 17 GB em bf16 | não cabe nos 16 GB da GPU nessa forma |

O caminho que a base usa hoje carrega os pesos em bf16, e são cerca de 17 GB.
Existe GGUF quantizado que cabe em 8 GB e também é Apache-2.0, mas isso seria
mudar como a base carrega o motor.

## Ordem sugerida

1. **Confucius4-TTS**, se o objetivo é o melhor resultado em português gastando
   pouca VRAM: 3 GB de pesos e 5 a 6 GB de pico.
2. **dots.tts**, como segundo motor de GPU, para comparar resultado em português
   com o Confucius. É o que o próprio autor declara como referência de
   similaridade de locutor.
3. **MOSS-TTS-Nano** ou **PocketTTS** para começar sem risco nenhum: rodam na
   CPU, não consomem VRAM e não têm como derrubar os motores que já funcionam.

## Quanto da amostra cada motor aproveita

Descoberta da mesma rodada, e vale para qualquer motor que você instalar: o teto
da amostra não é o que o motor usa. A base informa esse número por motor, e a
tela de Clonar mostra em português o que cada um aproveita.

| Motor | O que aproveita da amostra |
|---|---|
| OmniVoice | a melhor janela de 20 segundos |
| VoxCPM2 | os primeiros 30 segundos |
| Chatterbox PT-BR | aceitou uma amostra de 75 s no teste e gerou normalmente |

Ou seja: mandar uma amostra de 3 minutos não faz o motor usar 3 minutos. Faz ele
ter mais material para escolher a janela boa. É por isso que o teto da tela é de
3 minutos e não de 20 segundos.

## Como instalar

O catálogo da base, na aba Configuração da tela, tem a instalação em um clique
para a maioria destes motores. Confucius4-TTS, dots.tts e MOSS-TTS-Nano marcam
`one_click_install`. A instalação é isolada: cada motor ganha a própria pasta e o
próprio ambiente Python, e nada do que ele instala toca nos motores que já
funcionam.
