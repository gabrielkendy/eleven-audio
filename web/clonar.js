window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "clonar",
  titulo: "CLONAR",
  montar(raiz) {
    raiz.innerHTML = `
      <form data-clonar-form>
        <label>Nome do perfil <input name="nome" maxlength="60" required></label>
        <label>Clipe de 5 a 15 segundos <input name="arquivo_referencia" type="file" accept="audio/*"></label>
        <button type="button" data-gravar>Gravar no navegador</button>
        <span data-duracao>Nenhum clipe selecionado.</span>
        <audio data-original controls hidden></audio>
        <label>Transcricao do clipe (opcional) <textarea name="transcricao"></textarea></label>
        <fieldset>
          <legend>Consentimento obrigatorio</legend>
          <p>Antes de clonar, confirme: esta voz e sua, ou voce tem autorizacao de quem e dono.<br>
          Clonar voz de terceiro sem autorizacao e ilegal e antiético.<br>
          O audio que voce gerar e seu, mas cada motor tem licenca propria. Leia antes de uso comercial.</p>
          <label><input type="radio" name="origem_voz" value="propria" required> A voz e minha</label>
          <label><input type="radio" name="origem_voz" value="autorizada"> Tenho autorizacao</label>
          <label><input type="checkbox" name="aceite_consentimento" required> Confirmo o aviso</label>
        </fieldset>
        <button type="submit">Clonar</button>
      </form>
      <p role="status" data-estado></p>
      <section data-previa hidden>
        <h3>Previa comparativa</h3>
        <p>Original</p><audio data-original-comparacao controls></audio>
        <label>Texto da voz clonada <input data-texto-previa value="Esta e uma previa da minha voz clonada."></label>
        <button type="button" data-gerar-previa>Gerar previa clonada</button>
        <audio data-clonada controls></audio>
      </section>
      <section><h3>Perfis</h3><div data-perfis>Carregando perfis...</div></section>`;

    const form = raiz.querySelector("[data-clonar-form]");
    const arquivo = form.elements.arquivo_referencia;
    const duracao = raiz.querySelector("[data-duracao]");
    const estado = raiz.querySelector("[data-estado]");
    const original = raiz.querySelector("[data-original]");
    const previa = raiz.querySelector("[data-previa]");
    const originalComparacao = raiz.querySelector("[data-original-comparacao]");
    let clipe;
    let perfilAtual;

    function mensagem(texto, erro = false) {
      estado.textContent = texto;
      estado.setAttribute("data-erro", erro ? "true" : "false");
    }

    function usarClipe(blob, nome = "gravacao.webm") {
      clipe = new File([blob], nome, { type: blob.type || "audio/webm" });
      const url = URL.createObjectURL(clipe);
      original.src = url;
      original.hidden = false;
      originalComparacao.src = url;
      const medidor = new Audio(url);
      medidor.addEventListener("loadedmetadata", () => {
        const segundos = medidor.duration;
        duracao.textContent = `${segundos.toFixed(2)} s medidos. ${segundos < 5 || segundos > 15 ? "Use um clipe de 5 a 15 s." : "Duracao valida."}`;
      });
    }

    arquivo.addEventListener("change", () => arquivo.files[0] && usarClipe(arquivo.files[0], arquivo.files[0].name));
    raiz.querySelector("[data-gravar]").addEventListener("click", async (evento) => {
      const botao = evento.currentTarget;
      if (botao.dataset.gravando) {
        botao._gravador.stop();
        return;
      }
      try {
        const fluxo = await navigator.mediaDevices.getUserMedia({ audio: true });
        const partes = [];
        const gravador = new MediaRecorder(fluxo);
        botao._gravador = gravador;
        botao.dataset.gravando = "sim";
        botao.textContent = "Parar gravacao";
        gravador.ondataavailable = ({ data }) => partes.push(data);
        gravador.onstop = () => {
          fluxo.getTracks().forEach((faixa) => faixa.stop());
          delete botao.dataset.gravando;
          botao.textContent = "Gravar no navegador";
          usarClipe(new Blob(partes, { type: gravador.mimeType }));
        };
        gravador.start();
      } catch (erro) {
        mensagem(`Erro ao acessar o microfone: ${erro.message}`, true);
      }
    });

    async function carregarPerfis() {
      const lista = raiz.querySelector("[data-perfis]");
      lista.textContent = "Carregando perfis...";
      try {
        const resposta = await fetch("/api/perfis");
        if (!resposta.ok) throw new Error((await resposta.json()).detail || resposta.statusText);
        const perfis = await resposta.json();
        if (!perfis.length) {
          lista.textContent = "Nenhum perfil. Clone uma voz para comecar.";
          return;
        }
        lista.replaceChildren(...perfis.map((perfil) => {
          const item = document.createElement("p");
          const texto = document.createElement("span");
          texto.textContent = `${perfil.nome} · ${perfil.consentimento_em ? "consentimento ativo" : "sem consentimento"} · ${perfil.total_geracoes} geracoes `;
          const apagar = document.createElement("button");
          apagar.type = "button";
          apagar.textContent = "Apagar";
          apagar.onclick = async () => {
            apagar.disabled = true;
            const resposta = await fetch(`/api/perfis/${encodeURIComponent(perfil.id)}`, { method: "DELETE" });
            if (resposta.ok) carregarPerfis();
            else mensagem(`Erro ao apagar: ${(await resposta.json()).detail}`, true);
          };
          item.append(texto, apagar);
          return item;
        }));
      } catch (erro) {
        lista.textContent = `Erro ao carregar perfis: ${erro.message}`;
      }
    }

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      if (!clipe) return mensagem("Escolha ou grave um clipe.", true);
      const dados = new FormData(form);
      dados.set("arquivo_referencia", clipe, clipe.name);
      mensagem("Clonando e salvando o consentimento...");
      try {
        const resposta = await fetch("/api/clonar", { method: "POST", body: dados });
        const corpo = await resposta.json();
        if (!resposta.ok) throw new Error(corpo.detail || resposta.statusText);
        perfilAtual = corpo.perfil_id;
        previa.hidden = false;
        mensagem("Perfil clonado. Gere a previa para comparar.");
        carregarPerfis();
      } catch (erro) {
        mensagem(`Erro ao clonar: ${erro.message}`, true);
      }
    });

    raiz.querySelector("[data-gerar-previa]").addEventListener("click", async () => {
      mensagem("Gerando previa clonada...");
      try {
        const resposta = await fetch("/api/gerar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto: raiz.querySelector("[data-texto-previa]").value, perfil_id: perfilAtual, idioma: "pt" }),
        });
        const corpo = await resposta.json();
        if (!resposta.ok) throw new Error(corpo.detail || resposta.statusText);
        raiz.querySelector("[data-clonada]").src = corpo.audio_url || corpo.arquivo;
        mensagem("Previa pronta.");
      } catch (erro) {
        mensagem(`Erro ao gerar previa: ${erro.message}`, true);
      }
    });

    carregarPerfis();
  },
});
