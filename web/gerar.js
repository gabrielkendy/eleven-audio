window.AREAS.gerar = {
  titulo: "Gerar",
  ordem: 1,
  html() {
    return `
      <div class="titulo-area"><span>01</span><h2>Gerar áudio</h2></div>
      <label>O que a voz vai dizer
        <textarea data-campo="texto" maxlength="5000" rows="7" placeholder="Escreva em português..."></textarea>
      </label>
      <div class="linha"><small data-campo="contador">0 / 5000</small></div>
      <div class="grade">
        <label>Motor<select data-campo="motor"><option>Carregando...</option></select></label>
        <label>Perfil<select data-campo="perfil"><option value="">Voz padrão</option></select></label>
        <label>Idioma<select data-campo="idioma"><option value="pt">Português</option></select></label>
        <label>Velocidade<input data-campo="velocidade" type="number" min="0.5" max="2" step="0.1" value="1"></label>
      </div>
      <button data-acao="gerar" class="primario">Gerar áudio</button>
      <p data-campo="estado" role="status">Nenhum áudio gerado nesta sessão.</p>
      <audio data-campo="player" controls hidden></audio>
      <h3>Saídas recentes</h3>
      <ul data-campo="saidas"><li>Carregando...</li></ul>`;
  },
  montar(area) {
    const campo = (nome) => area.querySelector(`[data-campo="${nome}"]`);
    const estado = campo("estado");

    async function api(caminho, opcoes = {}) {
      const resposta = await fetch(`/api${caminho}`, {
        headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
        ...opcoes,
      });
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || "Erro inesperado");
      return corpo;
    }

    async function carregar() {
      try {
        const [motores, maquina, itens] = await Promise.all([
          api("/motores"), api("/estado"), api("/saidas"),
        ]);
        campo("motor").innerHTML = motores.map((motor) =>
          `<option value="${motor.id}" ${motor.disponivel ? "" : "disabled"}>${motor.nome}${motor.disponivel ? "" : ` · ${motor.motivo}`}</option>`
        ).join("");
        campo("motor").value = motores.some((m) =>
          m.id === maquina.motor_ativo && m.disponivel
        ) ? maquina.motor_ativo : "mock";
        campo("saidas").innerHTML = itens.length ? itens.slice(0, 5).map((item) =>
          `<li>${item.motor} · ${Number(item.duracao_audio_s).toFixed(2)} s · ${item.arquivo_saida}</li>`
        ).join("") : "<li>Nenhuma saída ainda.</li>";
      } catch (erro) {
        estado.textContent = erro.message;
        estado.className = "erro";
      }
    }

    campo("texto").addEventListener("input", (evento) => {
      campo("contador").textContent = `${evento.target.value.length} / 5000`;
    });
    campo("motor").addEventListener("change", async () => {
      try {
        await api("/motores/ativo", {
          method: "POST",
          body: JSON.stringify({ motor: campo("motor").value }),
        });
        window.dispatchEvent(new Event("estudio:atualizar-estado"));
      } catch (erro) {
        estado.textContent = erro.message;
        estado.className = "erro";
      }
    });
    area.querySelector("[data-acao='gerar']").addEventListener("click", async (evento) => {
      const botao = evento.currentTarget;
      botao.disabled = true;
      estado.textContent = "Gerando e medindo. No primeiro uso, o motor pode baixar vários GB...";
      estado.className = "";
      try {
        const resultado = await api("/gerar", {
          method: "POST",
          body: JSON.stringify({
            texto: campo("texto").value,
            motor: campo("motor").value,
            perfil_id: campo("perfil").value || null,
            idioma: campo("idioma").value,
            velocidade: Number(campo("velocidade").value),
          }),
        });
        estado.textContent = `Pronto em ${resultado.duracao_geracao_s.toFixed(3)} s. Áudio de ${resultado.duracao_audio_s.toFixed(2)} s.`;
        estado.className = "ok";
        campo("player").src = resultado.audio_url;
        campo("player").hidden = false;
        await carregar();
        window.dispatchEvent(new Event("estudio:atualizar-estado"));
      } catch (erro) {
        estado.textContent = erro.message;
        estado.className = "erro";
      } finally {
        botao.disabled = false;
      }
    });
    carregar();
  },
};
