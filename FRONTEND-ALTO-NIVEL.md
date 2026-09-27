# FRONTEND DE ALTO NÍVEL (onda 2)

> Origem: sistema de design do produto publicado que é a nossa base (`4-BASE-VOICESTUDIO/electron/src/renderer/src/styles/t3-theme.css` e `globals.css`), mais os componentes caros que ela já resolve: `WaveformPlayer.jsx`, `WaveformTimeline.jsx`, `GlobalAudioPlayer.jsx`, `CompareModal.jsx`, `AudioTrimmer.jsx`, `captureWaveform.js` e os `shared/components/*`.
> Objetivo: o nosso estúdio tem que parecer (e se comportar como) um produto de verdade, não um protótipo.

## 1. Tokens: alinhar ao produto publicado

Trocar a paleta solta por uma escala semântica, igual à do produto. Assim o estúdio e o app base parecem a mesma família, e qualquer tema futuro entra só mexendo nas variáveis.

```css
:root {
  --raio: 0.625rem;              /* 10 px, igual ao produto */
  --raio-sm: calc(var(--raio) - 4px);
  --raio-md: calc(var(--raio) - 2px);
  --raio-lg: var(--raio);
  --raio-xl: calc(var(--raio) * 1.4);
}

/* TEMA ESCURO = padrão do produto */
[data-tema="estudio"] {
  --fundo: #0a0a0a;                                   /* neutral-950 */
  --cartao: color-mix(in srgb, var(--fundo) 97%, #fff);/* superfície +3% de branco */
  --superficie-alta: color-mix(in srgb, var(--fundo) 94%, #fff);
  --texto: #f5f5f5;                                   /* neutral-100 */
  --texto-fraco: color-mix(in srgb, #737373 90%, #fff);
  --texto-tenue: #5c5c5c;
  --primaria: oklch(0.571 0.21 264);                  /* a ação do produto no escuro */
  --primaria-texto: #fff;
  --borda: rgb(255 255 255 / 6%);                     /* separação por borda, não por leite */
  --entrada: rgb(255 255 255 / 8%);
  --muted: rgb(255 255 255 / 3%);
  --acento-fundo: rgb(255 255 255 / 4%);
  --sucesso: #34d399; --aviso: #fbbf24; --erro: #f87171; --info: #60a5fa;
  --foco: var(--primaria);
}

/* TEMA CLARO = padrão do produto (zinc) */
[data-tema="papel"] {
  --fundo: #fafafa;                                   /* zinc-25 */
  --cartao: #ffffff;
  --texto: #27272a;                                   /* zinc-800 */
  --texto-fraco: #71717a;                             /* zinc-500 */
  --texto-tenue: #a1a1aa;
  --primaria: oklch(0.488 0.217 264);
  --primaria-texto: #fff;
  --borda: #e4e4e7; --entrada: #d4d4d8;
  --muted: #fafafa; --acento-fundo: #f4f4f5;
  --sucesso: #10b981; --aviso: #f59e0b; --erro: #ef4444; --info: #3b82f6;
  --foco: var(--primaria);
}
```

Regras que vêm junto:
1. **Separação por borda de 1px a 6% e por hover a 4%, nunca por cinza leitoso.** O painel vive no mesmo tom do fundo; o que muda é a borda.
2. Fonte `Inter` (mesma do produto) com fallback de sistema. Números em tabela com `font-variant-numeric: tabular-nums`.
3. Foco sempre visível: `outline: 2px solid var(--foco)` com `outline-offset: 2px`.
4. `prefers-reduced-motion` desliga tudo.

## 2. Componentes caros para portar (sem framework, sem dependência)

### 2.1 Player com onda de verdade
Ler o WAV com a Web Audio API (`decodeAudioData`), reduzir para ~120 baldes de pico, desenhar em `<div>`s com altura proporcional. Mostrar: onda, botão redondo de play/pause, tempo atual e total, linha de progresso clicável para buscar, e as ações `Baixar WAV` e `Abrir pasta`.
- Desenhar a onda uma vez por arquivo e guardar o resultado em cache na memória por caminho.
- A onda precisa reagir ao clique: buscar a posição proporcional.
- Estado de carregando: barras em opacidade baixa pulsando.

### 2.2 Comparação A/B sincronizada
Dois players empilhados (A e B) com **um só controle de play**: ao tocar, os dois começam juntos; um botão de "trocar A com B" e um de "só A" / "só B" / "os dois". Medições em cartões: duração do áudio, tempo de geração, RTF, taxa em kHz e peso em KB, e uma frase dizendo qual ganhou em cada critério.
- Nada de dois players independentes: a graça é ouvir a mesma frase na mesma posição.

### 2.3 Player global fixo
Uma barra fina acima do rodapé que continua tocando quando você muda de área, com nome do arquivo, botão de play, tempo e a onda em miniatura. Toda geração nova alimenta esse player.

### 2.4 Seletor de voz com busca
Campo de busca que filtra por nome e por origem (`clonado`, `desenhado`), lista com avatar redondo (iniciais), chip de origem, botão de prévia e botão de usar. Navegação por seta para cima/baixo e Enter para escolher. Estado vazio que ensina: "você ainda não clonou nenhuma voz, comece pela área CLONAR".

### 2.5 Marcas de expressão com destaque
O editor conhece as marcas do motor (`GET /api/marcas?motor=X&texto=Y`): pinta a marca válida com a cor de sucesso e a inválida com a cor de erro, e mostra uma linha de aviso quando o motor não conhece a marca (ele falaria a marca em voz alta). A lista de marcas do motor aparece como botões que inserem no texto na posição do cursor.

### 2.6 Estados e acabamento
- Esqueleto de carregamento (blocos cinza pulsando) em vez de "carregando...".
- Aviso flutuante curto no canto para sucesso e erro, com fechar e tempo de 5 s.
- Estado vazio sempre com uma frase e um atalho, nunca uma tela morta.
- Erro curto, sem desculpa, com o motivo literal do motor.
- Foco e atalhos: `Ctrl+Enter` gera, `Ctrl+K` abre a paleta de comandos (trocar de área, escolher voz, gerar, abrir pasta), `Esc` fecha o que estiver aberto.

## 3. Divisão de arquivos (onda 2)

| Dono | Arquivos | Escopo |
|---|---|---|
| ONDA2-A | `web/estilo.css`, `web/index.html`, `web/app.js`, `web/onda.js` (novo), `tests/test_frontend_nivel.py` | tokens novos, player global fixo, paleta de comandos, avisos flutuantes, esqueleto de carregamento |
| ONDA2-B | `web/gerar.js`, `web/clonar.js`, `web/comparar.js`, `web/player.js` (novo), `tests/test_player.py` | player com onda real, comparação A/B sincronizada, seletor de voz com busca, marcas com destaque |

Regra: `web/player.js` é escrito por ONDA2-B e usado por quem quiser (`window.Player.criar(...)`); ONDA2-A não edita esse arquivo e ONDA2-B não edita o CSS nem o shell.

## 4. Prova obrigatória

1. `pytest -q` verde e `ruff check app tests scripts` limpo.
2. `node --check` em todo `web/*.js`.
3. Nascer com o app no ar e mostrar com curl que o HTML servido contém as classes novas.
4. Print da tela nova (o agente tira print do próprio servidor na porta dele, com um navegador headless se houver, ou descreve com precisão o que viu no `curl` do HTML).
5. Medição real: gerar um áudio e mostrar o tempo gasto contra a duração, antes e depois, para provar que o acabamento não deixou a tela lenta.
