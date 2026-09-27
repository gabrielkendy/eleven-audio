const ORDEM_PADRAO = ["gerar", "clonar", "comparar", "desenhar", "transcrever", "agente", "config"];

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

function montarAreas() {
  const areas = listaDeAreas();
  const navegacao = document.querySelector("#navegacao");
  const destino = document.querySelector("#areas");
  const titulo = document.querySelector("#titulo-area");

  // Seguro por construcao: titulo e html vem apenas dos nossos proprios arquivos web/*.js,
  // nunca de dado do usuario nem de resposta da base. Texto que vem de fora entra por textContent.
  navegacao.innerHTML = areas
    .map((area, indice) => `<button data-alvo="${area.id}" class="${indice === 0 ? "ativo" : ""}">${area.titulo || area.id}</button>`)
    .join("");
  destino.innerHTML = areas
    .map((area, indice) => `<section id="${area.id}" class="painel" ${indice === 0 ? "" : "hidden"}>${area.html ? area.html() : ""}</section>`)
    .join("");

  areas.forEach((area) => area.montar?.(document.querySelector(`#${area.id}`)));

  const mostrar = (id) => {
    const area = areas.find((item) => item.id === id);
    navegacao.querySelectorAll("button").forEach((item) => item.classList.toggle("ativo", item.dataset.alvo === id));
    destino.querySelectorAll("section").forEach((painel) => {
      painel.hidden = painel.id !== id;
    });
    if (titulo && area) titulo.textContent = area.titulo || area.id;
    document.title = `${area?.titulo || "Estúdio"} · Estúdio de Voz Local`;
    window.dispatchEvent(new CustomEvent("estudio:area-visivel", { detail: { id } }));
  };

  navegacao.addEventListener("click", (evento) => {
    const botao = evento.target.closest("button[data-alvo]");
    if (botao) mostrar(botao.dataset.alvo);
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
