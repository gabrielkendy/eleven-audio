const ORDEM_PADRAO = ["gerar", "clonar", "comparar", "desenhar", "transcrever", "agente", "config"];
const TEMAS = ["estudio", "papel"];

function definirTema(nome) {
  const tema = TEMAS.includes(nome) ? nome : "estudio";
  document.documentElement.dataset.tema = tema;
  document.querySelectorAll("[data-tema-opcao]").forEach((botao) => {
    botao.setAttribute("aria-pressed", String(botao.dataset.temaOpcao === tema));
  });
  try {
    localStorage.setItem("estudio:tema", tema);
  } catch (_) {
    // O tema ainda funciona quando o navegador bloqueia armazenamento local.
  }
  return tema;
}

window.definirTema = definirTema;
try {
  definirTema(localStorage.getItem("estudio:tema"));
} catch (_) {
  definirTema("estudio");
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
  seletor.innerHTML = `<h3>APARÊNCIA</h3><div class="tema-opcoes">
    <button type="button" data-tema-opcao="estudio">Estúdio</button>
    <button type="button" data-tema-opcao="papel">Papel</button>
  </div>`;
  seletor.addEventListener("click", (evento) => {
    const botao = evento.target.closest("[data-tema-opcao]");
    if (botao) definirTema(botao.dataset.temaOpcao);
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
    .map((area, indice) => `<button data-alvo="${area.id}" class="${indice === 0 ? "ativo" : ""}">${area.titulo || area.id}</button>`)
    .join("");
  destino.innerHTML = areas
    .map((area, indice) => `<section id="${area.id}" class="painel" ${indice === 0 ? "" : "hidden"}>${area.html ? area.html() : ""}</section>`)
    .join("");

  areas.forEach((area) => area.montar?.(document.querySelector(`#${area.id}`)));
  montarSeletorTema();

  const mostrar = (id) => {
    const area = areas.find((item) => item.id === id);
    navegacao.querySelectorAll("button").forEach((item) => item.classList.toggle("ativo", item.dataset.alvo === id));
    destino.querySelectorAll("section").forEach((painel) => {
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
    const base = estado.base === "ok";
    ponto?.classList.toggle("erro", !base);
    if (resumo) resumo.textContent = `${base ? "base conectada" : "base fora"} · ${estado.dispositivo} · motor ${estado.motor_ativo}`;
    rodape.textContent = `Base ${estado.base} · ${estado.dispositivo} · motor ${estado.motor_ativo} · pasta ${estado.pasta_saidas}${ultima ? ` · última geração ${ultima} s` : ""}`;
  } catch (erro) {
    ponto?.classList.add("erro");
    if (resumo) resumo.textContent = "estado indisponível";
    rodape.textContent = `Estado indisponível: ${erro.message}`;
  }
}

montarAreas();
atualizarRodape();
window.addEventListener("estudio:atualizar-estado", atualizarRodape);
