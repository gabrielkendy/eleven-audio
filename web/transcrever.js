window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "transcrever",
  titulo: "Transcrever",
  montar(raiz) {
    raiz.innerHTML = `
      <form class="compositor" data-form-transcrever>
        <label class="solte" data-solte>
          <strong>Solte um áudio ou vídeo aqui</strong>
          <span>ou clique para escolher</span>
          <small>MP3 WAV M4A FLAC MP4 MOV MKV WEBM</small>
          <input name="arquivo" type="file" accept=".mp3,.wav,.m4a,.flac,.mp4,.mov,.mkv,.webm,audio/*,video/*" required>
          <span data-arquivo>Nenhum arquivo escolhido</span>
        </label>
        <div class="linha-acao">
          <label class="chip">Idioma
            <select name="idioma">
              <option value="pt">Português</option>
              <option value="en">Inglês</option>
              <option value="es">Espanhol</option>
              <option value="auto">Auto</option>
            </select>
          </label>
          <button type="submit">Transcrever</button>
        </div>
      </form>
      <p class="aviso" role="status" data-estado>Escolha um arquivo para começar.</p>
      <section data-resultado hidden>
        <label class="campo-rotulo" for="resultado-transcrever">Texto transcrito</label>
        <textarea id="resultado-transcrever" readonly rows="12"></textarea>
        <div class="linha-acao">
          <span data-tempo></span>
          <button type="button" data-copiar>Copiar</button>
        </div>
      </section>
      <section>
        <h3>Últimas transcrições</h3>
        <div class="grade-cartoes" data-historico><p class="vazio">Carregando histórico...</p></div>
      </section>`;

    const form = raiz.querySelector("[data-form-transcrever]");
    const entrada = form.elements.arquivo;
    const solte = raiz.querySelector("[data-solte]");
    const estado = raiz.querySelector("[data-estado]");
    const resultado = raiz.querySelector("#resultado-transcrever");
    const historico = raiz.querySelector("[data-historico]");
    const botao = form.querySelector("button[type=submit]");
    const tempos = new Map();
    let arquivo;

    function escolher(novoArquivo) {
      arquivo = novoArquivo;
      raiz.querySelector("[data-arquivo]").textContent = arquivo?.name || "Nenhum arquivo escolhido";
    }

    async function ler(resposta) {
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || resposta.statusText);
      return corpo;
    }

    async function carregarHistorico() {
      try {
        const itens = await fetch("/api/transcricoes").then(ler);
        if (!itens.length) {
          historico.innerHTML = '<p class="vazio">Nenhuma transcrição ainda.</p>';
          return;
        }
        historico.replaceChildren(...itens.map((item) => {
          const cartao = document.createElement("article");
          const titulo = document.createElement("strong");
          const texto = document.createElement("p");
          const tempo = tempos.get(item.id) ?? item.duracao_transcricao_s;
          titulo.textContent = `${item.idioma_detectado || item.idioma || "Idioma não detectado"} · ${tempo == null ? "tempo não informado" : `${Number(tempo).toFixed(1).replace(".", ",")} s`}`;
          texto.textContent = item.texto_saida || item.texto || "Sem texto";
          cartao.append(titulo, texto);
          return cartao;
        }));
      } catch (erro) {
        historico.textContent = `Erro ao carregar o histórico: ${erro.message}`;
      }
    }

    entrada.addEventListener("change", () => escolher(entrada.files[0]));
    ["dragenter", "dragover"].forEach((evento) => solte.addEventListener(evento, (e) => {
      e.preventDefault();
      solte.dataset.arrastando = "sim";
    }));
    ["dragleave", "drop"].forEach((evento) => solte.addEventListener(evento, (e) => {
      e.preventDefault();
      delete solte.dataset.arrastando;
    }));
    solte.addEventListener("drop", (evento) => escolher(evento.dataTransfer.files[0]));

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      if (!arquivo) {
        estado.textContent = "Erro: escolha um arquivo de áudio ou vídeo.";
        return;
      }
      botao.disabled = true;
      estado.textContent = "Transcrevendo...";
      const inicio = performance.now();
      try {
        const dados = new FormData();
        dados.set("arquivo", arquivo, arquivo.name);
        dados.set("idioma", form.elements.idioma.value);
        const transcricao = await fetch("/api/transcrever", { method: "POST", body: dados }).then(ler);
        const segundos = (performance.now() - inicio) / 1000;
        tempos.set(transcricao.transcricao_id, segundos);
        resultado.value = transcricao.texto;
        raiz.querySelector("[data-tempo]").textContent = `Transcrição em ${segundos.toFixed(1).replace(".", ",")} s · idioma ${transcricao.idioma_detectado || "não informado"}`;
        raiz.querySelector("[data-resultado]").hidden = false;
        estado.textContent = "Transcrição pronta.";
        await carregarHistorico();
      } catch (erro) {
        estado.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
      }
    });

    raiz.querySelector("[data-copiar]").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(resultado.value);
        estado.textContent = "Texto copiado.";
      } catch (_) {
        resultado.focus();
        resultado.select();
        estado.textContent = "A cópia automática falhou. O texto foi selecionado para você copiar.";
      }
    });

    carregarHistorico();
  },
});
