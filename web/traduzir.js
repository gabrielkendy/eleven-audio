window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "traduzir",
  titulo: "Traduzir",
  montar(raiz) {
    raiz.innerHTML = `
      <section class="bloco">
        <h3>Traduzir texto</h3>
        <p class="ajuda">
          Tradutor offline, 50 idiomas, roda na sua máquina sem enviar nada para fora.
          Pares que não existem direto passam pelo inglês.
        </p>
        <label class="campo-rotulo" for="texto-origem">Texto original</label>
        <textarea id="texto-origem" rows="6" placeholder="Cole ou escreva o texto aqui"></textarea>
        <div class="linha-acao">
          <label class="chip">De
            <select data-idioma-origem></select>
          </label>
          <button type="button" class="secundario" data-detectar>Detectar idioma</button>
          <span class="seta" aria-hidden="true">→</span>
          <label class="chip">Para
            <select data-idioma-destino></select>
          </label>
          <button type="button" data-traduzir>Traduzir</button>
        </div>
        <p class="aviso" role="status" data-estado-texto>Escolha os idiomas e clique em traduzir.</p>
        <section data-resultado-texto hidden>
          <label class="campo-rotulo" for="texto-traduzido">Texto traduzido</label>
          <textarea id="texto-traduzido" readonly rows="6"></textarea>
          <div class="linha-acao">
            <span data-detalhe-texto></span>
            <button type="button" class="secundario" data-copiar-traducao>Copiar</button>
            <button type="button" class="secundario" data-usar-no-gerar>Usar em Gerar</button>
          </div>
        </section>
      </section>

      <section class="bloco">
        <h3>Áudio para áudio</h3>
        <p class="ajuda">
          Entende o áudio, traduz e fala de novo <strong>na sua voz clonada</strong>.
          Exemplo: um áudio em português vira o mesmo conteúdo em inglês, na sua voz.
        </p>
        <label class="solte" data-solte-dub>
          <strong>Solte um áudio aqui</strong>
          <span>ou clique para escolher</span>
          <small>MP3 WAV M4A FLAC OGG MP4 MOV — até 50 MB</small>
          <input name="arquivo-dub" type="file" accept=".mp3,.wav,.m4a,.flac,.ogg,.mp4,.mov,audio/*,video/*">
          <span data-arquivo-dub>Nenhum arquivo escolhido</span>
        </label>
        <div class="linha-acao">
          <label class="chip">Áudio está em
            <select data-idioma-fonte-dub>
              <option value="">Detectar sozinho</option>
            </select>
          </label>
          <span class="seta" aria-hidden="true">→</span>
          <label class="chip">Vira
            <select data-idioma-destino-dub></select>
          </label>
          <label class="chip">Na voz de
            <select data-perfil-dub></select>
          </label>
        </div>
        <div class="linha-acao">
          <label class="chip">Motor
            <select data-motor-dub></select>
          </label>
          <button type="button" data-dublar>Dublar agora</button>
        </div>
        <p class="aviso" role="status" data-estado-dub>Escolha um áudio e o idioma de destino.</p>
        <section data-resultado-dub hidden>
          <audio data-player-dub controls></audio>
          <div class="linha-acao">
            <span data-detalhe-dub></span>
            <a data-baixar-dub download>Baixar o áudio</a>
          </div>
          <div class="colunas">
            <div>
              <label class="campo-rotulo">O que o áudio dizia</label>
              <textarea data-texto-original readonly rows="6"></textarea>
            </div>
            <div>
              <label class="campo-rotulo">O que foi falado, traduzido</label>
              <textarea data-texto-traduzido-falado readonly rows="6"></textarea>
            </div>
          </div>
        </section>
      </section>`;

    const seletores = [
      raiz.querySelector("[data-idioma-origem]"),
      raiz.querySelector("[data-idioma-destino]"),
      raiz.querySelector("[data-idioma-fonte-dub]"),
      raiz.querySelector("[data-idioma-destino-dub]"),
    ];
    const estadoTexto = raiz.querySelector("[data-estado-texto]");
    const estadoDub = raiz.querySelector("[data-estado-dub]");
    const entradaTexto = raiz.querySelector("#texto-origem");
    const saidaTexto = raiz.querySelector("#texto-traduzido");

    let traduzidoAtual = "";

    async function ler(resposta) {
      const corpo = await resposta.json().catch(() => ({}));
      if (!resposta.ok) throw new Error(corpo.detail || resposta.statusText);
      return corpo;
    }

    function descrever(dados) {
      const partes = [`${dados.origem_nome} → ${dados.destino_nome}`];
      if (dados.saltos > 1) partes.push(`passou pelo inglês (${dados.saltos} saltos)`);
      else partes.push("direto");
      return partes.join(" · ");
    }

    async function carregarIdiomas() {
      try {
        const dados = await fetch("/api/traduzir/idiomas").then(ler);
        const lista = dados.idiomas;
        seletores.forEach((seletor, indice) => {
          const manter = seletor.value;
          seletor.replaceChildren(...lista.map((item) => new Option(item.nome, item.codigo)));
          if (indice === 2) {
            // "Detectar sozinho" vai na frente, e o valor tem que ser forçado
            // depois: replaceChildren seleciona o primeiro item, e o prepend move
            // o ITEM selecionado, não o índice, então sem isto o campo abria em
            // "Albanês" (o primeiro alfabético) em vez de detecção automática.
            seletor.prepend(new Option("Detectar sozinho", ""));
            seletor.value = "";
          }
          if (manter) seletor.value = manter;
        });
        raiz.querySelector("[data-idioma-origem]").value = "pb";
        raiz.querySelector("[data-idioma-destino]").value = "en";
        raiz.querySelector("[data-idioma-destino-dub]").value = "en";
      } catch (erro) {
        estadoTexto.textContent = `Erro ao carregar os idiomas: ${erro.message}`;
      }
    }

    // Chatterbox é especializado em português do Brasil: só vale quando o
    // destino é português. Deixá-lo selecionado para dublar em inglês produziria
    // áudio errado sem avisar.
    const SO_PORTUGUES = new Set(["chatterbox-ptbr"]);
    const IDIOMAS_PT = new Set(["pt", "pb"]);
    let motoresDisponiveis = [];
    let motorAtivo = "";

    function preencherMotores() {
      const seletorMotor = raiz.querySelector("[data-motor-dub]");
      const destino = raiz.querySelector("[data-idioma-destino-dub]").value;
      const usaveis = motoresDisponiveis.filter(
        (m) => !SO_PORTUGUES.has(m.id) || IDIOMAS_PT.has(destino),
      );
      const anterior = seletorMotor.value;
      seletorMotor.replaceChildren(...usaveis.map((m) => new Option(m.nome, m.id)));
      if (!usaveis.length) {
        seletorMotor.append(new Option("Nenhum motor que clona disponível", ""));
        return;
      }
      // prefere o motor já ativo no estúdio, senão o anterior, senão o primeiro
      const preferido = [motorAtivo, anterior].find((id) => id && usaveis.some((m) => m.id === id));
      seletorMotor.value = preferido || usaveis[0].id;
    }

    async function carregarVozes() {
      try {
        const [perfis, motores, estado] = await Promise.all([
          fetch("/api/perfis").then(ler),
          fetch("/api/motores").then(ler),
          fetch("/api/estado").then(ler),
        ]);
        const seletorPerfil = raiz.querySelector("[data-perfil-dub]");
        const anteriores = seletorPerfil.value;
        seletorPerfil.replaceChildren(...perfis.map((p) => new Option(
          `${p.nome} · ${p.origem}`, p.id,
        )));
        if (!perfis.length) {
          seletorPerfil.append(new Option("Crie um perfil antes de dublar", ""));
        } else if (anteriores && perfis.some((p) => p.id === anteriores)) {
          seletorPerfil.value = anteriores;
        }

        motoresDisponiveis = motores.filter(
          (m) => m.id !== "mock" && m.clonagem && m.disponivel,
        );
        motorAtivo = estado.motor_ativo || "";
        preencherMotores();
      } catch (erro) {
        estadoDub.textContent = `Erro ao carregar vozes e motores: ${erro.message}`;
      }
    }

    // ---------- texto ----------
    raiz.querySelector("[data-detectar]").addEventListener("click", async (evento) => {
      const botao = evento.currentTarget;
      const texto = entradaTexto.value.trim();
      if (!texto) {
        estadoTexto.textContent = "Escreva algo para detectar o idioma.";
        return;
      }
      botao.disabled = true;
      estadoTexto.textContent = "Olhando o idioma...";
      try {
        const r = await fetch("/api/traduzir/detectar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto }),
        }).then(ler);
        if (r.detectado) {
          raiz.querySelector("[data-idioma-origem]").value = r.codigo;
          estadoTexto.textContent = `Idioma provável: ${r.nome}. Confira e troque se estiver errado.`;
        } else {
          estadoTexto.textContent = `Não consegui detectar (${r.motivo}). Escolha o idioma na mão.`;
        }
      } catch (erro) {
        estadoTexto.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
      }
    });

    raiz.querySelector("[data-traduzir]").addEventListener("click", async (evento) => {
      const botao = evento.currentTarget;
      const texto = entradaTexto.value.trim();
      if (!texto) {
        estadoTexto.textContent = "Escreva algo para traduzir.";
        return;
      }
      botao.disabled = true;
      estadoTexto.textContent = "Traduzindo...";
      const inicio = performance.now();
      try {
        const r = await fetch("/api/traduzir/texto", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            texto,
            origem: raiz.querySelector("[data-idioma-origem]").value,
            destino: raiz.querySelector("[data-idioma-destino]").value,
          }),
        }).then(ler);
        traduzidoAtual = r.texto;
        saidaTexto.value = r.texto;
        const segundos = ((performance.now() - inicio) / 1000).toFixed(1).replace(".", ",");
        raiz.querySelector("[data-detalhe-texto]").textContent =
          `${descrever(r)} · ${segundos} s${r.observacao ? " · " + r.observacao : ""}`;
        raiz.querySelector("[data-resultado-texto]").hidden = false;
        estadoTexto.textContent = "Traduzido.";
      } catch (erro) {
        estadoTexto.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
      }
    });

    raiz.querySelector("[data-copiar-traducao]").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(saidaTexto.value);
        estadoTexto.textContent = "Tradução copiada.";
      } catch (_) {
        saidaTexto.focus();
        saidaTexto.select();
        estadoTexto.textContent = "A cópia automática falhou. O texto foi selecionado.";
      }
    });

    raiz.querySelector("[data-usar-no-gerar]").addEventListener("click", () => {
      if (!traduzidoAtual) return;
      try {
        sessionStorage.setItem("texto-para-gerar", traduzidoAtual);
      } catch (_) { /* sem sessionStorage, o botão só não transporta */ }
      const aba = document.querySelector('[data-aba="gerar"], [data-area="gerar"]');
      if (aba) aba.click();
      estadoTexto.textContent = "Texto enviado para a aba Gerar.";
    });

    // ---------- áudio para áudio ----------
    const entradaDub = raiz.querySelector("[name=arquivo-dub]");
    const solteDub = raiz.querySelector("[data-solte-dub]");
    let arquivoDub;

    function escolherDub(novo) {
      arquivoDub = novo;
      raiz.querySelector("[data-arquivo-dub]").textContent =
        novo?.name || "Nenhum arquivo escolhido";
    }

    entradaDub.addEventListener("change", () => escolherDub(entradaDub.files[0]));

    // Trocar o idioma de destino reavalia quais motores podem falar aquele idioma
    raiz.querySelector("[data-idioma-destino-dub]").addEventListener("change", () => {
      preencherMotores();
    });
    ["dragenter", "dragover"].forEach((ev) => solteDub.addEventListener(ev, (e) => {
      e.preventDefault();
      solteDub.dataset.arrastando = "sim";
    }));
    ["dragleave", "drop"].forEach((ev) => solteDub.addEventListener(ev, (e) => {
      e.preventDefault();
      delete solteDub.dataset.arrastando;
    }));
    solteDub.addEventListener("drop", (e) => escolherDub(e.dataTransfer.files[0]));

    raiz.querySelector("[data-dublar]").addEventListener("click", async (evento) => {
      const botao = evento.currentTarget;
      if (!arquivoDub) {
        estadoDub.textContent = "Escolha um áudio para dublar.";
        return;
      }
      const perfil = raiz.querySelector("[data-perfil-dub]").value;
      if (!perfil) {
        estadoDub.textContent = "Escolha a voz que vai falar. Se não houver, crie um perfil em Clonar.";
        return;
      }
      botao.disabled = true;
      estadoDub.textContent = "Ouvindo o áudio, traduzindo e falando de novo. Isso leva um tempo...";
      const inicio = performance.now();
      try {
        const dados = new FormData();
        dados.set("arquivo", arquivoDub, arquivoDub.name);
        dados.set("destino", raiz.querySelector("[data-idioma-destino-dub]").value);
        dados.set("origem", raiz.querySelector("[data-idioma-fonte-dub]").value);
        dados.set("perfil_id", perfil);
        dados.set("motor", raiz.querySelector("[data-motor-dub]").value);
        const r = await fetch("/api/dublar", { method: "POST", body: dados }).then(ler);

        const player = raiz.querySelector("[data-player-dub]");
        player.src = `/api/audio?caminho=${encodeURIComponent(r.arquivo)}`;
        raiz.querySelector("[data-baixar-dub]").href = player.src;
        raiz.querySelector("[data-texto-original]").value = r.texto_original;
        raiz.querySelector("[data-texto-traduzido-falado]").value = r.texto_traduzido;
        const total = ((performance.now() - inicio) / 1000).toFixed(1).replace(".", ",");
        raiz.querySelector("[data-detalhe-dub]").textContent =
          `${r.origem_nome} → ${r.destino_nome} · ${r.pedacos} trecho(s) · ` +
          `${Number(r.duracao_audio_s).toFixed(1).replace(".", ",")} s de áudio · ${total} s no total` +
          (r.observacao ? ` · ${r.observacao}` : "");
        raiz.querySelector("[data-resultado-dub]").hidden = false;
        estadoDub.textContent = "Pronto. Ouça abaixo.";
      } catch (erro) {
        estadoDub.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
      }
    });

    carregarIdiomas();
    carregarVozes();
  },
});
