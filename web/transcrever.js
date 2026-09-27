window.AREAS.push({
  id: "transcrever",
  titulo: "TRANSCREVER",
  montar(raiz) {
    raiz.innerHTML = `
      <form id="form-transcrever">
        <label>Áudio ou vídeo <input id="arquivo-transcrever" name="arquivo" type="file" accept="audio/*,video/*" required></label>
        <label>Idioma
          <select name="idioma"><option value="pt">Português</option><option value="en">Inglês</option><option value="es">Espanhol</option></select>
        </label>
        <button type="submit">Transcrever</button>
      </form>
      <p id="estado-transcrever" role="status">Selecione um arquivo para transcrever.</p>
      <label>Resultado <textarea id="resultado-transcrever" readonly></textarea></label>
      <button id="copiar-transcricao" type="button" disabled>Copiar</button>
      <h3>Últimas transcrições</h3>
      <p id="estado-historico" role="status">Carregando histórico...</p>
      <ul id="historico-transcricoes"></ul>`;

    const form = raiz.querySelector("#form-transcrever");
    const botao = form.querySelector("button");
    const estado = raiz.querySelector("#estado-transcrever");
    const resultado = raiz.querySelector("#resultado-transcrever");
    const copiar = raiz.querySelector("#copiar-transcricao");
    const estadoHistorico = raiz.querySelector("#estado-historico");
    const historico = raiz.querySelector("#historico-transcricoes");

    async function carregarHistorico() {
      estadoHistorico.textContent = "Carregando histórico...";
      try {
        const resposta = await fetch("/api/transcricoes");
        if (!resposta.ok) throw new Error((await resposta.json()).detail || resposta.statusText);
        const itens = await resposta.json();
        historico.replaceChildren(...itens.map((item) => {
          const linha = document.createElement("li");
          linha.textContent = `${item.criado_em} · ${item.idioma_detectado || "idioma não detectado"} · ${item.texto_saida}`;
          return linha;
        }));
        estadoHistorico.textContent = itens.length ? "" : "Nenhuma transcrição ainda.";
      } catch (erro) {
        estadoHistorico.textContent = `Erro ao carregar histórico: ${erro.message}`;
      }
    }

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      botao.disabled = true;
      copiar.disabled = true;
      estado.textContent = "Transcrevendo...";
      try {
        const resposta = await fetch("/api/transcrever", { method: "POST", body: new FormData(form) });
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.detail || resposta.statusText);
        resultado.value = dados.texto;
        copiar.disabled = false;
        estado.textContent = `Transcrição pronta. Idioma detectado: ${dados.idioma_detectado || "não informado"}.`;
        await carregarHistorico();
      } catch (erro) {
        estado.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
      }
    });

    copiar.addEventListener("click", async () => {
      await navigator.clipboard.writeText(resultado.value);
      estado.textContent = "Texto copiado.";
    });

    carregarHistorico();
  },
});
