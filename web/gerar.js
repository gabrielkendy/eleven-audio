function urlAudioLocalSegura(valor) {
  if (!valor) return null;
  try {
    const url = new URL(valor, window.location.origin);
    if (url.origin !== window.location.origin || !["http:", "https:"].includes(url.protocol)) {
      return null;
    }
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_) {
    return null;
  }
}

window.AREAS.gerar = {
  titulo: "Gerar",
  ordem: 1,
  html() {
    return `
      <div class="rail">
        <div class="compositor">
          <div class="abas" role="group" aria-label="Áreas do estúdio">
            <button class="aba ativa" type="button" data-nav="gerar">Compor</button>
            <button class="aba" type="button" data-acao="config">Configurações</button>
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

          <div data-painel="config" hidden>
            <section class="painel-config" aria-label="Configurações da geração">
              <div class="config-cabecalho">
                <h3>Configurações da geração</h3>
                <small data-campo="config-resumo">carregando…</small>
              </div>
              <div class="config-linhas" data-campo="config-linhas"></div>
              <form class="config-form" data-campo="config-form">
                <label class="slider"><span class="campo-rotulo">Velocidade <output data-campo="config-velocidade-valor">1,0x</output></span>
                  <input data-campo="config-velocidade" type="range" min="0.5" max="2" step="0.1" value="1">
                  <small>Mais lento</small><small>Mais rápido</small>
                </label>
                <label><span class="campo-rotulo">Acabamento</span>
                  <select data-campo="config-modo">
                    <option value="natural">Natural · sem efeito de rádio</option>
                    <option value="detalhado">Detalhado · OmniVoice 64 passos</option>
                    <option value="broadcast">Broadcast · voz processada</option>
                  </select>
                </label>
                <label><span class="campo-rotulo">Semente fixa</span>
                  <input data-campo="config-semente" type="number" min="0" max="2147483647" step="1" value="2026">
                </label>
                <button class="primario" type="submit">Salvar como padrão</button>
                <small class="config-status" data-campo="config-status" role="status"></small>
              </form>
            </section>
          </div>

          <div data-painel="historico" hidden>
            <div data-vista="historico-lista">
              <div class="historico-topo">
                <input data-campo="busca-historico" type="search" placeholder="Histórico de pesquisa...">
                <div class="chips-filtro">
                  <button class="chip-filtro" type="button" data-filtro="voz" aria-pressed="false">+ Voz</button>
                  <button class="chip-filtro" type="button" data-filtro="modelo" aria-pressed="false">+ Modelo</button>
                </div>
              </div>
              <div class="vazio" data-historico-vazio>Suas últimas gerações vão aparecer aqui.</div>
              <div data-campo="historico"></div>
            </div>
            <div data-vista="historico-detalhe" data-campo="historico-detalhe" hidden></div>
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
    let historicoItens = [];
    let historicoBusca = "";
    const historicoFiltros = { voz: false, modelo: false };
    let configAtual = null;
    // Rótulos em português para o bloco "Configurações" do histórico, iguais aos
    // do painel da base, para a tela falar a mesma língua do resumo do backend.
    const ROTULOS_AJUSTES = { num_step: "Passos", guidance_scale: "Guia", position_temperature: "Expressividade", class_temperature: "Variação de classe", max_chunk_chars: "Bloco máximo", crossfade_ms: "Transição", denoise: "Limpeza de ruído", postprocess_output: "Corte de silêncio", pronounce: "Pronúncia", effect_preset: "Efeito" };
    const MODOS_QUALIDADE = { natural: "Natural · sem efeito de rádio", detalhado: "Detalhado · OmniVoice 64 passos", broadcast: "Broadcast · voz processada" };
    const LIGADO = { true: "ligada", false: "desligada" };
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
          const previa = urlAudioLocalSegura(perfil.audio_url);
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

    // ── Histórico e Configurações (mesmo desenho do ElevenLabs) ──────────────
    function linhasDaConfiguracao(config) {
      const linhas = [];
      const add = (rotulo, valor) => {
        if (valor === null || valor === undefined || valor === "") return;
        linhas.push([rotulo, String(valor)]);
      };
      add("Motor", config.motor_nome || config.motor);
      add("Voz", config.voz);
      if (config.velocidade !== null && config.velocidade !== undefined) {
        add("Velocidade", `${Number(config.velocidade).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}x`);
      }
      add("Idioma", config.idioma);
      add("Acabamento", config.modo ? MODOS_QUALIDADE[config.modo] || config.modo : null);
      for (const [chave, valor] of Object.entries(config.ajustes || {})) {
        const rotulo = ROTULOS_AJUSTES[chave] || chave;
        const texto = ["denoise", "postprocess_output", "pronounce"].includes(chave)
          ? (String(valor) === "true" ? "ligada" : "desligada")
          : String(valor);
        add(rotulo, texto);
      }
      if (config.preparo !== null && config.preparo !== undefined) {
        add("Preparo da referência", config.preparo ? "ligado" : "desligado");
      }
      add("Semente", config.semente);
      return linhas;
    }

    function montarLinhas(alvo, linhas) {
      alvo.replaceChildren();
      for (const [rotulo, valor] of linhas) {
        const linha = document.createElement("div");
        linha.className = "config-linha";
        const nome = document.createElement("span");
        nome.className = "config-rotulo";
        nome.textContent = rotulo;
        const conteudo = document.createElement("span");
        conteudo.className = "config-valor";
        conteudo.textContent = valor;
        linha.append(nome, conteudo);
        alvo.append(linha);
      }
    }

    function diaCurto(iso) {
      const data = iso ? new Date(iso) : null;
      return data && !Number.isNaN(data.getTime()) ? data.toLocaleDateString("pt-BR") : "sem data";
    }

    function rotuloDoDia(iso) {
      const hoje = new Date().toLocaleDateString("pt-BR");
      const ontem = new Date(Date.now() - 86400000).toLocaleDateString("pt-BR");
      const dia = diaCurto(iso);
      return dia === hoje ? "Hoje" : dia === ontem ? "Ontem" : dia;
    }

    function historicoFiltrado() {
      const termo = historicoBusca.trim().toLocaleLowerCase("pt-BR");
      const vozAtual = perfilSelecionado?.nome || "voz do motor";
      return historicoItens.filter((item) => {
        if (historicoFiltros.voz && (item.voz || "voz do motor") !== vozAtual) return false;
        if (historicoFiltros.modelo && item.motor !== campo("motor").value) return false;
        if (!termo) return true;
        return `${item.texto_entrada || ""} ${item.voz || ""} ${item.motor_nome || ""}`
          .toLocaleLowerCase("pt-BR")
          .includes(termo);
      });
    }

    function linhaDoHistorico(item) {
      const linha = document.createElement("button");
      linha.type = "button";
      linha.className = "item-historico";
      linha.dataset.geracaoId = item.id;
      const resumo = document.createElement("strong");
      resumo.textContent = (item.texto_entrada || "(sem texto)").split("\n")[0].slice(0, 96);
      const meta = document.createElement("small");
      const voz = item.voz || "voz do motor";
      const duracao = Number(item.duracao_audio_s || 0).toFixed(1);
      meta.textContent = `${voz} · ${item.quando} · ${duracao} s de áudio`;
      linha.append(resumo, meta);
      linha.addEventListener("click", () => abrirDetalhe(item));
      return linha;
    }

    function renderizarHistorico() {
      const lista = campo("historico");
      lista.replaceChildren();
      const vazio = area.querySelector("[data-historico-vazio]");
      const filtrados = historicoFiltrado();
      vazio.hidden = Boolean(filtrados.length);
      vazio.textContent = historicoItens.length
        ? "Nenhuma geração encontrada com esse filtro."
        : "Suas últimas gerações vão aparecer aqui.";
      let grupoAtual = null;
      filtrados.forEach((item) => {
        const grupo = rotuloDoDia(item.criado_em);
        if (grupo !== grupoAtual) {
          grupoAtual = grupo;
          const cabecalho = document.createElement("div");
          cabecalho.className = "grupo-dia";
          cabecalho.textContent = grupo;
          lista.append(cabecalho);
        }
        lista.append(linhaDoHistorico(item));
      });
    }

    async function carregarHistorico() {
      try {
        const resposta = await api("/historico?limite=50");
        historicoItens = resposta.itens || [];
      } catch (erro) {
        historicoItens = [];
        renderizarHistorico();
        const vazio = area.querySelector("[data-historico-vazio]");
        vazio.textContent = `Histórico indisponível: ${erro.message}`;
        return;
      }
      renderizarHistorico();
    }

    function abrirDetalhe(item) {
      const alvo = campo("historico-detalhe");
      const config = item.configuracao || {};
      alvo.replaceChildren();

      const voltar = document.createElement("button");
      voltar.type = "button";
      voltar.className = "voltar";
      voltar.textContent = "← Voltar para o histórico";
      voltar.addEventListener("click", () => {
        area.querySelector("[data-vista='historico-lista']").hidden = false;
        alvo.hidden = true;
      });

      const topo = document.createElement("div");
      topo.className = "detalhe-topo";
      const quandoTag = document.createElement("span");
      quandoTag.className = "chip-quando";
      quandoTag.textContent = item.quando;
      const identificador = document.createElement("small");
      identificador.className = "detalhe-id";
      identificador.textContent = `ID da geração: ${item.id}`;
      topo.append(quandoTag, identificador);

      const acoes = document.createElement("div");
      acoes.className = "detalhe-acoes";
      const tocar = document.createElement("button");
      tocar.type = "button";
      tocar.className = "primario";
      tocar.textContent = "▶ Reproduzir";
      const audioHistorico = urlAudioLocalSegura(item.audio_url);
      tocar.disabled = !audioHistorico;
      if (!audioHistorico) tocar.title = "O arquivo desta geração não está mais na pasta de saídas.";
      tocar.addEventListener("click", () => {
        mostrarPlayer(item);
        audio.play().catch(() => mostrarAviso("Clique em reproduzir para ouvir."));
      });
      const baixar = document.createElement("a");
      baixar.className = "secundario";
      baixar.textContent = "Baixar WAV";
      baixar.download = "";
      if (audioHistorico) baixar.href = audioHistorico;
      else {
        baixar.setAttribute("aria-disabled", "true");
        baixar.classList.add("desabilitado");
      }
      const restaurar = document.createElement("button");
      restaurar.type = "button";
      restaurar.className = "secundario";
      restaurar.textContent = "↻ Restaurar tudo";
      restaurar.addEventListener("click", () => restaurarTudo(item));
      acoes.append(tocar, baixar, restaurar);

      const bloco = document.createElement("section");
      bloco.className = "detalhe-config";
      const titulo = document.createElement("h4");
      titulo.textContent = "Configurações";
      const linhas = document.createElement("div");
      linhas.className = "config-linhas";
      const lista = linhasDaConfiguracao(config);
      if (lista.length) montarLinhas(linhas, lista);
      else {
        const nota = document.createElement("p");
        nota.className = "vazio";
        nota.textContent = "Esta geração é anterior ao registro das configurações.";
        linhas.append(nota);
      }
      bloco.append(titulo, linhas);

      const texto = document.createElement("section");
      texto.className = "detalhe-texto";
      const tituloTexto = document.createElement("h4");
      tituloTexto.textContent = "Texto";
      const paragrafo = document.createElement("p");
      paragrafo.textContent = item.texto_entrada || "";
      const medicao = document.createElement("small");
      medicao.textContent = `Áudio ${Number(item.duracao_audio_s || 0).toFixed(2)} s · gerado em ${Number(item.duracao_geracao_s || 0).toFixed(2)} s · ${(Number(item.tamanho_bytes || 0) / 1048576).toFixed(1)} MB`;
      texto.append(tituloTexto, paragrafo, medicao);

      alvo.append(voltar, topo, acoes, bloco, texto);
      area.querySelector("[data-vista='historico-lista']").hidden = true;
      alvo.hidden = false;
    }

    function restaurarTudo(item) {
      const config = item.configuracao || {};
      const motorAlvo = motores.find((motor) => motor.id === config.motor && motor.disponivel);
      if (motorAlvo) {
        campo("motor").value = config.motor;
        atualizarMotor();
      }
      if (config.velocidade !== null && config.velocidade !== undefined && !campo("velocidade").disabled) {
        campo("velocidade").value = config.velocidade;
        campo("velocidade-valor").textContent = `${Number(config.velocidade).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}x`;
      }
      if (config.modo) {
        const opcao = campo("qualidade").querySelector(`[value="${config.modo}"]`);
        if (opcao && !opcao.disabled) campo("qualidade").value = config.modo;
      }
      if (config.semente !== null && config.semente !== undefined) campo("variacao").value = config.semente;
      const voz = perfis.find((perfil) => perfil.id === config.perfil_id);
      if (voz) {
        perfilSelecionado = voz;
        atualizarVoz();
        diagnosticoVoz();
      }
      const textoVazio = !campo("texto").value.trim();
      if (textoVazio && item.texto_entrada) {
        campo("texto").value = item.texto_entrada;
        atualizarContador();
      }
      irPara("compor");
      mostrarAviso(`Configuração restaurada (${item.quando}): ${config.resumo || "padrão do motor"}${motorAlvo ? "" : " · motor original está indisponível agora"}.`);
    }

    async function carregarConfiguracoes() {
      try {
        configAtual = await api("/configuracoes");
      } catch (erro) {
        campo("config-status").textContent = erro.message;
        return;
      }
      montarLinhas(campo("config-linhas"), linhasDaConfiguracao(configAtual));
      campo("config-resumo").textContent = configAtual.resumo || "padrão do motor";
      campo("config-velocidade").value = configAtual.velocidade ?? 1;
      campo("config-velocidade-valor").textContent = `${Number(configAtual.velocidade ?? 1).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}x`;
      campo("config-modo").value = configAtual.modo || "natural";
      campo("config-semente").value = configAtual.semente ?? 2026;
      const indisponivel = configAtual.motor_disponivel === false;
      campo("config-status").textContent = indisponivel ? "O motor ativo não está disponível neste momento." : "";
    }

    function aplicarPadroesNaComposicao() {
      if (!configAtual) return;
      if (configAtual.velocidade !== null && configAtual.velocidade !== undefined && !campo("velocidade").disabled) {
        campo("velocidade").value = configAtual.velocidade;
        campo("velocidade-valor").textContent = `${Number(configAtual.velocidade).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}x`;
      }
      if (configAtual.modo) {
        const opcao = campo("qualidade").querySelector(`[value="${configAtual.modo}"]`);
        if (opcao && !opcao.disabled) campo("qualidade").value = configAtual.modo;
      }
      if (configAtual.semente !== null && configAtual.semente !== undefined) campo("variacao").value = configAtual.semente;
    }

    function irPara(painel) {
      const alvos = { compor: "compor", config: "config", historico: "historico" };
      for (const [chave, valor] of Object.entries(alvos)) {
        area.querySelector(`[data-painel='${valor}']`).hidden = chave !== painel;
      }
      // O aviso de "escreva um texto" é do compositor: nas outras abas ele
      // aparecia no meio da lista de histórico.
      campo("vazio").hidden = painel !== "compor" || Boolean(campo("texto").value.trim());
      area.querySelectorAll(".aba").forEach((aba) => {
        const ativa = painel === "compor" ? aba.dataset.nav === "gerar" : aba.dataset.acao === painel;
        aba.classList.toggle("ativa", ativa);
        aba.setAttribute("aria-selected", String(ativa));
      });
      if (painel === "historico") {
        area.querySelector("[data-vista='historico-lista']").hidden = false;
        campo("historico-detalhe").hidden = true;
        carregarHistorico().catch((erro) => mostrarAviso(erro.message));
      }
      if (painel === "config") carregarConfiguracoes();
    }

    function mostrarPlayer(resultado) {
      previaOriginal.pause();
      const url = urlAudioLocalSegura(resultado.audio_url);
      if (!url) {
        mostrarAviso("O endereço deste áudio é inválido ou não pertence ao estúdio.");
        return;
      }
      audio.src = url;
      campo("baixar").href = url;
      campo("tempo-player").textContent = `${Number(resultado.duracao_audio_s).toFixed(2)} s`;
      campo("player").hidden = false;
      campo("vazio").hidden = true;

    }

    async function carregar() {
      try {
        // O seletor de motor é a primeira coisa que o aluno olha. Ele NÃO depende
        // de /estado nem de /saidas, então vai sozinho, na frente. Antes os três
        // pedidos ficavam em fila no mesmo Promise.all e a tela passava segundos
        // em "Carregando...", o que parece travamento (foi o que aconteceu ao
        // abrir o app para testar).
        const catalogo = await api("/motores");
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
        const [estado, saidas] = await Promise.all([api("/estado"), api("/saidas")]);
        const ativo = motores.find((motor) => motor.id === estado.motor_ativo && motor.disponivel) || motores.find((motor) => motor.disponivel);
        if (ativo) campo("motor").value = ativo.id;
        ultimaGeracao = saidas[0] || (estado.tempo_ultima_geracao_s ? { duracao_audio_s: estado.tempo_ultima_geracao_s } : null);
        atualizarMotor();
        await atualizarMarcas();
        atualizarContador();
        await carregarHistorico();
        await carregarConfiguracoes();
        aplicarPadroesNaComposicao();
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
            modo,
            ajustes,
          }),
        });
        ultimaGeracao = resultado;
        mostrarPlayer(resultado);
        atualizarContador();
        await carregarHistorico();
        window.dispatchEvent(new Event("estudio:atualizar-estado"));
      } catch (erro) {
        mostrarAviso(erro.message);
      } finally {
        gerando = false;
        botao.disabled = false;
        botao.textContent = "Gerar áudio Ctrl+Enter";
      }
    }

    area.querySelectorAll("[data-nav]").forEach((aba) => {
      aba.addEventListener("click", () => {
        document.querySelector(`#navegacao [data-alvo="${aba.dataset.nav}"]`)?.click();
      });
    });
    area.querySelector("[data-acao='historico']").addEventListener("click", () => irPara("historico"));
    area.querySelector("[data-acao='config']").addEventListener("click", () => irPara("config"));
    area.querySelector("[data-nav='gerar']").addEventListener("click", () => irPara("compor"));
    campo("busca-historico").addEventListener("input", () => {
      historicoBusca = campo("busca-historico").value;
      renderizarHistorico();
    });
    area.querySelectorAll(".chip-filtro").forEach((chip) => {
      chip.addEventListener("click", () => {
        const nome = chip.dataset.filtro;
        historicoFiltros[nome] = !historicoFiltros[nome];
        chip.classList.toggle("ativo", historicoFiltros[nome]);
        chip.setAttribute("aria-pressed", String(historicoFiltros[nome]));
        renderizarHistorico();
      });
    });
    campo("config-velocidade").addEventListener("input", () => {
      campo("config-velocidade-valor").textContent = `${Number(campo("config-velocidade").value).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}x`;
    });
    campo("config-form").addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const status = campo("config-status");
      const semente = Number(campo("config-semente").value);
      if (!Number.isInteger(semente) || semente < 0 || semente > 2147483647) {
        status.textContent = "A semente deve ser um inteiro de 0 a 2147483647.";
        return;
      }
      try {
        configAtual = await api("/configuracoes", {
          method: "POST",
          body: JSON.stringify({
            velocidade: Number(campo("config-velocidade").value),
            modo: campo("config-modo").value,
            semente,
          }),
        });
        await carregarConfiguracoes();
        aplicarPadroesNaComposicao();
        status.textContent = "Padrão salvo. A próxima geração já usa estes ajustes.";
      } catch (erro) {
        status.textContent = erro.message;
      }
    });
    area.querySelectorAll(".pílula").forEach((botao) => {
      botao.addEventListener("click", () => {
        campo("texto").value = botao.dataset.texto;
        atualizarContador();
        campo("texto").focus();
      });
    });
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
