(function () {
  const BASE_MCP = "http://127.0.0.1:3900/mcp/";

  async function api(url, options) {
    const resposta = await fetch(url, options);
    const corpo = await resposta.json();
    if (!resposta.ok) throw new Error(corpo.detail || `Erro HTTP ${resposta.status}`);
    return corpo;
  }

  window.AREAS = window.AREAS || [];
  window.AREAS.push({
    id: "agente",
    titulo: "Agente",
    montar(raiz) {
      raiz.innerHTML = `
        <ol class="grade-cartoes" aria-label="Passos para ligar a voz">
          <li aria-label="1. Escolher cliente e voz"><strong>Escolher cliente e voz</strong><span>Defina quem usará o perfil.</span></li>
          <li aria-label="2. Ligar"><strong>Ligar</strong><span>Salve o vínculo na base local.</span></li>
          <li aria-label="3. Colar o comando no agente"><strong>Colar o comando no agente</strong><span>Use o formato aceito pelo seu agente.</span></li>
        </ol>
        <section class="compositor">
          <label class="campo-rotulo" for="agente-cliente">Cliente</label>
          <input id="agente-cliente" value="hermes" list="agente-clientes" maxlength="128">
          <datalist id="agente-clientes"><option value="hermes"></option></datalist>
          <label class="campo-rotulo" for="agente-perfil">Perfil salvo</label>
          <select id="agente-perfil"><option value="">Carregando perfis...</option></select>
          <div class="linha-acao">
            <span class="chip" data-estado-atual>Estado atual: consultando</span>
            <div><button id="agente-ligar" type="button">Ligar</button> <button id="agente-desligar" type="button">Desligar</button></div>
          </div>
        </section>
        <p class="aviso" id="agente-mensagem" role="status">Carregando vínculos...</p>
        <section>
          <h3>Vínculos existentes</h3>
          <div class="grade-cartoes" id="agente-vinculos"></div>
        </section>
        <section class="grade-cartoes">
          <article>
            <h3>Codex (TOML)</h3>
            <pre id="agente-toml" tabindex="0"></pre>
            <button type="button" data-copiar="agente-toml">Copiar</button>
          </article>
          <article>
            <h3>JSON</h3>
            <pre id="agente-json" tabindex="0"></pre>
            <button type="button" data-copiar="agente-json">Copiar</button>
          </article>
        </section>`;

      const cliente = raiz.querySelector("#agente-cliente");
      const perfil = raiz.querySelector("#agente-perfil");
      const mensagem = raiz.querySelector("#agente-mensagem");
      const lista = raiz.querySelector("#agente-vinculos");
      const estadoAtual = raiz.querySelector("[data-estado-atual]");

      function comandos() {
        const id = cliente.value.trim() || "hermes";
        raiz.querySelector("#agente-toml").textContent = `[mcp_servers.estudio]\nurl = "${BASE_MCP}"\nhttp_headers = { "X-OmniVoice-Client-Id" = ${JSON.stringify(id)} }`;
        raiz.querySelector("#agente-json").textContent = JSON.stringify({
          "mcpServers": { estudio: { url: BASE_MCP, headers: { "X-OmniVoice-Client-Id": id } } },
        }, null, 2);
      }

      async function carregarPerfis() {
        try {
          const dados = await api("/api/perfis");
          const perfis = Array.isArray(dados) ? dados : (dados.perfis || []);
          perfil.replaceChildren(...perfis.map((voz) => new Option(`${voz.nome} · ${voz.origem}`, voz.id)));
          if (!perfis.length) perfil.append(new Option("Nenhum perfil disponível", ""));
        } catch (erro) {
          perfil.replaceChildren(new Option(`Erro: ${erro.message}`, ""));
        }
      }

      async function carregarStatus() {
        mensagem.textContent = "Carregando vínculos...";
        try {
          const estado = await api("/api/agente/status");
          const unidos = new Map();
          estado.vinculos_base.forEach((v) => {
            unidos.set(v.client_id, v);
          });
          estado.vinculos_locais.forEach((v) => {
            unidos.set(v.cliente_id, { ...unidos.get(v.cliente_id), ...v });
          });
          lista.replaceChildren(...Array.from(unidos, ([id, vinculo]) => {
            const item = document.createElement("article");
            const titulo = document.createElement("strong");
            const detalhe = document.createElement("p");
            titulo.textContent = id;
            detalhe.textContent = vinculo.perfil_nome || vinculo.profile_id || vinculo.perfil_id || "Sem perfil";
            item.append(titulo, detalhe);
            return item;
          }));
          if (!unidos.size) lista.innerHTML = '<p class="vazio">Nenhum vínculo ativo.</p>';
          estadoAtual.textContent = `Estado atual: MCP ${estado.mcp.estado} · ${estado.clientes_vinculados ?? unidos.size} cliente(s)`;
          mensagem.textContent = estado.mcp.estado === "erro"
            ? `Erro: ${estado.mcp.motivo}. Os vínculos locais continuam listados.`
            : (unidos.size ? `${unidos.size} vínculo(s) ativo(s).` : "Nenhum vínculo ativo.");
        } catch (erro) {
          estadoAtual.textContent = "Estado atual: indisponível";
          mensagem.textContent = `Erro: ${erro.message}`;
        }
      }

      async function alterar(url) {
        mensagem.textContent = "Carregando...";
        try {
          const corpo = { cliente_id: cliente.value.trim() };
          if (url.endsWith("ligar")) corpo.perfil_id = perfil.value;
          await api(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(corpo),
          });
          await carregarStatus();
        } catch (erro) {
          mensagem.textContent = `Erro: ${erro.message}`;
        }
      }

      async function copiar(id) {
        const bloco = raiz.querySelector(`#${id}`);
        try {
          await navigator.clipboard.writeText(bloco.textContent);
          mensagem.textContent = "Comando copiado.";
        } catch (_) {
          const selecao = window.getSelection();
          const faixa = document.createRange();
          faixa.selectNodeContents(bloco);
          selecao.removeAllRanges();
          selecao.addRange(faixa);
          mensagem.textContent = "A cópia automática falhou. O comando foi selecionado para você copiar.";
        }
      }

      cliente.addEventListener("input", comandos);
      raiz.querySelector("#agente-ligar").addEventListener("click", () => alterar("/api/agente/ligar"));
      raiz.querySelector("#agente-desligar").addEventListener("click", () => alterar("/api/agente/desligar"));
      raiz.querySelectorAll("[data-copiar]").forEach((botao) => {
        botao.addEventListener("click", () => copiar(botao.dataset.copiar));
      });
      comandos();
      carregarPerfis();
      carregarStatus();
    },
  });
}());
