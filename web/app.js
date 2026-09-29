const ORDEM_PADRAO = ["gerar", "clonar", "comparar", "desenhar", "transcrever", "agente", "config"];
const TEMAS = ["estudio", "papel"];
const ICONES = {
  gerar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13h2l2-5 4 11 3-8 2 4h3"/></svg>',
  clonar: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="12" height="12" rx="3"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  comparar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3 4 7l4 4M4 7h13a3 3 0 0 1 3 3v1M16 21l4-4-4-4m4 4H7a3 3 0 0 1-3-3v-1"/></svg>',
  desenhar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20Zm10-13 3 3"/></svg>',
  transcrever: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z"/><path d="M5 11v1a7 7 0 0 0 14 0v-1M12 19v3m-4 0h8"/></svg>',
  agente: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="6" width="16" height="13" rx="3"/><path d="M9 11h.01M15 11h.01M9 15h6M12 6V3"/></svg>',
  config: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></svg>',
};

function definirTema(nome, explicito = false) {
  const tema = TEMAS.includes(nome) ? nome : "papel";
  document.documentElement.dataset.tema = tema;
  document.querySelectorAll("[data-tema-opcao]").forEach((botao) => {
    botao.setAttribute("aria-pressed", String(botao.dataset.temaOpcao === tema));
  });
  try {
    localStorage.setItem("estudio:tema", tema);
    if (explicito) localStorage.setItem("estudio:tema-explicito", "1");
  } catch (_) {
    // O tema ainda funciona quando o navegador bloqueia armazenamento local.
  }
  return tema;
}

window.definirTema = definirTema;
try {
  const salvo = localStorage.getItem("estudio:tema");
  const explicito = localStorage.getItem("estudio:tema-explicito") === "1";
  const migrou = localStorage.getItem("estudio:tema-papel-v2") === "1";
  if (!explicito && salvo === "estudio" && !migrou) {
    localStorage.setItem("estudio:tema-papel-v2", "1");
    definirTema("papel");
  } else {
    definirTema(salvo || "papel");
  }
} catch (_) {
  definirTema("papel");
}

function listaDeAreas() {
  const bruto = window.AREAS || {};
  const itens = [];

  // Forma em lista: window.AREAS.push({ id, titulo, montar }).
  if (Array.isArray(bruto)) {
    bruto.forEach((area, indice) => {
      if (area && typeof area === "object") itens.push({ ...area, id: area.id || `area-${indice}` });
    });
  }

  // Forma em objeto: window.AREAS.gerar = { titulo, html, montar } (e tambem cobre a lista acima).
  Object.entries(bruto).forEach(([chave, area]) => {
    if (/^\d+$/.test(chave) || !area || typeof area !== "object") return;
    itens.push({ ...area, id: area.id || chave });
  });

  const posicao = (area) => {
    const ordem = area.ordem ?? ORDEM_PADRAO.indexOf(area.id) + 1;
    return ordem || 99;
  };

  return itens.sort((a, b) => posicao(a) - posicao(b));
}

function montarSeletorTema() {
  const area = document.querySelector("#config");
  if (!area || area.querySelector("[data-seletor-tema]")) return;
  const seletor = document.createElement("section");
  seletor.className = "config-licencas";
  seletor.dataset.seletorTema = "";
  seletor.innerHTML = `<h3>Aparência</h3><div class="tema-opcoes">
    <button type="button" data-tema-opcao="estudio">Estúdio</button>
    <button type="button" data-tema-opcao="papel">Papel</button>
  </div>`;
  seletor.addEventListener("click", (evento) => {
    const botao = evento.target.closest("[data-tema-opcao]");
    if (botao) definirTema(botao.dataset.temaOpcao, true);
  });
  area.prepend(seletor);
  definirTema(document.documentElement.dataset.tema);
}

function montarAreas() {
  const areas = listaDeAreas();
  const navegacao = document.querySelector("#navegacao");
  const destino = document.querySelector("#areas");
  const titulo = document.querySelector("#titulo-area");
  const sanfona = document.querySelector("#sanfona");

  // Seguro por construcao: titulo e html vem apenas dos nossos proprios arquivos web/*.js,
  // nunca de dado do usuario nem de resposta da base. Texto que vem de fora entra por textContent.
  navegacao.innerHTML = areas
    .map((area, indice) => `<button data-alvo="${area.id}" class="${indice === 0 ? "ativo" : ""}">${ICONES[area.id] || ""}<span>${area.titulo || area.id}</span></button>`)
    .join("");
  destino.innerHTML = areas
    .map((area, indice) => `<section id="${area.id}" class="painel" ${indice === 0 ? "" : "hidden"}>${area.html ? area.html() : ""}</section>`)
    .join("");

  areas.forEach((area) => area.montar?.(document.querySelector(`#${area.id}`)));
  montarSeletorTema();

  const mostrar = (id) => {
    const area = areas.find((item) => item.id === id);
    navegacao.querySelectorAll("button").forEach((item) => item.classList.toggle("ativo", item.dataset.alvo === id));
    // Só os paineis de primeiro nivel entram no liga/desliga. As secoes internas de cada
    // area (colunas, blocos, comparacao) tem o proprio hidden e nao podem ser mexidas aqui.
    destino.querySelectorAll(":scope > section").forEach((painel) => {
      painel.hidden = painel.id !== id;
    });
    if (titulo && area) titulo.textContent = area.titulo || area.id;
    document.title = `${area?.titulo || "Estúdio"} · Estúdio de Voz Local`;
    window.dispatchEvent(new CustomEvent("estudio:area-visivel", { detail: { id } }));
    if (matchMedia("(max-width: 900px)").matches) {
      document.body.classList.remove("menu-aberto");
      sanfona?.setAttribute("aria-expanded", "false");
    }
  };

  navegacao.addEventListener("click", (evento) => {
    const botao = evento.target.closest("button[data-alvo]");
    if (botao) mostrar(botao.dataset.alvo);
  });

  sanfona?.addEventListener("click", () => {
    const aberto = document.body.classList.toggle("menu-aberto");
    sanfona.setAttribute("aria-expanded", String(aberto));
  });

  if (areas[0]) mostrar(areas[0].id);
}

async function atualizarRodape() {
  const rodape = document.querySelector("#rodape");
  const resumo = document.querySelector("#resumo-status");
  const ponto = document.querySelector("#ponto-base");
  try {
    const resposta = await fetch("/api/estado");
    const estado = await resposta.json();
    if (!resposta.ok) throw new Error(estado.detail || "estado indisponível");
    const ultima = estado.tempo_ultima_geracao_s ?? estado.ultima_geracao_s;
    const ultimaCurta = Number.isFinite(Number(ultima)) ? `${Number(ultima).toFixed(2)} s` : null;
    const base = estado.base === "ok";
    ponto?.classList.toggle("erro", !base);
    if (resumo) resumo.textContent = `${base ? "base conectada" : "base fora"} · ${estado.dispositivo} · motor ${estado.motor_ativo}`;
    rodape.textContent = `Base ${estado.base} · ${estado.dispositivo} · motor ${estado.motor_ativo} · pasta ${estado.pasta_saidas}${ultimaCurta ? ` · última geração ${ultimaCurta}` : ""}`;
  } catch (erro) {
    ponto?.classList.add("erro");
    if (resumo) resumo.textContent = "estado indisponível";
    rodape.textContent = `Estado indisponível: ${erro.message}`;
  }
}

montarAreas();
atualizarRodape();
window.addEventListener("estudio:atualizar-estado", atualizarRodape);

// ---------------------------------------------------------------------------
// Conserto no arquivo nao chega em aba que ja estava aberta: o navegador nao
// busca o JS de novo. A pessoa abre pelo atalho, a aba velha esta la, e ela ve
// o defeito que a gente ja corrigiu. Aconteceu duas vezes seguidas.
//
// Aqui o app pergunta de tempo em tempo se a tela que esta no disco mudou. Se
// mudou, ele se recarrega sozinho. Assim nenhum conserto fica invisivel, e
// ninguem precisa saber o que e cache.
let versaoDaTela = null;

async function conferirVersao() {
  if (document.visibilityState === "hidden") return;
  try {
    const resposta = await fetch("/api/versao", { cache: "no-store" });
    if (!resposta.ok) return;
    const { versao } = await resposta.json();
    if (!versao) return;
    if (versaoDaTela === null) {
      versaoDaTela = versao;
      return;
    }
    if (versao !== versaoDaTela) location.reload();
  } catch (_) {
    // Sem resposta: o app segue funcionando com a tela que ja tem.
  }
}

conferirVersao();
setInterval(conferirVersao, 20000);
document.addEventListener("visibilitychange", conferirVersao);
window.addEventListener("focus", conferirVersao);
