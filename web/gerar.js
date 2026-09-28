window.AREAS.gerar = {
  titulo: "Gerar",
  ordem: 1,
  html() {
    return `
      <div class="rail">
        <div class="compositor">
          <div class="abas" role="tablist" aria-label="Áreas do estúdio">
            <button class="aba ativa" type="button" data-nav="gerar">Compor</button>
            <button class="aba" type="button" data-acao="historico">Histórico</button>
          </div>

          <div data-painel="compor">
            <div class="editor-gerar">
              <textarea data-campo="texto" maxlength="5000" rows="12" aria-label="Texto para gerar áudio" placeholder="Escreva o que a voz vai dizer..."></textarea>
              <small data-campo="contador">0 caracteres · ~0 s</small>
            </div>
            <div class="pílulas" aria-label="Pontos de partida">
              <button class="pílula" type="button" data-texto="Hoje eu quero narrar uma história que merece ser ouvida até o fim.">Narrar um trecho</button>
              <button class="pílula" type="button" data-texto="No vídeo de hoje, você vai descobrir como transformar uma ideia em resultado.">Abrir o vídeo</button>
              <button class="pílula" type="button" data-texto="Em trinta segundos, aqui está o que você precisa saber para começar.">Explicar em 30 segundos</button>
              <button class="pílula" type="button" data-texto="Conheça uma forma mais simples de dar voz aos seus projetos.">Ler um anúncio</button>
              <button class="pílula" type="button" data-texto="Se este conteúdo ajudou, compartilhe e continue acompanhando os próximos passos.">Encerrar com chamada</button>
            </div>
            <div class="linha-acao">
              <div class="chips-gerar">
                <button class="chip" type="button" data-acao="ajustes" aria-expanded="true">
                  <span class="avatar avatar-chip" aria-hidden="true">M</span>
                  <span><strong data-campo="motor-chip">Motor </strong><small data-campo="motor-dispositivo">carregando</small></span>
                  <span class="pastilha" data-campo="motor-estado">...</span>
                </button>
                <button class="chip" type="button" data-acao="focar-vozes">
                  <span class="avatar avatar-chip" aria-hidden="true">V</span>
                  <span><strong data-campo="voz-chip">Voz padrão </strong><small data-campo="voz-origem">do motor</small></span>
                </button>
              </div>
              <button class="primario" type="button" data-acao="gerar">Gerar áudio Ctrl+Enter</button>
            </div>
          </div>

          <div data-painel="historico" hidden>
            <div class="vazio" data-historico-vazio>Suas últimas gerações vão aparecer aqui.</div>
            <div data-campo="historico"></div>
          </div>

          <div class="vazio" data-campo="vazio">Escreva um texto ou escolha um ponto de partida. Use Ctrl+Enter para gerar.</div>
          <div class="aviso" data-campo="aviso" role="alert" hidden></div>
          <div class="player" data-campo="player" hidden>
            <div class="onda" data-campo="onda">
              <audio data-campo="audio" controls></audio>
            </div>
            <span data-campo="tempo-player">0:00</span>
            <a data-campo="baixar" download>Baixar WAV</a>
            <button type="button" data-acao="abrir-pasta">Abrir pasta</button>
          </div>
        </div>

        <aside class="ajustes" data-campo="rail" aria-label="Ajustes de geração">
          <label><span class="campo-rotulo">Motor</span>
            <select data-campo="motor"><option>Carregando...</option></select>
          </label>
          <small class="motor-resumo" data-campo="motor-resumo"></small>
          <details><summary data-campo="catalogo-titulo">Outros motores</summary><div class="catalogo-motores" data-campo="catalogo"></div></details>
          <div>
            <label for="busca-voz-gerar" class="campo-rotulo">Voz</label>
            <input id="busca-voz-gerar" data-campo="busca-voz" type="search" placeholder="Buscar voz salva">
            <div data-campo="vozes" class="lista-vozes"></div>
          </div>
          <label class="slider"><span class="campo-rotulo">Velocidade <output data-campo="velocidade-valor">1,0x</output></span>
            <input data-campo="velocidade" type="range" min="0.5" max="2" step="0.1" value="1">
            <small>Mais lento</small><small>Mais rápido</small>
          </label>
          <label><span class="campo-rotulo">Acabamento</span>
            <select data-campo="qualidade">
              <option value="natural">Natural · sem efeito de rádio</option>
              <option value="detalhado">Detalhado · OmniVoice 64 passos</option>
              <option value="broadcast">Broadcast · voz processada</option>
            </select>
            <small>Mais passos não garantem maior semelhança.</small>
          </label>
          <label><span class="campo-rotulo">Semente fixa</span>
            <input data-campo="variacao" type="number" min="0" max="2147483647" step="1" value="2026">
            <small>Repete a condição aleatória. Não controla estabilidade.</small>
          </label>
          <details><summary>Qualidade da referência</summary><p data-campo="diagnostico">Selecione uma voz clonada.</p></details>
          <details>
            <summary>Marcas aceitas</summary>
            <p data-campo="marcas">Carregando...</p>
          </details>
        </aside>
      </div>`;
  },
  montar(area) {
    const campo = (nome) => area.querySelector(`[data-campo="${nome}"]`);
    const aviso = campo("aviso");
    const audio = campo("audio");
    const previaOriginal = new Audio();
    let gerando = false;
    let motores = [];
    let perfis = [];
    let perfilSelecionado = null;
    let ultimaGeracao = null;
    const nomesMotores = {omnivoice: "OmniVoice", "omnivoice-subprocess": "OmniVoice · isolado", voxcpm2: "VoxCPM2", kittentts: "KittenTTS · inglês", "chatterbox-ptbr": "Chatterbox V3 · PT-BR", cosyvoice: "CosyVoice 3", "mlx-audio": "MLX Audio · Mac", "moss-tts-nano": "MOSS Nano", "gpt-sovits": "GPT-SoVITS", "sherpa-onnx": "Sherpa ONNX", indextts2: "IndexTTS 2.5", "omnivoice-gguf": "OmniVoice GGUF", supertonic3: "Supertonic 3", "moss-tts-v15": "MOSS 1.5", "dots-tts": "Dots TTS", pockettts: "PocketTTS", "confucius4-tts": "Confucius4 TTS", audiocpp: "Audio.cpp"};
    const nomeMotor = (motor) => nomesMotores[motor.id] || motor.nome.split(" (")[0];

    async function api(caminho, opcoes = {}) {
      const resposta = await fetch(`/api${caminho}`, {
        headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
        ...opcoes,
      });
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || "Não foi possível concluir.");
      return corpo;
    }

    function mostrarAviso(mensagem = "") {
      aviso.textContent = mensagem;
      aviso.hidden = !mensagem;
    }

    function atualizarContador() {
      const total = campo("texto").value.length;
      const estimado = Math.ceil(total / 14);
      const real = ultimaGeracao ? ` · última medição ${Number(ultimaGeracao.duracao_audio_s).toFixed(1)} s` : "";
      campo("contador").textContent = `${total} caracteres · ~${estimado} s${real}`;
    }

    function atualizarMotor() {
      const motor = motores.find((item) => item.id === campo("motor").value);
      if (!motor) return;
      campo("motor-chip").textContent = nomeMotor(motor);
      const descricao = motor.id === "kittentts" ? "Somente inglês. Não clona sua voz." : motor.clonagem ? "Clonagem disponível. Selecione sua voz abaixo." : "Síntese de fala. Não oferece clonagem de voz.";
      campo("motor-resumo").textContent = motor.aviso_licenca ? `${descricao} ${motor.aviso_licenca}` : descricao;
      campo("motor-dispositivo").textContent = motor.dispositivo || "sem dispositivo";
      campo("motor-estado").textContent = motor.disponivel ? "instalado" : "indisponível";
      const detalhado = campo("qualidade").querySelector('[value="detalhado"]');
      detalhado.disabled = !motor.id.startsWith("omnivoice");
      if (detalhado.disabled && campo("qualidade").value === "detalhado") campo("qualidade").value = "natural";
      campo("velocidade").disabled = motor.id === "chatterbox-ptbr";
      if (campo("velocidade").disabled) { campo("velocidade").value = "1"; campo("velocidade-valor").textContent = "1,0x"; }
      campo("qualidade").disabled = motor.id === "chatterbox-ptbr";
    }

    async function atualizarMarcas() {
      try {
        const resultado = await api(`/marcas?motor=${encodeURIComponent(campo("motor").value)}`);
        campo("marcas").textContent = resultado.marcas.length ? resultado.marcas.join(", ") : "Este motor não expõe marcas de expressão.";
      } catch (erro) {
        campo("marcas").textContent = erro.message;
      }
    }

    function atualizarVoz() {
      campo("voz-chip").textContent = `${perfilSelecionado?.nome || "Voz padrão"} `;
      const origem = perfilSelecionado?.origem;
      campo("voz-origem").textContent = origem === "clonado" ? "Voz clonada" : origem === "desenhado" ? "Voz por descrição" : origem ? "Voz salva" : "do motor";
      area.querySelectorAll("[data-perfil-id]").forEach((item) => {
        item.classList.toggle("ativo", item.dataset.perfilId === perfilSelecionado?.id);
        const botao = item.querySelector("button");
        botao.textContent = item.dataset.perfilId === perfilSelecionado?.id ? "Selecionada ✓" : "Selecionar";
        botao.setAttribute("aria-pressed", String(item.dataset.perfilId === perfilSelecionado?.id));
      });
      try { if (perfilSelecionado) localStorage.setItem("estudio:perfil", perfilSelecionado.id); } catch (_) {}
    }

    async function diagnosticoVoz() {
      const id = perfilSelecionado?.id;
      campo("diagnostico").textContent = "Selecione uma voz clonada.";
      if (!id || perfilSelecionado.origem !== "clonado") return;
      try {
        const info = await api(`/perfis/${encodeURIComponent(id)}/qualidade`);
        if (perfilSelecionado?.id !== id) return;
        campo("diagnostico").textContent = `${info.duracao_s} s · pico ${info.pico_dbfs} dBFS · nível médio ${info.rms_dbfs} dBFS. ${info.avisos.join(" ") || "Sem alertas básicos de nível."} ${info.limite}`;
      } catch (erro) { if (perfilSelecionado?.id === id) campo("diagnostico").textContent = erro.message; }
    }

    function renderizarVozes() {
      const termo = campo("busca-voz").value.trim().toLocaleLowerCase("pt-BR");
      const filtrados = perfis.filter((perfil) => `${perfil.nome} ${perfil.origem}`.toLocaleLowerCase("pt-BR").includes(termo));
      const lista = campo("vozes");
      lista.replaceChildren();
      if (!filtrados.length) {
        const vazio = document.createElement("p");
        vazio.className = "vazio";
        vazio.textContent = perfis.length ? "Nenhuma voz encontrada." : "Nenhuma voz salva. Você ainda pode usar a voz padrão.";
        lista.append(vazio);
        return;
      }
      filtrados.forEach((perfil) => {
        const item = document.createElement("div");
        item.className = "voz-item";
        item.dataset.perfilId = perfil.id;
        const nome = document.createElement("strong");
        nome.textContent = perfil.nome;
        const origem = document.createElement("small");
        origem.textContent = perfil.origem === "clonado" ? "Voz clonada" : perfil.origem === "desenhado" ? "Voz por descrição" : "Voz salva";
        const usar = document.createElement("button");
        usar.type = "button";
        usar.textContent = "Usar esta voz";
        usar.addEventListener("click", () => {
          perfilSelecionado = perfil;
          atualizarVoz();
          diagnosticoVoz();
        });
        const tocar = document.createElement("button");
        tocar.type = "button";
        tocar.textContent = "Ouvir original";
        tocar.disabled = perfil.origem !== "clonado" || !perfil.audio_url;
        if (tocar.disabled) tocar.title = "Prévia original ainda não disponível neste servidor.";
        tocar.addEventListener("click", async () => {
          const previa = perfil.audio_url;
          if (!previa) return mostrarAviso("Esta voz ainda não tem prévia nesta sessão.");
          audio.pause();
          previaOriginal.src = previa;
          try { await previaOriginal.play(); } catch (_) { mostrarAviso("Não foi possível ouvir a referência original."); }
        });
        item.append(nome, origem, usar, tocar);
        lista.append(item);
      });
      atualizarVoz();
    }

    async function carregarPerfis() {
      perfis = await api("/perfis");
      if (!perfilSelecionado) {
        try { perfilSelecionado = perfis.find((item) => item.id === localStorage.getItem("estudio:perfil")) || null; } catch (_) {}
        perfilSelecionado ||= perfis.find((item) => item.origem === "clonado") || null;
      }
      if (perfilSelecionado) perfilSelecionado = perfis.find((item) => item.id === perfilSelecionado.id) || null;
      renderizarVozes();
      atualizarVoz();
      diagnosticoVoz();
    }

    function renderizarHistorico(itens) {
      const lista = campo("historico");
      lista.replaceChildren();
      area.querySelector("[data-historico-vazio]").hidden = Boolean(itens.length);
      itens.slice(0, 5).forEach((item) => {
        const linha = document.createElement("div");
        linha.className = "item-historico";
        const resumo = document.createElement("strong");
        resumo.textContent = `${item.motor}, ${Number(item.duracao_audio_s).toFixed(2)} s de áudio, ${Number(item.duracao_geracao_s || 0).toFixed(2)} s para gerar`;
        const caminho = document.createElement("small");
        caminho.textContent = item.arquivo_saida;
        linha.append(resumo, caminho);
        if (item.audio_url) {
          const ouvir = document.createElement("button");
          ouvir.type = "button";
          ouvir.textContent = "Ouvir e baixar";
          ouvir.onclick = () => { mostrarPlayer(item); audio.play().catch(() => mostrarAviso("Clique em reproduzir para ouvir.")); };
          linha.append(ouvir);
        }
        lista.append(linha);
      });
    }

    function mostrarPlayer(resultado) {
      previaOriginal.pause();
      const url = resultado.audio_url || resultado.arquivo;
      audio.src = url;
      campo("baixar").href = url;
      campo("tempo-player").textContent = `${Number(resultado.duracao_audio_s).toFixed(2)} s`;
      campo("player").hidden = false;
      campo("vazio").hidden = true;

    }

    async function carregar() {
      try {
        const [catalogo, estado, saidas] = await Promise.all([api("/motores"), api("/estado"), api("/saidas")]);
        motores = catalogo.filter((motor) => motor.id !== "mock");
        campo("motor").replaceChildren(...motores.filter((motor) => motor.disponivel).map((motor) => {
          const opcao = document.createElement("option");
          opcao.value = motor.id;
          opcao.disabled = !motor.disponivel;
          opcao.textContent = nomeMotor(motor);
          return opcao;
        }));
        const outros = motores.filter((motor) => !motor.disponivel);
        campo("catalogo-titulo").textContent = `Outros motores · ${outros.length} indisponíveis`;
        campo("catalogo").replaceChildren(...outros.map((motor) => {
          const artigo = document.createElement("article");
          const nome = document.createElement("strong");
          nome.textContent = nomeMotor(motor);
          const motivo = document.createElement("small");
          const texto = motor.motivo || "";
          motivo.textContent = /platform/i.test(texto) ? "Incompatível com este sistema." : /isn't installed/i.test(texto) ? "Pacote ainda não instalado." : /missing|unreadable/i.test(texto) ? "Faltam arquivos necessários." : "Requer instalação ou configuração adicional.";
          artigo.title = texto;
          artigo.append(nome, motivo);
          return artigo;
        }));
        const ativo = motores.find((motor) => motor.id === estado.motor_ativo && motor.disponivel) || motores.find((motor) => motor.disponivel);
        if (ativo) campo("motor").value = ativo.id;
        ultimaGeracao = saidas[0] || (estado.tempo_ultima_geracao_s ? { duracao_audio_s: estado.tempo_ultima_geracao_s } : null);
        atualizarMotor();
        await atualizarMarcas();
        atualizarContador();
        renderizarHistorico(saidas);
        await carregarPerfis();
      } catch (erro) {
        mostrarAviso(erro.message);
      }
    }

    async function gerar() {
      if (gerando) return;
      const texto = campo("texto").value.trim();
      if (!texto) return mostrarAviso("Escreva o texto do áudio.");
      const seed = Number(campo("variacao").value);
      if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647) return mostrarAviso("A semente deve ser um inteiro de 0 a 2147483647.");
      const motor = campo("motor").value;
      if (motor === "chatterbox-ptbr" && !perfilSelecionado) return mostrarAviso("Selecione sua voz clonada para usar o Chatterbox PT-BR.");
      const modo = campo("qualidade").value;
      const ajustes = motor === "chatterbox-ptbr" ? {} : modo === "broadcast"
        ? {effect_preset: "broadcast", postprocess_output: true, denoise: true}
        : {effect_preset: "raw", postprocess_output: false, denoise: false,
           ...(motor.startsWith("omnivoice") ? {num_step: modo === "detalhado" ? 64 : 32} : {})};
      gerando = true;
      const botao = area.querySelector("[data-acao='gerar']");
      botao.disabled = true;
      botao.textContent = "Gerando áudio…";
      mostrarAviso();
      try {
        const resultado = await api("/gerar", {
          method: "POST",
          body: JSON.stringify({
            texto,
            perfil_id: perfilSelecionado?.id || null,
            motor: campo("motor").value,
            idioma: "pt",
            velocidade: Number(campo("velocidade").value),
            semente: seed,
            ajustes,
          }),
        });
        ultimaGeracao = resultado;
        mostrarPlayer(resultado);
        atualizarContador();
        renderizarHistorico(await api("/saidas"));
        window.dispatchEvent(new Event("estudio:atualizar-estado"));
      } catch (erro) {
        mostrarAviso(erro.message);
      } finally {
        gerando = false;
        botao.disabled = false;
        botao.textContent = "Gerar áudio Ctrl+Enter";
      }
    }

    area.querySelectorAll("[data-nav]").forEach((aba) => aba.addEventListener("click", () => {
      document.querySelector(`#navegacao [data-alvo="${aba.dataset.nav}"]`)?.click();
    }));
    area.querySelector("[data-acao='historico']").addEventListener("click", (evento) => {
      area.querySelector("[data-painel='compor']").hidden = true;
      area.querySelector("[data-painel='historico']").hidden = false;
      area.querySelectorAll(".aba").forEach((aba) => aba.classList.toggle("ativa", aba === evento.currentTarget));
    });
    area.querySelector("[data-nav='gerar']").addEventListener("click", () => {
      area.querySelector("[data-painel='compor']").hidden = false;
      area.querySelector("[data-painel='historico']").hidden = true;
    });
    area.querySelectorAll(".pílula").forEach((botao) => botao.addEventListener("click", () => {
      campo("texto").value = botao.dataset.texto;
      atualizarContador();
      campo("texto").focus();
    }));
    campo("texto").addEventListener("input", atualizarContador);
    campo("texto").addEventListener("keydown", (evento) => {
      if ((evento.ctrlKey || evento.metaKey) && evento.key === "Enter") {
        evento.preventDefault();
        gerar();
      }
    });
    area.querySelector("[data-acao='gerar']").addEventListener("click", gerar);
    campo("busca-voz").addEventListener("input", renderizarVozes);
    area.querySelector("[data-acao='focar-vozes']").addEventListener("click", () => campo("busca-voz").focus());
    area.querySelector("[data-acao='ajustes']").addEventListener("click", (evento) => {
      campo("rail").hidden = !campo("rail").hidden;
      evento.currentTarget.setAttribute("aria-expanded", String(!campo("rail").hidden));
    });
    campo("velocidade").addEventListener("input", () => {
      campo("velocidade-valor").textContent = `${Number(campo("velocidade").value).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}x`;
    });
    audio.addEventListener("play", () => previaOriginal.pause());
    campo("motor").addEventListener("change", async () => {
      atualizarMotor();
      try {
        await api("/motores/ativo", { method: "POST", body: JSON.stringify({ motor: campo("motor").value }) });
        await atualizarMarcas();
        window.dispatchEvent(new Event("estudio:atualizar-estado"));
      } catch (erro) {
        mostrarAviso(erro.message);
      }
    });
    area.querySelector("[data-acao='abrir-pasta']").addEventListener("click", async () => {
      try {
        await api("/saidas/abrir", { method: "POST" });
      } catch (erro) {
        mostrarAviso(erro.message);
      }
    });
    window.addEventListener("estudio:area-visivel", (evento) => {
      if (evento.detail?.id === "gerar") carregarPerfis().catch((erro) => mostrarAviso(erro.message));
    });

    carregar();
  },
};
