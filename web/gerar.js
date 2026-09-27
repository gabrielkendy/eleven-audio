window.AREAS.gerar = {
  titulo: "Gerar",
  ordem: 1,
  html() {
    return `
      <div class="rail">
        <div class="compositor">
          <div class="abas" role="tablist" aria-label="Áreas do estúdio">
            <button class="aba ativa" type="button" data-nav="gerar">Speech</button>
            <button class="aba" type="button" data-nav="clonar">Clonar</button>
            <button class="aba" type="button" data-nav="desenhar">Desenhar</button>
            <button class="aba" type="button" data-nav="transcrever">Transcrever</button>
            <button class="aba" type="button" data-nav="agente">Agente</button>
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
            <button type="button" class="player-play" data-acao="play" aria-label="Tocar áudio">▶</button>
            <div class="onda" data-campo="onda" aria-hidden="true"></div>
            <span data-campo="tempo-player">0:00</span>
            <a data-campo="baixar" download>Baixar WAV</a>
            <button type="button" data-acao="abrir-pasta">Abrir pasta</button>
            <audio data-campo="audio"></audio>
          </div>
        </div>

        <aside class="ajustes" data-campo="rail" aria-label="Ajustes de geração">
          <label><span class="campo-rotulo">Motor</span>
            <select data-campo="motor"><option>Carregando...</option></select>
          </label>
          <div>
            <label for="busca-voz-gerar" class="campo-rotulo">Voz</label>
            <input id="busca-voz-gerar" data-campo="busca-voz" type="search" placeholder="Buscar voz salva">
            <div data-campo="vozes" class="lista-vozes"></div>
          </div>
          <label class="slider"><span class="campo-rotulo">Velocidade <output data-campo="velocidade-valor">1,0x</output></span>
            <input data-campo="velocidade" type="range" min="0.5" max="2" step="0.1" value="1">
            <small>Mais lento</small><small>Mais rápido</small>
          </label>
          <label class="slider"><span class="campo-rotulo">Variação <output data-campo="variacao-valor">50%</output></span>
            <input data-campo="variacao" type="range" min="0" max="100" value="50">
            <small>Mais variável</small><small>Mais estável</small>
          </label>
          <div><span class="campo-rotulo">Marcas aceitas</span><p data-campo="marcas">Carregando...</p></div>
        </aside>
      </div>`;
  },
  montar(area) {
    const campo = (nome) => area.querySelector(`[data-campo="${nome}"]`);
    const aviso = campo("aviso");
    const audio = campo("audio");
    const previas = new Map();
    let motores = [];
    let perfis = [];
    let perfilSelecionado = null;
    let ultimaGeracao = null;

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
      campo("motor-chip").textContent = `${motor.nome} `;
      campo("motor-dispositivo").textContent = motor.dispositivo || "sem dispositivo";
      campo("motor-estado").textContent = motor.disponivel ? "instalado" : "indisponível";
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
      campo("voz-origem").textContent = perfilSelecionado?.origem || "do motor";
      area.querySelectorAll("[data-perfil-id]").forEach((item) => {
        item.classList.toggle("ativo", item.dataset.perfilId === perfilSelecionado?.id);
      });
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
        origem.textContent = perfil.origem || "origem não informada";
        const usar = document.createElement("button");
        usar.type = "button";
        usar.textContent = "Usar esta voz";
        usar.addEventListener("click", () => {
          perfilSelecionado = perfil;
          atualizarVoz();
        });
        const tocar = document.createElement("button");
        tocar.type = "button";
        tocar.textContent = "Tocar prévia";
        tocar.addEventListener("click", () => {
          const previa = previas.get(perfil.id);
          if (!previa) return mostrarAviso("Esta voz ainda não tem prévia nesta sessão.");
          audio.src = previa;
          audio.play();
        });
        item.append(nome, origem, usar, tocar);
        lista.append(item);
      });
      atualizarVoz();
    }

    async function carregarPerfis() {
      perfis = await api("/perfis");
      if (perfilSelecionado) perfilSelecionado = perfis.find((item) => item.id === perfilSelecionado.id) || null;
      renderizarVozes();
      atualizarVoz();
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
        lista.append(linha);
      });
    }

    function desenharOnda(chave) {
      const onda = campo("onda");
      onda.replaceChildren();
      let semente = [...chave].reduce((total, letra) => total + letra.charCodeAt(0), 0) || 1;
      for (let indice = 0; indice < 48; indice += 1) {
        semente = (semente * 9301 + 49297) % 233280;
        const barra = document.createElement("i");
        barra.style.height = `${18 + (semente % 70)}%`;
        onda.append(barra);
      }
    }

    function mostrarPlayer(resultado) {
      const url = resultado.audio_url || resultado.arquivo;
      audio.src = url;
      campo("baixar").href = url;
      campo("tempo-player").textContent = `${Number(resultado.duracao_audio_s).toFixed(2)} s`;
      desenharOnda(resultado.arquivo || url);
      campo("player").hidden = false;
      campo("vazio").hidden = true;
      if (perfilSelecionado) previas.set(perfilSelecionado.id, url);
    }

    async function carregar() {
      try {
        const [catalogo, estado, saidas] = await Promise.all([api("/motores"), api("/estado"), api("/saidas")]);
        motores = catalogo;
        campo("motor").replaceChildren(...motores.map((motor) => {
          const opcao = document.createElement("option");
          opcao.value = motor.id;
          opcao.disabled = !motor.disponivel;
          opcao.textContent = `${motor.nome}${motor.disponivel ? "" : `: ${motor.motivo || "indisponível"}`}`;
          return opcao;
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
      const texto = campo("texto").value.trim();
      if (!texto) return mostrarAviso("Escreva o texto do áudio.");
      const botao = area.querySelector("[data-acao='gerar']");
      botao.disabled = true;
      botao.textContent = "Gerando. O primeiro uso pode baixar vários GB...";
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
            semente: Number(campo("variacao").value),
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
    campo("variacao").addEventListener("input", () => campo("variacao-valor").textContent = `${campo("variacao").value}%`);
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
    area.querySelector("[data-acao='play']").addEventListener("click", () => audio.paused ? audio.play() : audio.pause());
    audio.addEventListener("play", () => area.querySelector("[data-acao='play']").textContent = "❚❚");
    audio.addEventListener("pause", () => area.querySelector("[data-acao='play']").textContent = "▶");
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
