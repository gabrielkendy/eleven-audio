# Guia de uso do Estudio de Voz Local

## Como ligar

Abra a pasta `scripts` e clique duas vezes em `ligar-tudo.bat`.

O atalho liga a base na porta 3900 e o app na porta 7800. Depois abre `http://127.0.0.1:7800` no navegador.

A janela pode ficar aberta enquanto voce usa o estudio. Fechar a janela desliga os servicos que o atalho iniciou. Se os dois servicos ja estavam ligados, o atalho nao cria copias e encerra sozinho.

## Como gerar audio

Abra a area GERAR. Escreva o texto. Escolha a voz e o motor. Clique em gerar. Espere o player aparecer. O primeiro uso de um motor pode demorar porque ele baixa os arquivos necessarios.

Os audios ficam em `saidas\audio`, organizados pela data no nome. Use o botao ABRIR PASTA DE SAIDAS quando ele estiver disponivel na tela.

## Como clonar uma voz

Abra a area CLONAR. Use um clipe limpo de 5 a 30 segundos. Informe o nome e a transcricao exata. Confirme que a voz e sua ou que voce tem autorizacao. A clonagem fica bloqueada sem esse aceite.

**Mais material de voz, mais fiel o clone.** O clipe de 30 segundos e o que entrega a maior fidelidade: o OmniVoice usa a melhor janela dele automaticamente e o VoxCPM2 aproveita os 30 segundos inteiros.

## Qual combinacao usar (medido em 27/09/2026)

Mesma frase gerada com a voz do dono, comparada com a gravacao real dele (F0 mediano de 124 Hz, faixa de 113 a 143 Hz). Timbre medido por similaridade de MFCC contra a referencia.

| Combinacao | Texto certo | F0 medido | Diferenca de tom | Timbre | RTF |
|---|---|---|---|---|---|
| **OmniVoice + referencia de 30 s** | 100% | 126 Hz | **2 Hz** | **0,993** | 0,67 |
| OmniVoice + referencia de 13 s | 100% | 134 Hz | 10 Hz | 0,995 | **0,16** |
| VoxCPM2 + referencia de 30 s | 100% | 117 Hz | 8 Hz | 0,959 | 2,72 |
| VoxCPM2 + referencia de 13 s | 100% | 145 Hz | 21 Hz | 0,964 | 1,53 |

Leitura honesta: o **OmniVoice com 30 segundos** e o mais fiel ao dono da voz, com o tom praticamente no lugar e o timbre mais proximo. O **OmniVoice com 13 s** e o mais rapido de todos, com timbre igualmente proximo e o tom um pouco acima. O **VoxCPM2** e o unico que entrega 48 kHz de estudio, mas o timbre fica menos parecido com a voz original.

Regra pratica: quer parecer com a pessoa, use OmniVoice com 30 segundos. Quer arquivo de estudio a 48 kHz e nao se importa com uma diferenca pequena de timbre, use VoxCPM2. Todos os quatro acertaram o texto por completo.

Perfis criados: `Voz do Gabriel (30s)` e `Voz do Gabriel (13s)`. Os audios da medicao ficam em `saidas\audio\comparativo-voz`.

Depois escolha o perfil criado na area GERAR. Nunca clone voz de outra pessoa sem permissao.

## Quando um motor nao roda

Leia o motivo mostrado ao lado do motor. No primeiro uso, aguarde o download. Se faltar memoria de video, feche outros programas ou use CPU. Se a base estiver fora do ar, feche a janela do estudio e abra `ligar-tudo.bat` novamente. O registro fica em `dados\logs\ligar-tudo.log`.

## Licencas

O Estudio de Voz Local ainda tem licenca a definir. A base VoiceStudio usa AGPL-3.0. OmniVoice, VoxCPM2, IndexTTS 2.5, Faster-Whisper e WhisperX possuem licencas proprias dos projetos. O motor mock segue a licenca do nosso app.

O audio gerado e seu. Leia a licenca do motor escolhido antes de uso comercial. O estudo roda localmente. Nao exige login, conta, nuvem ou cobranca.
