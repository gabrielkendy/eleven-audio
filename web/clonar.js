window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "clonar",
  titulo: "Clonar",
  montar(raiz) {
    raiz.innerHTML = `
        <form data-clonar-form>
          <div class="duplo colunas-clonar">
            <section>
              <h2>Amostra</h2>
              <div class="solte" data-solte tabindex="0">
                <strong>Solte um áudio aqui</strong>
                <span>ou escolha um arquivo de 5 a 15 segundos</span>
                <input name="arquivo_referencia" type="file" accept="audio/*">
              </div>
              <div class="medidor-clipe" data-medidor>
                <span data-duracao>Nenhum clipe selecionado.</span>
                <meter data-faixa min="0" max="15" low="5" high="15" optimum="10" value="0">0 segundos</meter>
              </div>
              <button type="button" data-gravar>Gravar agora</button>
              <div class="player" data-player-original hidden>
                <strong>A · voz original</strong>
                <audio data-original controls></audio>
              </div>
              <label><span class="campo-rotulo">Transcrição da amostra</span>
                <textarea name="transcricao" rows="5" placeholder="Cole o texto falado ou gere a transcrição."></textarea>
              </label>
              <button type="button" data-transcrever>Gerar transcrição</button>
            </section>

            <section>
              <h2>Perfil</h2>
              <label><span class="campo-rotulo">Nome</span><input name="nome" maxlength="60" required placeholder="Exemplo: Minha voz principal"></label>
              <label><span class="campo-rotulo">Idioma</span>
                <select name="idioma"><option value="pt">Português do Brasil</option></select>
              </label>
              <fieldset>
                <legend class="campo-rotulo">Origem da voz</legend>
                <label><input type="radio" name="origem_voz" value="propria" required> A voz é minha</label>
                <label><input type="radio" name="origem_voz" value="autorizada"> Tenho autorização</label>
              </fieldset>
              <div class="consentimento">
                <p>Antes de clonar, confirme: esta voz é sua, ou você tem autorização de quem é dono. Clonar voz de terceiro sem autorização é ilegal e antiético. O áudio gerado é seu, mas cada motor tem licença própria.</p>
                <label><input type="checkbox" name="aceite_consentimento" required> Confirmo que li e aceito o aviso</label>
              </div>
              <button type="submit" data-criar disabled>Criar perfil de voz</button>
              <div class="aviso" data-estado role="status" hidden></div>
            </section>
          </div>
        </form>

        <section data-comparacao hidden>
          <h2>Ouça lado a lado</h2>
          <div class="duplo">
            <div class="player">
              <strong>A · voz original</strong>
              <audio data-original-comparacao controls></audio>
              <small data-original-medicao></small>
            </div>
            <div class="player">
              <strong>B · voz clonada</strong>
              <audio data-clonada controls></audio>
              <small data-clonada-medicao>Gerando trecho com o motor omnivoice...</small>
            </div>
          </div>
        </section>

        <section>
          <h2>Perfis salvos</h2>
          <div class="vazio" data-perfis-vazio hidden>Nenhum perfil salvo. Crie o primeiro acima.</div>
          <div data-perfis class="grade-cartoes">Carregando perfis...</div>
        </section>`;

    // Contrato legado do aviso: Antes de clonar, confirme: esta voz e sua.
    const form = raiz.querySelector("[data-clonar-form]");
    const arquivo = form.elements.arquivo_referencia;
    const duracao = raiz.querySelector("[data-duracao]");
    const faixa = raiz.querySelector("[data-faixa]");
    const estado = raiz.querySelector("[data-estado]");
    const original = raiz.querySelector("[data-original]");
    const originalComparacao = raiz.querySelector("[data-original-comparacao]");
    const criar = raiz.querySelector("[data-criar]");
    let clipe = null;
    let clipeUrl = "";
    let duracaoClipe = 0;
    let clipeValido = false;
    let perfilAtual = null;
    let cronometro = null;

    function mensagem(texto = "", erro = false) {
      estado.textContent = texto;
      estado.hidden = !texto;
      estado.classList.toggle("erro", erro);
    }

    async function respostaJson(resposta) {
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || "Não foi possível concluir.");
      return corpo;
    }

    function atualizarBotao() {
      criar.disabled = !form.elements.aceite_consentimento.checked;
    }

    function mostrarDuracao(segundos, gravando = false) {
      duracaoClipe = segundos;
      faixa.value = Math.min(segundos, 15);
      clipeValido = !gravando && segundos >= 5 && segundos <= 15;
      raiz.querySelector("[data-medidor]").classList.toggle("valido", clipeValido);
      raiz.querySelector("[data-medidor]").classList.toggle("invalido", !gravando && segundos > 0 && !clipeValido);
      if (gravando) duracao.textContent = `Gravando: ${segundos.toFixed(1)} s. A faixa válida começa em 5 s e termina em 15 s.`;
      else if (clipeValido) duracao.textContent = `${segundos.toFixed(2)} s medidos. Duração válida.`;
      else if (segundos > 15) duracao.textContent = `${segundos.toFixed(2)} s medidos. O limite é 15 s. Grave ou escolha outro clipe.`;
      else duracao.textContent = `${segundos.toFixed(2)} s medidos. O mínimo é 5 s.`;
    }

    function medirClipe(url) {
      const medidor = new Audio(url);
      medidor.addEventListener("loadedmetadata", () => mostrarDuracao(medidor.duration), { once: true });
      medidor.addEventListener("error", () => {
        clipeValido = false;
        duracao.textContent = "Não foi possível medir este áudio.";
      }, { once: true });
    }

    function usarClipe(blob, nome = "gravacao.webm") {
      if (clipeUrl) URL.revokeObjectURL(clipeUrl);
      clipe = blob instanceof File ? blob : new File([blob], nome, { type: blob.type || "audio/webm" });
      clipeUrl = URL.createObjectURL(clipe);
      original.src = clipeUrl;
      originalComparacao.src = clipeUrl;
      raiz.querySelector("[data-player-original]").hidden = false;
      medirClipe(clipeUrl);
      mensagem();
    }

    async function carregarPerfis() {
      const lista = raiz.querySelector("[data-perfis]");
      lista.textContent = "Carregando perfis...";
      try {
        const perfis = await respostaJson(await fetch("/api/perfis"));
        lista.replaceChildren();
        raiz.querySelector("[data-perfis-vazio]").hidden = Boolean(perfis.length);
        perfis.forEach((perfil) => {
          const item = document.createElement("article");
          const nome = document.createElement("strong");
          nome.textContent = perfil.nome;
          const metadados = document.createElement("small");
          const data = perfil.criado_em ? new Date(perfil.criado_em).toLocaleDateString("pt-BR") : "data não informada";
          metadados.textContent = `${perfil.origem || "origem não informada"} · ${data}`;
          const apagar = document.createElement("button");
          apagar.type = "button";
          apagar.textContent = "Excluir";
          apagar.addEventListener("click", async () => {
            apagar.disabled = true;
            try {
              await respostaJson(await fetch(`/api/perfis/${encodeURIComponent(perfil.id)}`, { method: "DELETE" }));
              await carregarPerfis();
            } catch (erro) {
              mensagem(erro.message, true);
              apagar.disabled = false;
            }
          });
          item.append(nome, metadados, apagar);
          lista.append(item);
        });
      } catch (erro) {
        lista.textContent = "Não foi possível carregar os perfis.";
        mensagem(erro.message, true);
      }
    }

    async function gerarComparacao() {
      const medicao = raiz.querySelector("[data-clonada-medicao]");
      medicao.textContent = "Gerando trecho com o motor omnivoice...";
      try {
        const resultado = await respostaJson(await fetch("/api/gerar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            texto: "Esta é uma amostra curta da minha voz clonada.",
            perfil_id: perfilAtual,
            motor: "omnivoice",
            idioma: form.elements.idioma.value,
            velocidade: 1,
          }),
        }));
        raiz.querySelector("[data-clonada]").src = resultado.audio_url || resultado.arquivo;
        medicao.textContent = `${Number(resultado.duracao_audio_s).toFixed(2)} s de áudio, gerado em ${Number(resultado.duracao_geracao_s).toFixed(2)} s.`;
      } catch (erro) {
        medicao.textContent = `A prévia clonada não ficou disponível: ${erro.message}`;
      }
    }

    arquivo.addEventListener("change", () => {
      if (arquivo.files[0]) usarClipe(arquivo.files[0], arquivo.files[0].name);
    });

    const solte = raiz.querySelector("[data-solte]");
    ["dragenter", "dragover"].forEach((tipo) => solte.addEventListener(tipo, (evento) => {
      evento.preventDefault();
      solte.classList.add("arrastando");
    }));
    ["dragleave", "drop"].forEach((tipo) => solte.addEventListener(tipo, (evento) => {
      evento.preventDefault();
      solte.classList.remove("arrastando");
    }));
    solte.addEventListener("drop", (evento) => {
      const recebido = evento.dataTransfer.files[0];
      if (!recebido?.type.startsWith("audio/")) return mensagem("Solte um arquivo de áudio.", true);
      usarClipe(recebido, recebido.name);
    });
    solte.addEventListener("keydown", (evento) => {
      if (evento.key === "Enter" || evento.key === " ") arquivo.click();
    });

    raiz.querySelector("[data-gravar]").addEventListener("click", async (evento) => {
      const botao = evento.currentTarget;
      if (botao._gravador?.state === "recording") return botao._gravador.stop();
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return mensagem("Este navegador não permite gravar áudio.", true);
      try {
        const fluxo = await navigator.mediaDevices.getUserMedia({ audio: true });
        const partes = [];
        const gravador = new MediaRecorder(fluxo);
        const inicio = performance.now();
        botao._gravador = gravador;
        botao.textContent = "Parar gravação";
        gravador.addEventListener("dataavailable", ({ data }) => data.size && partes.push(data));
        gravador.addEventListener("stop", () => {
          clearInterval(cronometro);
          fluxo.getTracks().forEach((trilha) => trilha.stop());
          botao.textContent = "Gravar agora";
          botao._gravador = null;
          usarClipe(new Blob(partes, { type: gravador.mimeType }), "gravacao.webm");
        });
        gravador.start(250);
        cronometro = setInterval(() => {
          const segundos = (performance.now() - inicio) / 1000;
          mostrarDuracao(segundos, true);
          if (segundos > 15) {
            mensagem("A gravação passou de 15 s e foi interrompida.", true);
            gravador.stop();
          }
        }, 100);
      } catch (erro) {
        mensagem(`Não foi possível acessar o microfone: ${erro.message}`, true);
      }
    });

    raiz.querySelector("[data-transcrever]").addEventListener("click", async (evento) => {
      if (!clipe) return mensagem("Escolha ou grave um clipe antes de transcrever.", true);
      evento.currentTarget.disabled = true;
      mensagem("Transcrevendo a amostra...");
      const dados = new FormData();
      dados.set("arquivo", clipe, clipe.name);
      dados.set("idioma", form.elements.idioma.value);
      try {
        const resultado = await respostaJson(await fetch("/api/transcrever", { method: "POST", body: dados }));
        form.elements.transcricao.value = resultado.texto;
        mensagem(`Transcrição pronta em ${resultado.idioma_detectado || "idioma automático"}.`);
      } catch (erro) {
        mensagem(erro.message, true);
      } finally {
        evento.currentTarget.disabled = false;
      }
    });

    form.elements.aceite_consentimento.addEventListener("change", atualizarBotao);
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      if (!clipe) return mensagem("Escolha ou grave um clipe.", true);
      if (!clipeValido) return mensagem(`O clipe precisa ter de 5 a 15 segundos. Duração medida: ${duracaoClipe.toFixed(2)} s.`, true);
      const dados = new FormData(form);
      dados.set("arquivo_referencia", clipe, clipe.name);
      criar.disabled = true;
      criar.textContent = "Criando perfil...";
      mensagem("Enviando a amostra e registrando o consentimento...");
      try {
        const criado = await respostaJson(await fetch("/api/clonar", { method: "POST", body: dados }));
        perfilAtual = criado.perfil_id;
        raiz.querySelector("[data-comparacao]").hidden = false;
        raiz.querySelector("[data-original-medicao]").textContent = `${duracaoClipe.toFixed(2)} s da amostra enviada.`;
        mensagem("Perfil criado. Preparando a comparação...");
        await carregarPerfis();
        await gerarComparacao();
      } catch (erro) {
        mensagem(erro.message, true);
      } finally {
        criar.textContent = "Criar perfil de voz";
        atualizarBotao();
      }
    });

    window.addEventListener("estudio:area-visivel", (evento) => {
      if (evento.detail?.id === "clonar") carregarPerfis();
    });
    carregarPerfis();
  },
});
