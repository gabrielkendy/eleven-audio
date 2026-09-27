window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "desenhar",
  titulo: "DESENHAR",
  montar(raiz) {
    const exemplos = [
      "Uma narradora idosa, de voz grave e sotaque britanico.",
      "Um locutor jovem, de voz aguda e sotaque americano.",
      "Uma mulher adulta falando em sussurro.",
      "Um senhor de voz muito grave, calmo e acolhedor.",
    ];
    raiz.innerHTML = `
      <form data-form-desenhar>
        <label>Descreva a voz
          <textarea name="descricao" maxlength="2000" required></textarea>
        </label>
        <div data-exemplos></div>
        <label>Texto da previa
          <textarea name="texto_previa" maxlength="5000" required>A mesma frase permite comparar claramente as duas vozes desenhadas.</textarea>
        </label>
        <button type="submit">Ouvir</button>
        <p role="status" data-estado>Preencha a descricao para comecar.</p>
      </form>
      <audio controls data-player hidden></audio>
      <section aria-labelledby="desenhos-titulo">
        <h3 id="desenhos-titulo">Vozes desenhadas</h3>
        <div data-lista>Carregando vozes desenhadas...</div>
      </section>`;

    const form = raiz.querySelector("[data-form-desenhar]");
    const descricao = form.elements.descricao;
    const estado = raiz.querySelector("[data-estado]");
    const player = raiz.querySelector("[data-player]");
    const lista = raiz.querySelector("[data-lista]");
    const botao = form.querySelector("button[type=submit]");

    exemplos.forEach((texto) => {
      const exemplo = document.createElement("button");
      exemplo.type = "button";
      exemplo.textContent = texto;
      exemplo.addEventListener("click", () => {
        descricao.value = texto;
        descricao.focus();
      });
      raiz.querySelector("[data-exemplos]").append(exemplo);
    });

    async function ler(resposta) {
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || "A base nao respondeu.");
      return corpo;
    }

    async function atualizarLista() {
      lista.textContent = "Carregando vozes desenhadas...";
      try {
        const vozes = await fetch("/api/desenhos").then(ler);
        if (!vozes.length) {
          lista.textContent = "Nenhuma voz desenhada ainda.";
          return;
        }
        lista.replaceChildren(...vozes.map((voz) => {
          const item = document.createElement("p");
          item.textContent = `${voz.nome} · ${voz.total_geracoes} previa(s)`;
          return item;
        }));
      } catch (erro) {
        lista.textContent = `Erro ao carregar as vozes: ${erro.message}`;
      }
    }

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      botao.disabled = true;
      botao.textContent = "Desenhando e gerando...";
      estado.textContent = "Carregando o motor e criando a previa. O primeiro uso pode demorar.";
      try {
        const resultado = await fetch("/api/desenhar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            descricao: descricao.value,
            texto_previa: form.elements.texto_previa.value,
            motor: "voxcpm2",
          }),
        }).then(ler);
        player.src = `/${resultado.arquivo}`;
        player.hidden = false;
        estado.textContent = `Pronto em ${resultado.duracao_geracao_s}s. Audio de ${resultado.duracao_audio_s}s.`;
        await player.play();
        await atualizarLista();
      } catch (erro) {
        estado.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
        botao.textContent = "Ouvir";
      }
    });

    atualizarLista();
  },
});
