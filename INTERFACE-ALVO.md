# INTERFACE ALVO (alto nível, alinhada ao ElevenLabs)

> Fonte: `3-AS-7-FASES-ENTREGUES/FASE-04-INTERFACE/FASE-04.md` (anatomia medida) e os prints do app em
> `3-AS-7-FASES-ENTREGUES/FASE-02-COLETA/prints-internos/`. Cores do alvo amostradas pixel a pixel.

## 1. O que o alvo faz e a gente copia

1. **Uma função, uma tela.** Nada de tela única fazendo tudo.
2. **Card compositor central.** Um cartão grande e arredondado com: linha de abas com ícone no topo, área de texto gigante, pílulas de exemplo embaixo, e uma linha final com chip de motor, chip de voz e o botão escuro de gerar.
3. **Painel de ajustes à direita.** Voz, motor e sliders, com rótulo nas duas pontas de cada slider.
4. **Barra do topo enxuta.** Ícone de menu, título da tela, e à direita o estado/avatar.
5. **Contador de caracteres com tempo estimado** no canto do editor.
6. **Botão de gerar com atalho `Ctrl+Enter` escrito nele.**
7. **Player com onda** logo abaixo, com nome do arquivo, tempo e ações (baixar, abrir pasta).
8. **Pílulas de ponto de partida** para quem não sabe o que escrever.
9. **Estado vazio que ensina**, estado de erro curto e sem desculpa.

## 2. O que NÃO se copia (marca alheia)

Logotipo, nome ElevenLabs, pílula laranja, os quatro gradientes medidos, a família tipográfica exata, textos de marketing, escada de preço/crédito, menu de sete itens, modal de idioma com bandeira, selo `Popular`/`Get Pro`, widget de atendimento.

## 3. Medidas do alvo (usar como referência, não como identidade)

| Item | Valor medido |
|---|---|
| Fundo | `#FDFCFC` |
| Painel | `#F5F3F1` |
| Cartão | `#FFFFFF` |
| Texto e ação | `#000000` |
| Raio dos cartões | grande, 16 a 20 px |
| Borda | quase inexistente, 1px bem clara |

## 4. Dois temas, mesma estrutura

O estúdio tem **dois temas** controlados por `data-tema` no `<html>`: `estudio` (escuro, a identidade da casa) e `papel` (claro, alinhado ao alvo). Toda cor sai de variável CSS. O seletor fica na área CONFIGURACAO e a escolha persiste em `localStorage` (`estudio:tema`).

```css
:root, [data-tema="estudio"] {
  --fundo: #050510; --painel: #0b0b1a; --cartao: rgba(255,255,255,0.035);
  --texto: #f5efe8; --texto-fraco: #9a97b8; --texto-tenue: #6c6a85;
  --acento: #3d5afe; --acento-claro: #7d8cff; --dourado: #c9a86b;
  --borda: rgba(255,255,255,0.07); --borda-forte: rgba(255,255,255,0.14);
}
[data-tema="papel"] {
  --fundo: #fdfcfc; --painel: #f5f3f1; --cartao: #ffffff;
  --texto: #0a0a0a; --texto-fraco: #5b5b66; --texto-tenue: #8a8a94;
  --acento: #0a0a0a; --acento-claro: #2b2b33; --dourado: #9b6a1f;
  --borda: rgba(0,0,0,0.08); --borda-forte: rgba(0,0,0,0.16);
}
```

Tipografia: display serifada (`--display`, Fraunces) só em título grande de tela; corpo `--corpo` (Inter). Nada de fonte de sistema em texto visível além do fallback.

## 5. Classes obrigatórias (contrato entre os arquivos)

Quem monta o CSS (`web/estilo.css`) garante estas classes; quem monta cada área usa exatamente estes nomes.

| Classe | O que é |
|---|---|
| `.estudio` | grade geral: `sidebar` + `conteudo` |
| `.lateral` | barra lateral escura/clara com marca e menu |
| `.menu button` | item de menu (estado `.ativo`) |
| `.conteudo` | coluna da direita |
| `.topo` | barra do topo: menu sanfona, `#titulo-area`, `#resumo-status` |
| `.painel` | cartão da área (raio grande, borda fina) |
| `.compositor` | cartão compositor: abas, texto, pílulas e linha de ação |
| `.abas` + `.aba` (`.ativa`) | linha de abas com ícone dentro do compositor |
| `.pílulas` + `.pílula` | pílulas de exemplo/ponto de partida |
| `.linha-acao` | linha final do compositor: chips à esquerda, botão à direita |
| `.chip` | chip de motor ou de voz (avatar redondo + texto + chevron) |
| `.pastilha` | selo pequeno de versão/estado (ex.: `v2`) |
| `.rail` | painel de ajustes à direita (`grid-template-columns: minmax(0,1fr) 340px`) |
| `.campo-rotulo` | rótulo maiúsculo pequeno de campo |
| `.slider` | controle deslizante com rótulo nas duas pontas |
| `.duplo` | dois players lado a lado (A e B) para comparação |
| `.player` | player: botão redondo, onda desenhada em divs, tempo, ações |
| `.onda` | caixa da onda (barras geradas por JS, altura variável) |
| `.solte` | área de arrastar e soltar arquivo |
| `.vazio` | estado vazio que ensina (ícone + frase + atalho) |
| `.aviso` | mensagem de erro curta e sem desculpa |
| `.rodape` | barra fixa de status embaixo |
| `.grade-cartoes` | grade de cartões (config, listas) |

## 6. Anatomia por área

### GERAR (área principal, a que vende)
- `.topo`: título `Gerar`, à direita `#resumo-status`.
- `.compositor`:
  - `.abas` com `Speech` ativo, `Clonar`, `Desenhar`, `Transcrever`, `Agente` (troca de área pelo clique, mesma função do menu).
  - `textarea` gigante (`data-campo="texto"`), mínimo 320px de altura, sem borda interna, fundo transparente.
  - `.pílulas` de ponto de partida (4 a 6 em português): `Narrar um trecho`, `Abrir o vídeo`, `Explicar em 30 segundos`, `Ler um anúncio`, `Encerrar com chamada`.
  - `.linha-acao`: `.chip` do motor (com `.pastilha` de versão e estado de instalação), `.chip` da voz (avatar + nome + origem), `More options` equivalente = botão `Ajustes` que abre/fecha o `.rail`; à direita o botão principal `Gerar áudio` com `Ctrl+Enter` escrito.
- `.rail`: `Motor` (select), `Voz` (busca por texto + lista com botão de prévia e `usar esta voz`), `Velocidade` (slider 0.5 a 2.0, rótulo `Mais lento` / `Mais rápido`), `Variação` (slider, `Mais variável` / `Mais estável`), e `Marcas aceitas` mostrando as marcas do motor escolhido.
- Contador `N caracteres · ~X s` atualizando ao digitar.
- Depois de gerar: `.player` com onda, tempo, `Baixar WAV`, `Abrir pasta`.
- Aba `Histórico` no card: últimas gerações com motor, tempo e caminho.

### CLONAR
- Duas colunas: `Amostra` (esquerda) e `Perfil` (direita).
- `.solte` para arrastar arquivo + botão `Gravar agora` (MediaRecorder) + medidor de duração (regra dura: 5 a 15 segundos, o servidor recusa fora disso).
- Campo de transcrição da amostra (`gerar transcrição` chama `/api/transcrever`).
- Metadados: nome, idioma, origem da voz.
- Aviso de consentimento com caixa de seleção (obrigatório, senão 409).
- Botão `Criar perfil de voz`.
- `.duplo` com `.player` A (`voz original`) e B (`voz clonada`) para provar a clonagem.
- Lista de perfis salvos com origem (`clonado`, `desenhado`) e botão de excluir.

### DESENHAR
- Descrição livre (textarea) + `.pílulas` de ponto de partida (Narrador, Locutor, Personagem, Sussurro, Idoso, Infantil) que preenchem a descrição.
- `.rail` com nome do perfil, motor (só `voxcpm2` funciona) e prévia.
- Resultado: `.player` + nome do perfil criado.

### TRANSCREVER
- `.solte` grande (áudio ou vídeo), lista de formatos aceitos, idioma, botão `Transcrever`.
- Resultado em textarea com botão `Copiar` (o texto sai literal) + tempo medido.

### COMPARAR
- Frase única + dois chips de motor + `.duplo` com os dois players e as medições (tempo, RTF, taxa, peso) em `.grade-cartoes`.

### AGENTE
- Passos numerados (1 ligar, 2 copiar o comando, 3 usar no agente), campo de cliente e perfil, botão `Ligar`/`Desligar`, e o bloco de comando pronto para colar.

### CONFIGURACAO
- `.grade-cartoes` com portas, pastas, espaço livre, estado da base, motor ativo.
- Seletor de tema (`estudio` / `papel`).
- Botão `Abrir pasta de saídas` (chama `/api/saidas/abrir`).
- Lista de licenças por motor.

## 7. Regras duras para quem executa

1. `window.AREAS.push({ id, titulo, montar })` continua sendo o contrato (o `web/app.js` aceita lista e objeto).
2. Nada de framework, nada de npm, nada de CDN obrigatório: HTML puro. Fonte por CDN com fallback.
3. Todo JS tem que passar `node --check` (há teste no pytest que roda isso).
4. `[hidden] { display: none !important; }` fica no CSS (as áreas usam grid e venceriam o atributo).
5. Texto sempre em português do Brasil, zero travessão, zero hífen como pontuação.
6. Nada de caminho absoluto chumbado, nada de segredo, nada de nuvem.
7. Contraste: no tema `papel` usar `#0a0a0a` sobre `#fdfcfc`; no tema `estudio` usar `#f5efe8` sobre `#050510`.
8. `prefers-reduced-motion` respeitado, foco visível em todo campo e botão.
9. Entregar com `pytest -q` verde (48 testes ou mais) e `ruff check app tests scripts` limpo.
