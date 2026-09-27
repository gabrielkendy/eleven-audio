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
    titulo: "AGENTE",
    montar(raiz) {
      raiz.innerHTML = `
        <section aria-labelledby="agente-titulo">
          <h2 id="agente-titulo">Ligar a voz no agente</h2>
          <label>Identificador do cliente <input id="agente-cliente" value="estudio" maxlength="128"></label>
          <label>Perfil de voz <select id="agente-perfil"><option>Carregando perfis...</option></select></label>
          <button id="agente-ligar" type="button">Ligar</button>
          <button id="agente-desligar" type="button">Desligar</button>
          <p id="agente-mensagem" role="status">Carregando vínculos...</p>
          <ul id="agente-vinculos"></ul>
          <h3>Codex CLI (TOML)</h3><pre id="agente-toml"></pre>
          <h3>Configuração JSON</h3><pre id="agente-json"></pre>
        </section>`;

      const cliente = raiz.querySelector("#agente-cliente");
      const perfil = raiz.querySelector("#agente-perfil");
      const mensagem = raiz.querySelector("#agente-mensagem");
      const lista = raiz.querySelector("#agente-vinculos");

      function comandos() {
        const id = cliente.value.trim() || "estudio";
        raiz.querySelector("#agente-toml").textContent = `[mcp_servers.estudio]\nurl = "${BASE_MCP}"\nhttp_headers = { "X-OmniVoice-Client-Id" = ${JSON.stringify(id)} }`;
        raiz.querySelector("#agente-json").textContent = JSON.stringify({
          "mcpServers": { estudio: { url: BASE_MCP, headers: { "X-OmniVoice-Client-Id": id } } },
        }, null, 2);
      }

      async function carregarPerfis() {
        try {
          const dados = await api("/api/perfis");
          const perfis = Array.isArray(dados) ? dados : (dados.perfis || []);
          perfil.replaceChildren();
          if (!perfis.length) {
            perfil.append(new Option("Nenhum perfil disponível", ""));
            return;
          }
          perfis.forEach((voz) => perfil.append(new Option(voz.nome, voz.id)));
        } catch (erro) {
          perfil.replaceChildren(new Option(`Erro: ${erro.message}`, ""));
        }
      }

      async function carregarStatus() {
        mensagem.textContent = "Carregando vínculos...";
        try {
          const estado = await api("/api/agente/status");
          const unidos = new Map();
          estado.vinculos_base.forEach((v) => unidos.set(v.client_id, v));
          estado.vinculos_locais.forEach((v) => unidos.set(v.cliente_id, { ...unidos.get(v.cliente_id), ...v }));
          lista.replaceChildren();
          unidos.forEach((v, id) => {
            const item = document.createElement("li");
            item.textContent = `${id}: ${v.perfil_nome || v.profile_id || v.perfil_id || "sem perfil"}`;
            lista.append(item);
          });
          mensagem.textContent = estado.mcp.estado === "erro"
            ? `Erro: ${estado.mcp.motivo}. Os vínculos locais continuam listados.`
            : (unidos.size ? `${unidos.size} vínculo(s) ativo(s).` : "Nenhum vínculo ativo.");
        } catch (erro) {
          mensagem.textContent = `Erro: ${erro.message}`;
        }
      }

      async function alterar(url) {
        mensagem.textContent = "Carregando...";
        try {
          const corpo = { cliente_id: cliente.value.trim() };
          if (url.endsWith("ligar")) corpo.perfil_id = perfil.value;
          await api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
          await carregarStatus();
        } catch (erro) {
          mensagem.textContent = `Erro: ${erro.message}`;
        }
      }

      cliente.addEventListener("input", comandos);
      raiz.querySelector("#agente-ligar").addEventListener("click", () => alterar("/api/agente/ligar"));
      raiz.querySelector("#agente-desligar").addEventListener("click", () => alterar("/api/agente/desligar"));
      comandos();
      carregarPerfis();
      carregarStatus();
    },
  });
}());
