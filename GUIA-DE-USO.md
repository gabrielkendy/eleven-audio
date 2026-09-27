# Guia de uso do Estudio de Voz Local

## Como ligar

Abra a pasta `scripts` e clique duas vezes em `ligar-tudo.bat`.

O atalho liga a base na porta 3900 e o app na porta 7800. Depois abre `http://127.0.0.1:7800` no navegador.

A janela pode ficar aberta enquanto voce usa o estudio. Fechar a janela desliga os servicos que o atalho iniciou. Se os dois servicos ja estavam ligados, o atalho nao cria copias e encerra sozinho.

## Como gerar audio

Abra a area GERAR. Escreva o texto. Escolha a voz e o motor. Clique em gerar. Espere o player aparecer. O primeiro uso de um motor pode demorar porque ele baixa os arquivos necessarios.

Os audios ficam em `saidas\audio`, organizados pela data no nome. Use o botao ABRIR PASTA DE SAIDAS quando ele estiver disponivel na tela.

## Como clonar uma voz

Abra a area CLONAR. Use um clipe limpo de 5 a 15 segundos. Informe o nome e a transcricao exata. Confirme que a voz e sua ou que voce tem autorizacao. A clonagem fica bloqueada sem esse aceite.

Depois escolha o perfil criado na area GERAR. Nunca clone voz de outra pessoa sem permissao.

## Quando um motor nao roda

Leia o motivo mostrado ao lado do motor. No primeiro uso, aguarde o download. Se faltar memoria de video, feche outros programas ou use CPU. Se a base estiver fora do ar, feche a janela do estudio e abra `ligar-tudo.bat` novamente. O registro fica em `dados\logs\ligar-tudo.log`.

## Licencas

O Estudio de Voz Local ainda tem licenca a definir. A base VoiceStudio usa AGPL-3.0. OmniVoice, VoxCPM2, IndexTTS 2.5, Faster-Whisper e WhisperX possuem licencas proprias dos projetos. O motor mock segue a licenca do nosso app.

O audio gerado e seu. Leia a licenca do motor escolhido antes de uso comercial. O estudo roda localmente. Nao exige login, conta, nuvem ou cobranca.
