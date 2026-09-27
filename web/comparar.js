window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "comparar",
  titulo: "COMPARAR",
  montar(raiz) {
    raiz.innerHTML = `
      <section aria-labelledby="comparar-titulo">
        <h2 id="comparar-titulo">Comparar motores</h2>
        <label>Frase <textarea id="comparar-texto" maxlength="5000" rows="4"></textarea></label>
        <label>Perfil <input id="comparar-perfil" required></label>
        <div>
          <label>Motor A <input id="comparar-a" value="mock" required></label>
          <label>Motor B <input id="comparar-b" value="omnivoice" required></label>
        </div>
        <button id="comparar-gerar" type="button">Gerar comparação</button>
        <p id="comparar-estado" role="status">Nenhuma comparação gerada.</p>
        <div id="comparar-faixas" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem"></div>
      </section>`;

    const estado = raiz.querySelector("#comparar-estado");
    const faixas = raiz.querySelector("#comparar-faixas");
    raiz.querySelector("#comparar-gerar").addEventListener("click", async () => {
      estado.textContent = "Carregando os dois motores. A geração real pode demorar.";
      faixas.replaceChildren();
      try {
        const resposta = await fetch("/api/comparar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            texto: raiz.querySelector("#comparar-texto").value,
            perfil_id: raiz.querySelector("#comparar-perfil").value,
            motores: [raiz.querySelector("#comparar-a").value, raiz.querySelector("#comparar-b").value],
          }),
        });
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.detail || "Erro ao gerar comparação.");
        dados.arquivos.forEach((item) => {
          const faixa = document.createElement("article");
          faixa.innerHTML = `<h3></h3><audio controls></audio><p></p>`;
          faixa.querySelector("h3").textContent = item.motor;
          faixa.querySelector("audio").src = item.audio_url;
          faixa.querySelector("p").textContent = `${item.duracao_geracao_s.toFixed(2)} s para gerar · ${item.tamanho_bytes} bytes`;
          faixas.appendChild(faixa);
        });
        estado.textContent = "Comparação pronta.";
      } catch (erro) {
        estado.textContent = `Erro: ${erro.message}`;
      }
    });
  },
});
