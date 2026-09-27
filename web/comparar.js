window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "comparar",
  titulo: "COMPARAR",
  montar(raiz) {
    raiz.innerHTML = `
      <form class="compositor" data-form-comparar>
        <label class="campo-rotulo" for="comparar-texto">Uma frase, dois motores</label>
        <textarea id="comparar-texto" name="texto" maxlength="5000" rows="4" required>A mesma frase permite ouvir com clareza o resultado de cada motor.</textarea>
        <label class="campo-rotulo" for="comparar-perfil">Perfil salvo</label>
        <select id="comparar-perfil" name="perfil_id" required><option value="">Carregando perfis...</option></select>
        <div class="linha-acao">
          <label class="chip">A <select name="motor_a" required></select><small data-motivo-a></small></label>
          <label class="chip">B <select name="motor_b" required></select><small data-motivo-b></small></label>
          <button type="submit">Gerar comparação</button>
        </div>
      </form>
      <p class="aviso" role="status" data-estado>Nenhuma comparação gerada.</p>
      <section data-resultado hidden>
        <div class="duplo">
          <article>
            <h3 data-titulo-a>Motor A</h3>
            <div class="player">
              <button type="button" data-tocar="a" aria-label="Tocar ou pausar o áudio A">▶</button>
              <div class="onda" data-onda="a" aria-hidden="true"></div>
              <span data-tempo="a">0,0 s</span>
              <audio data-audio="a" preload="metadata"></audio>
            </div>
          </article>
          <article>
            <h3 data-titulo-b>Motor B</h3>
            <div class="player">
              <button type="button" data-tocar="b" aria-label="Tocar ou pausar o áudio B">▶</button>
              <div class="onda" data-onda="b" aria-hidden="true"></div>
              <span data-tempo="b">0,0 s</span>
              <audio data-audio="b" preload="metadata"></audio>
            </div>
          </article>
        </div>
        <div class="grade-cartoes" data-medicoes></div>
        <p class="aviso" data-resumo></p>
      </section>`;

    const form = raiz.querySelector("[data-form-comparar]");
    const estado = raiz.querySelector("[data-estado]");
    const botao = form.querySelector("button[type=submit]");
    let motores = [];

    raiz.querySelectorAll(".onda").forEach((onda, indice) => {
      onda.innerHTML = Array.from(
        { length: 28 },
        (_, i) => `<i style="height:${18 + (((i + indice * 5) * 19) % 72)}%"></i>`,
      ).join("");
    });

    async function ler(resposta) {
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || resposta.statusText);
      return corpo;
    }

    function preencherMotores() {
      [form.elements.motor_a, form.elements.motor_b].forEach((select) => {
        select.replaceChildren(...motores.map((motor) => new Option(
          motor.disponivel ? motor.nome : `${motor.nome} · indisponível`,
          motor.id,
        )));
      });
      form.elements.motor_a.value = motores.find((motor) => motor.id === "mock")?.id || motores[0]?.id || "";
      form.elements.motor_b.value = motores.find((motor) => motor.id !== form.elements.motor_a.value)?.id || "";
      mostrarMotivos();
    }

    function mostrarMotivos() {
      [["a", form.elements.motor_a], ["b", form.elements.motor_b]].forEach(([lado, select]) => {
        const motor = motores.find((item) => item.id === select.value);
        raiz.querySelector(`[data-motivo-${lado}]`).textContent = motor?.disponivel
          ? "disponível"
          : (motor?.motivo || "indisponível sem motivo informado");
      });
    }

    async function carregarOpcoes() {
      try {
        const [catalogo, perfis] = await Promise.all([
          fetch("/api/motores").then(ler),
          fetch("/api/perfis").then(ler),
        ]);
        motores = catalogo;
        preencherMotores();
        form.elements.perfil_id.replaceChildren(...perfis.map((perfil) => new Option(
          `${perfil.nome} · ${perfil.origem}`,
          perfil.id,
        )));
        if (!perfis.length) form.elements.perfil_id.append(new Option("Crie um perfil antes de comparar", ""));
      } catch (erro) {
        estado.textContent = `Erro ao carregar motores e perfis: ${erro.message}`;
      }
    }

    async function taxaKhz(url) {
      try {
        const bytes = await fetch(url).then((resposta) => resposta.arrayBuffer());
        if (bytes.byteLength < 28 || new TextDecoder().decode(bytes.slice(0, 4)) !== "RIFF") return null;
        return new DataView(bytes).getUint32(24, true) / 1000;
      } catch (_) {
        return null;
      }
    }

    function preencherPlayer(lado, item) {
      const audio = raiz.querySelector(`[data-audio="${lado}"]`);
      audio.src = item.audio_url;
      raiz.querySelector(`[data-titulo-${lado}]`).textContent = item.motor;
      raiz.querySelector(`[data-tempo="${lado}"]`).textContent = `${Number(item.duracao_audio_s).toFixed(1).replace(".", ",")} s`;
    }

    function cartao(item, taxa) {
      const rtf = Number(item.duracao_geracao_s) / Number(item.duracao_audio_s);
      const elemento = document.createElement("article");
      const titulo = document.createElement("h3");
      const medidas = document.createElement("p");
      titulo.textContent = item.motor;
      medidas.textContent = `Áudio ${Number(item.duracao_audio_s).toFixed(2)} s · geração ${Number(item.duracao_geracao_s).toFixed(2)} s · RTF ${rtf.toFixed(2)} · ${taxa == null ? "taxa não informada" : `${taxa.toFixed(1)} kHz`} · ${(Number(item.tamanho_bytes) / 1024).toFixed(1)} KB`;
      elemento.append(titulo, medidas);
      return elemento;
    }

    form.elements.motor_a.addEventListener("change", mostrarMotivos);
    form.elements.motor_b.addEventListener("change", mostrarMotivos);
    raiz.querySelectorAll("[data-tocar]").forEach((tocar) => {
      const audio = raiz.querySelector(`[data-audio="${tocar.dataset.tocar}"]`);
      tocar.addEventListener("click", () => {
        if (audio.paused) audio.play();
        else audio.pause();
      });
      audio.addEventListener("play", () => { tocar.textContent = "❚❚"; });
      audio.addEventListener("pause", () => { tocar.textContent = "▶"; });
    });

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      botao.disabled = true;
      estado.textContent = "Carregando os dois motores. A geração real pode demorar.";
      try {
        const comparacao = await fetch("/api/comparar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            texto: form.elements.texto.value,
            perfil_id: form.elements.perfil_id.value,
            motores: [form.elements.motor_a.value, form.elements.motor_b.value],
          }),
        }).then(ler);
        const [a, b] = comparacao.arquivos;
        preencherPlayer("a", a);
        preencherPlayer("b", b);
        const taxas = await Promise.all([taxaKhz(a.audio_url), taxaKhz(b.audio_url)]);
        raiz.querySelector("[data-medicoes]").replaceChildren(cartao(a, taxas[0]), cartao(b, taxas[1]));
        const rapido = Number(a.duracao_geracao_s) <= Number(b.duracao_geracao_s) ? a : b;
        const maiorTaxa = taxas.every((taxa) => taxa != null)
          ? (taxas[0] >= taxas[1] ? a.motor : b.motor)
          : "não foi possível medir";
        raiz.querySelector("[data-resumo]").textContent = `${rapido.motor} foi o mais rápido. Maior taxa: ${maiorTaxa}.`;
        raiz.querySelector("[data-resultado]").hidden = false;
        estado.textContent = "Comparação pronta.";
      } catch (erro) {
        estado.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
      }
    });

    carregarOpcoes();
  },
});
