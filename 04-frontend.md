# 04 · Frontend (a tela única)

> Arquivo 4 de 10 do manual. Aqui está a tela, componente por componente, com os estados que
> precisam existir e o endpoint que cada botão chama.
> Padrão do kit: estrutura, padrões de tela, estados de carregando, vazio e erro, e a seção de
> armadilhas. Adaptação importante: **sem login, sem tema de assinatura, sem cadeado.**

---

## 1. Estrutura de arquivos da tela

```text
estudio\web\
├── index.html            a pagina unica
├── src\
│   ├── principal.jsx      monta a tela e o rodape de estado
│   ├── api.js             cliente do nosso /api/* (um lugar so)
│   ├── areas\
│   │   ├── Gerar.jsx
│   │   ├── Clonar.jsx
│   │   ├── Desenhar.jsx
│   │   └── Transcrever.jsx
│   ├── blocos\
│   │   ├── RodapeEstado.jsx
│   │   ├── BlocoAgente.jsx
│   │   ├── SeletorMotor.jsx
│   │   ├── SeletorPerfil.jsx
│   │   └── Player.jsx
│   ├── textos\pt-br.js    TODO texto visivel em portugues mora aqui
│   └── estilo\
│       ├── tokens.css     cores, espacamento e tipografia por variavel
│       └── app.css
└── vite.config.js         (ou sem build, se for HTML puro)
```

Regra de ouro número 1 da tela: **todo texto visível está em `textos\pt-br.js`.** Nada de string
solta no componente. Isso dá revisão de texto para o vídeo e permite trocar de idioma depois sem
caça ao tesouro.

Regra de ouro número 2: **todo componente tem tela de esperando, vazio e erro.** Componente sem os
três é componente pela metade, e o vídeo não grava componente pela metade.

---

## 2. Anatomia da tela, área por área

### 2.1 Área GERAR (o coração)

| Componente | Comportamento | Endpoint |
|---|---|---|
| Caixa de texto | contador de caracteres, corte em 5.000, aceita quebra de linha | nenhum até gerar |
| Seletor de perfil | lista perfis com consentimento, com busca e estado vazio | `GET /api/perfis` |
| Seletor de motor | mostra disponível ou indisponível com motivo, e o tempo da última geração naquele motor | `GET /api/motores`, `POST /api/motores/ativo` |
| Seletor de idioma | padrão português, com atalho para auto | nenhum até gerar |
| Botão gerar | parado, gerando com etapa, pronto, erro | `POST /api/gerar`, `GET /api/gerar/{id}` |
| Player | tocar, baixar, abrir pasta | arquivo local |
| Faixa de comparação | guarda dois resultados (mesma frase, dois motores) e mostra lado a lado | `POST /api/gerar` duas vezes |

Estados exatos que a faixa de geração precisa cobrir:

```text
[ vazio ]        -> "escreva o texto e escolha a voz"
[ escrevendo ]   -> contador ativo
[ acima do teto] -> avisa e desabilita o botao
[ na fila ]      -> "na fila da GPU"
[ carregando ]   -> "carregando o motor (primeira vez baixa o peso)"
[ sintetizando ] -> barra de progresso com tempo decorrido
[ salvando ]     -> "salvando em saidas\audio"
[ pronto ]       -> player + tempo medido + caminho do arquivo
[ erro ]         -> motivo literal da base + o que fazer
```

### 2.2 Área CLONAR

| Componente | Comportamento | Endpoint |
|---|---|---|
| Nome do perfil | obrigatório, de 1 a 60 caracteres | nenhum até clonar |
| Entrada de clipe | subir arquivo ou gravar pelo microfone, com dica de 5 a 15 segundos | nenhum até clonar |
| Medidor do clipe | mostra a duração do arquivo escolhido e avisa se estiver fora da faixa | leitura local do arquivo |
| Campo de transcrição | opcional para a pessoa, obrigatório no nosso fluxo (a gente transcreve se ficar vazio) | `POST /api/transcrever` quando vazio |
| Aviso de consentimento | bloqueia o botão até responder (própria ou autorizada) | `POST /api/clonar` |
| Botão clonar | parado, clonando, pronto, erro | `POST /api/clonar` |
| Prévia comparativa | toca o clipe original e toca a voz clonada, um do lado do outro | arquivo local e `POST /api/gerar` |
| Lista de perfis | com botão de apagar e marca de consentimento | `GET /api/perfis`, `DELETE /api/perfis/{id}` |

Texto do aviso (o mesmo do PRD, sem alterar):

```text
Antes de clonar, confirme: esta voz e sua, ou voce tem autorizacao de quem e dono.
Clonar voz de terceiro sem autorizacao e ilegal e antiético.
O audio que voce gerar e seu, mas cada motor tem licenca propria. Leia antes de uso comercial.
```

### 2.3 Área DESENHAR

| Componente | Comportamento | Endpoint |
|---|---|---|
| Campo de descrição | texto livre, com exemplos prontos em português | nenhum até ouvir |
| Texto de prévia | o que a voz vai falar (padrão: uma frase de exemplo em português) | nenhum até ouvir |
| Seletor de motor | precisa avisar que desenho de voz depende do motor | `GET /api/motores` |
| Botão ouvir | gera prévia sem salvar como perfil | `POST /api/desenhar` |
| Botão salvar voz | transforma o desenho em perfil de voz | `POST /api/desenhar` com `salvar=true` |

Exemplos prontos que entram na tela (em português, sem marca de terceiro):

```text
narrador grave e calmo, ritmo pausado, para documentario
moça jovem, alegre, fala rapida, para anuncio curto
senhor idoso, voz baixa e rouca, para historia de suspense
voz neutra e clara, sem emoção, para leitura de texto tecnico
```

### 2.4 Área TRANSCREVER

| Componente | Comportamento | Endpoint |
|---|---|---|
| Entrada de arquivo | aceita áudio e vídeo comuns | nenhum até transcrever |
| Seletor de idioma | padrão detectar sozinho | nenhum até transcrever |
| Botão transcrever | parado, transcrevendo, pronto, erro | `POST /api/transcrever` |
| Resultado | caixa de texto com copiar e contagem de palavras | nenhum |
| Histórico | últimas transcrições com data e arquivo de origem | banco local |

### 2.5 Rodapé de estado (o que dá confiança no vídeo)

| Item mostrado | De onde vem | Por que importa |
|---|---|---|
| Motor ativo | `GET /api/estado` | a pessoa sabe o que está usando |
| Dispositivo (GPU ou CPU) com motivo | `GET /api/estado` | mata a dúvida "por que está lento" |
| Base no ar ou não | `GET /api/estado` | diagnóstico em um olhar |
| Tempo da última geração | banco local | número real para o vídeo |
| Espaço livre em disco | `GET /api/saude` | avisa antes de encher o disco |
| Pasta de saídas com botão de abrir | configuração | mostra que o arquivo é da pessoa |

### 2.6 Bloco AGENTE

| Componente | Comportamento | Endpoint |
|---|---|---|
| Identificador do agente | texto (ex.: `estudio`, `hermes`, `claude-code`) | nenhum até ligar |
| Seletor de perfil | voz que o agente vai usar | `GET /api/perfis` |
| Botão ligar | cria vínculo e confirma o MCP | `POST /api/agente/ligar` |
| Botão desligar | remove vínculo | `POST /api/agente/desligar` |
| Lista de vínculos | o que está ligado agora | `GET /api/agente/status` |
| Comando pronto | bloco copiável de configuração do agente | nenhum |

Exemplo do que a tela mostra pronto para copiar (Streamable HTTP):

```json
{
  "mcpServers": {
    "estudio": {
      "url": "http://127.0.0.1:3900/mcp/",
      "headers": { "X-OmniVoice-Client-Id": "estudio" }
    }
  }
}
```

---

## 3. Padrões de código da tela

### 3.1 Cliente único da API (um lugar para erro e base)

```javascript
// web/src/api.js
const BASE = "/api";

async function chamar(caminho, opcoes = {}) {
  const r = await fetch(`${BASE}${caminho}`, {
    headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
    ...opcoes,
  });
  if (!r.ok) {
    let motivo = `erro ${r.status}`;
    try {
      const corpo = await r.json();
      motivo = corpo.detail || motivo;
    } catch (e) { /* corpo vazio */ }
    throw new Error(motivo);
  }
  return r.status === 204 ? null : r.json();
}

export const api = {
  estado:      () => chamar("/estado"),
  motores:     () => chamar("/motores"),
  gerar:       (pedido) => chamar("/gerar", { method: "POST", body: JSON.stringify(pedido) }),
  andamento:   (id) => chamar(`/gerar/${id}`),
  perfis:      () => chamar("/perfis"),
  transcrever: (form) => chamar("/transcrever", { method: "POST", body: form }),
  agenteLigar: (dados) => chamar("/agente/ligar", { method: "POST", body: JSON.stringify(dados) }),
};
```

### 3.2 Acompanhar a geração sem travar a tela

```javascript
// dentro de Gerar.jsx
async function gerar() {
  setEtapa("na fila");
  const { geracao_id } = await api.gerar({ texto, perfil_id, motor, idioma, velocidade });
  const relogio = setInterval(async () => {
    const s = await api.andamento(geracao_id);
    setEtapa(s.etapa);
    if (s.etapa === "pronto" || s.etapa === "erro") {
      clearInterval(relogio);
      setResultado(s);
    }
  }, 1200);
}
```

Regra: intervalo curto de consulta, etapa sempre visível, e o botão volta a funcionar em qualquer
desfecho. Nunca deixe a tela em "carregando" sem etapa.

### 3.3 Cores e espaçamento por variável (nada de hex solto)

```css
/* web/src/estilo/tokens.css */
:root {
  --cor-fundo: #0f1115;
  --cor-painel: #171a21;
  --cor-texto: #e8eaee;
  --cor-texto-fraco: #9aa3b2;
  --cor-acento: #4f8cff;
  --cor-ok: #2ecc71;
  --cor-alerta: #f5a623;
  --cor-erro: #ff5c5c;
  --raio: 10px;
  --espaco-1: 4px; --espaco-2: 8px; --espaco-3: 16px; --espaco-4: 24px;
}
```

Um único lugar muda a cara do produto. Hex dentro de componente é proibido pelo mesmo motivo que
caminho absoluto é proibido no backend.

### 3.4 Acessibilidade mínima que não se negocia

1. Todo botão tem rótulo de texto ou `aria-label` em português.
2. Foco visível em todos os campos.
3. Contraste suficiente para leitura de texto pequeno.
4. A área de resultado é anunciada quando fica pronta (`aria-live="polite"`).
5. O player tem controle de teclado nativo (use o elemento `audio`).
6. Nenhuma informação é transmitida só por cor: o erro tem texto, não só cor.

---

## 4. Armadilhas de frontend (as que realmente acontecem)

| Problema | Sintoma | Solução |
|---|---|---|
| Origem diferente da base | tela abre e nada carrega, erro de cabeçalho de CORS | servir a tela pela nossa própria camada (mesma origem) e nunca apontar direto para a base |
| Porta 7800 ocupada por outro projeto | "abri e apareceu outro site" | checar porta antes de subir; trocar por variável |
| Build cacheado | mudança não aparece | confirmar o hash do arquivo de build que está sendo servido e recarregar sem cache |
| Texto longo sem contador | a pessoa escreve 8.000 caracteres e leva erro no fim | contador e corte em 5.000 com aviso na hora |
| Player sem botão de baixar | o arquivo existe e a pessoa não acha | botão de baixar e botão de abrir pasta no mesmo bloco |
| Erro genérico em inglês | a pessoa não sabe o que fazer | todo erro passa por tradução e mostra o motivo da base |
| Duas gerações ao mesmo tempo | erro de VRAM e lentidão | a tela desabilita o botão durante a fila e a nossa fila serializa |
| Acento quebrado no nome do arquivo | nome estranho na pasta | sanitizar nome para ASCII, mantendo data, motor e perfil |
| Recarregar a página no meio de uma geração | perde o progresso | guardar `geracao_id` e retomar a consulta ao abrir |
| Cadeado ou trava sem explicação | a pessoa acha que é bug | todo bloqueio tem frase em português com o motivo |

Exemplo de sanitização de nome de arquivo (com acento, o perigo é real):

```python
import re, unicodedata

def limpar_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_-]+", "_", sem_acento).strip("_")[:40] or "sem_nome"
```

---

## 5. Checklist de frontend (20 itens)

- [ ] Uma tela, quatro áreas, um rodapé, um bloco de agente
- [ ] Todo texto visível em português, vindo de um arquivo de textos
- [ ] Todo componente com estado de esperando, vazio e erro
- [ ] Todo botão chama um endpoint da lista do PRD
- [ ] Nenhum hex de cor dentro de componente
- [ ] Nenhum texto de marca de terceiro
- [ ] Seletor de motor mostra motivo quando indisponível
- [ ] Rodapé mostra motor ativo, dispositivo e tempo da última geração
- [ ] Contador de caracteres com corte em 5.000
- [ ] Player com tocar, baixar e abrir pasta
- [ ] Aviso de consentimento bloqueia a clonagem até responder
- [ ] Prévia comparativa funciona na clonagem
- [ ] Faixa de comparação de motores funciona com dois áudios
- [ ] Transcrição com botão copiar e contagem de palavras
- [ ] Bloco de agente com comando pronto para copiar
- [ ] Acessibilidade mínima da seção 3.4 cumprida
- [ ] Nenhuma requisição sai da máquina
- [ ] Recarregar a página não perde geração em andamento
- [ ] Erro sempre em português, com o motivo literal da base
- [ ] Tela abre em `127.0.0.1:7800` e não em endereço de rede
