# Roda local. Informação medida, não prometida.

Este documento existe para responder uma pergunta só: **a solução precisa de internet?**
Não. E isso não é afirmação de arquitetura, é medição com as conexões abertas sendo observadas.

## O que roda na sua máquina

| peça | onde roda | endereço |
|---|---|---|
| Aplicação | seu PC, Python local | `127.0.0.1:7800` |
| Motor de voz (base VoiceStudio) | seu PC, Python local | `127.0.0.1:3900` |
| Modelos de clonagem | disco local, carregados na RTX 4080 | `experimentos/qwen3-tts/model-cache` (9,09 GB) mais o acervo da base |
| Transcrição | modelo local, sem serviço na nuvem | dentro da base |
| Áudio gerado | disco local | `saidas/audio/<data>/` |

Os dois serviços escutam apenas em `127.0.0.1`, o endereço que só existe dentro do seu computador. Nenhum deles abre porta para a rede, então **outra máquina não alcança o seu estúdio**, mesmo estando no mesmo wi-fi.

## Como medimos, e o que saiu

O teste abre uma geração de verdade e uma transcrição de verdade, e lê a tabela de conexões do Windows a cada 0,35 s, olhando só os processos do app e da base.

**Geração:**

| situação | conexões locais | conexões externas |
|---|---|---|
| base no modo padrão | 8 | **1** (HTTPS 443 para IP da AWS CloudFront) |
| base em modo offline | 8 | **0** |

**Transcrição:** 7 locais, **0 externas**. Transcreveu corretamente, 106 caracteres a partir de um áudio de teste.

## A conexão que existia, e o que ela era

No modo padrão, a base consultava o HuggingFace **a cada geração**, para checar metadados de modelo. É consulta de versão, não envio de áudio: seu áudio e sua voz nunca saíram daqui. Mesmo assim, é uma conexão que não precisa existir.

Três variáveis de ambiente resolvem, e já estão nos scripts de inicialização
(`scripts/subir-base.ps1` e `scripts/ligar-tudo.ps1`):

```
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
```

Efeito medido: a conexão externa desaparece **e a geração continua idêntica**. Os modelos já estão em disco, então não há o que baixar.

## Como você mesmo confere

Com tudo no ar, rode uma geração e olhe as conexões:

```bash
netstat -ano | grep ESTABLISHED
```

Compare com os PIDs que escutam nas portas 7800 e 3900. Qualquer linha `ESTABLISHED` desses PIDs com endereço remoto fora de `127.0.0.1` seria internet. Em modo offline, não aparece nenhuma.

## Se você quiser baixar um modelo novo

O modo offline impede download. Para instalar motor novo, rode a base uma vez sem as três variáveis, deixe o download terminar, e volte ao modo offline. A clonagem e a geração do dia a dia não precisam disso.
