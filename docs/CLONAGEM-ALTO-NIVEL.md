# Clonagem de voz em alto nível

Este documento responde uma pergunta prática: qual motor clona melhor a sua voz,
e o que dá para fazer para melhorar o resultado. Tudo aqui foi medido nesta
máquina, em 28/09/2026, ou verificado em fonte oficial.

## Como a qualidade de clone foi medida

Similaridade de locutor: o áudio gerado e a sua referência viram dois embeddings
de voz (ECAPA-TDNN, via SpeechBrain) e a gente mede o cosseno entre eles. É a
mesma família de métrica que os benchmarks de clonagem usam.

Ferramenta: `experimentos/qualidade-v2/medir_locutor.py`. Ela roda com o
interpretador do venv da base, porque é lá que vive o SpeechBrain. Não altera
nada da base.

Leitura do número: 1,0 seria idêntico. Abaixo de 0,70 costuma soar como outra
pessoa. **Isso mede identidade de locutor, não naturalidade nem pronúncia.** Um
motor pode ter similaridade menor e ainda assim soar mais natural ou pronunciar
melhor o português.

## Ranking medido, com a mesma voz e o mesmo texto

Texto único, semente 2026, o mesmo perfil de voz nos três.

| Motor | Similaridade de locutor | Tempo | Onde rodou |
|---|---|---|---|
| **VoxCPM2** | **0,8064** | 49,8 s para 7,0 s de áudio | CUDA |
| OmniVoice | 0,7694 | 15,9 s para 9,2 s de áudio | CUDA |
| Chatterbox PT-BR | 0,7567 | 90,1 s para 10,2 s de áudio | CPU |

Leitura prática: o VoxCPM2 é o que mais parece com a sua voz, e é o mais lento.
O OmniVoice é quase tão parecido e é três vezes mais rápido. O Chatterbox foi o
menos parecido neste teste, e o mais lento de todos porque caiu na CPU.

Ressalva honesta: é um texto e uma semente. Não é um veredito estatístico. Para
firmar ranking seria preciso repetir com vários textos e ouvir às cegas.

## O que melhorou de verdade: preparar a referência

Motores com estratégia "head" aproveitam só os primeiros segundos da amostra. Se
a amostra tem silêncio no começo, esses segundos preciosos vão embora.

O que o estúdio faz agora, antes de mandar a amostra para o motor:

1. acha a janela de fala e corta o silêncio das pontas;
2. acerta o nível, sem amplificar mais que 12 dB;
3. mantém a taxa e a profundidade originais.

Amostra de teste: 2 s de silêncio + 30 s de voz + 3 s de silêncio (35 s no total).
Depois de preparar, o motor recebeu **30,01 s**, só de fala.

Comparação controlada, mesmo texto, mesmo motor, mesma semente, mesma voz:

| Condição | Similaridade de locutor |
|---|---|
| **Com preparação** | **0,8025** |
| Sem preparação | 0,7404 |

Ganho medido de **+0,062** só por não desperdiçar o começo da amostra.

A preparação é ligada por padrão. Para desligar e comparar:
`ESTUDIO_PREPARO=0`.

O que ela **não** faz: não reordena a amostra e não corta fala. Isso é de
propósito, porque reordenar quebraria o casamento entre o áudio e o texto da
transcrição, e transcrição que não casa com o áudio piora o clone.

## Modelos melhores que ainda não estão aqui

Pesquisa em fontes oficiais (HuggingFace, GitHub, papers), com foco em português
do Brasil, 16 GB de VRAM e licença que permita uso comercial.

### 1. Qwen3-TTS 1.7B (Alibaba) — o mais promissor

- **Licença:** Apache-2.0, no código e nos pesos. Uso comercial liberado.
- **Português:** sim, entre os 10 idiomas.
- **Clonagem:** a partir de uma amostra de 3 segundos.
- **Tamanho:** 1,7B de parâmetros, cabe folgado em 16 GB.
- **Instalação:** `pip install qwen-tts`. Existe GGUF comunitário, também Apache-2.0.
- **Evidência:** na tabela publicada pela própria Qwen, o português fica em 0,817
  de similaridade, à frente de MiniMax (0,805) e ElevenLabs (0,711).
- **Estado:** não existe no VoiceStudio. Está sendo montado aqui como motor
  isolado, no mesmo padrão do Chatterbox.

Modelo: `Qwen/Qwen3-TTS-12Hz-1.7B-Base`. Paper: arXiv 2601.15621.

### 2. VoxCPM2 — já roda aqui

Maior similaridade de português entre os que já estão instalados e permitem uso
comercial. Já é o vencedor do ranking medido acima. O caminho mais curto para
melhorar agora é usar este motor e mandar amostra longa e limpa.

### 3. FireRedTTS3-Base (Xiaohongshu) — melhor número, instalação chata

- **Licença:** Apache-2.0. **Português:** sim, entre 24 idiomas.
- **Evidência:** relatório técnico (arXiv 2608.17492) traz português em 86,3,
  melhor da tabela, com VoxCPM2 em 83,7 e ElevenLabs em 71,1.
- **Problema:** clonagem exige 8 GB e o resto exige 16 GB. No Windows a
  instalação oficial pede `flash_attn`, que é chata. Existe fork comunitário com
  pacote pronto.

## Descartados, e por quê

**Por licença:**
- OmniVoice: pesos CC-BY-NC. Tem o maior índice de português em tabela de
  terceiros, e fica fora justamente pela licença. As versões quantizadas herdam
  a restrição.
- Higgs TTS 3: licença de pesquisa, não comercial.
- Fish S2 Pro: exige licença paga.
- F5-TTS, XTTS-v2, E2-TTS, Spark-TTS: licença incompatível com uso comercial.

**Por não falarem português:**
Spark-TTS, MegaTTS 3, Orpheus, Sesame CSM, VibeVoice, Higgs 2, OpenVoice,
CosyVoice 3, IndexTTS 2.5, GPT-SoVITS, AuK.

**Fechado:** Seed-TTS.

## O que falta para fechar a análise

1. Rodar o Qwen3-TTS de verdade nesta máquina e medir contra o VoxCPM2, com o
   mesmo texto e a mesma voz.
2. Repetir o ranking com vários textos, e não um só.
3. Comparação cega: gerar as amostras, embaralhar e ouvir sem saber qual é qual.
   Similaridade de locutor não captura naturalidade nem sotaque.
4. Os cards dizem "Portuguese" sem separar pt-BR de pt-PT, e não achei avaliação
   cega independente específica de português do Brasil. A validação final tem que
   ser com amostra brasileira, ouvindo.
