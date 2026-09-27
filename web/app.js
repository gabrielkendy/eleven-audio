function montarAreas() {
  const areas = Object.entries(window.AREAS)
    .sort(([, a], [, b]) => (a.ordem || 99) - (b.ordem || 99));
  const navegacao = document.querySelector("#navegacao");
  const destino = document.querySelector("#areas");

  navegacao.innerHTML = areas.map(([id, area], indice) =>
    `<button data-alvo="${id}" class="${indice === 0 ? "ativo" : ""}">${area.titulo}</button>`
  ).join("");
  destino.innerHTML = areas.map(([id, area], indice) =>
    `<section id="${id}" class="painel" ${indice === 0 ? "" : "hidden"}>${area.html()}</section>`
  ).join("");

  areas.forEach(([id, area]) => area.montar?.(document.querySelector(`#${id}`)));
  navegacao.addEventListener("click", (evento) => {
    const botao = evento.target.closest("button[data-alvo]");
    if (!botao) return;
    navegacao.querySelectorAll("button").forEach((item) =>
      item.classList.toggle("ativo", item === botao)
    );
    destino.querySelectorAll("section").forEach((painel) => {
      painel.hidden = painel.id !== botao.dataset.alvo;
    });
  });
}

async function atualizarRodape() {
  try {
    const resposta = await fetch("/api/estado");
    const estado = await resposta.json();
    if (!resposta.ok) throw new Error(estado.detail || "estado indisponível");
    document.querySelector("#rodape").textContent =
      `Base ${estado.base} · ${estado.dispositivo} · motor ${estado.motor_ativo} · última geração ${estado.tempo_ultima_geracao_s ?? "—"} s`;
  } catch (erro) {
    document.querySelector("#rodape").textContent = `Estado indisponível: ${erro.message}`;
  }
}

montarAreas();
atualizarRodape();
window.addEventListener("estudio:atualizar-estado", atualizarRodape);
