window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "desenhar",
  titulo: "Desenhar voz",
  montar(raiz) {
    const exemplos = {
      Narrador: "Narrador adulto, grave, sereno e acolhedor, com ritmo pausado.",
      Locutor: "Locutora jovem, clara, confiante e energética, com dicção de rádio.",
      Personagem: "Personagem aventureiro, expressivo, curioso e bem humorado.",
      Sussurro: "Mulher adulta falando baixo, em sussurro íntimo e tranquilo.",
      Idoso: "Senhor idoso, voz grave, rouca, calma e cheia de experiência.",
      Infantil: "Criança alegre, espontânea, curiosa e cheia de energia.",
    };

    raiz.innerHTML = `
      <div class="rail">
        <form class="compositor" data-form-desenhar>
          <label class="campo-rotulo" for="desenhar-descricao">Descreva a voz</label>
          <textarea id="desenhar-descricao" name="descricao" maxlength="2000" rows="10" required
            placeholder="Exemplo: narrador quente, grave, pausado e acolhedor"></textarea>
          <div class="pílulas" aria-label="Pontos de partida">
            ${Object.keys(exemplos).map((nome) => `<button class="pílula" type="button" data-exemplo="${nome}">${nome}</button>`).join("")}
          </div>
          <label class="campo-rotulo" for="desenhar-previa">Texto da prévia</label>
          <textarea id="desenhar-previa" name="texto_previa" maxlength="5000" rows="4" required>A mesma frase permite comparar claramente as vozes desenhadas.</textarea>
          <div class="linha-acao">
            <span class="chip">VoxCPM2 <span class="pastilha">único motor</span></span>
            <button type="submit">Ouvir e salvar perfil</button>
          </div>
        </form>
        <aside>
          <label class="campo-rotulo" for="desenhar-nome">Nome do perfil</label>
          <input id="desenhar-nome" name="nome" maxlength="60" placeholder="Minha nova voz">
          <p class="aviso">O desenho usa o motor VoxCPM2. Se ele estiver indisponível, abra a área <a href="#config" data-ir-config>CONFIGURACAO</a> e confira a instalação.</p>
        </aside>
      </div>
      <p class="aviso" role="status" data-estado>Descreva a voz e gere uma prévia para salvar o perfil.</p>
      <section data-resultado hidden>
        <h3 data-resultado-titulo>Perfil criado</h3>
        <div class="player">
          <div class="onda"><audio data-audio controls preload="metadata"></audio></div>
          <span data-tempo>0,0 s</span>
        </div>
      </section>
      <section aria-labelledby="desenhos-titulo">
        <h3 id="desenhos-titulo">Perfis desenhados</h3>
        <div class="grade-cartoes" data-lista><p class="vazio">Carregando perfis desenhados...</p></div>
      </section>`;

    const form = raiz.querySelector("[data-form-desenhar]");
    const descricao = form.elements.descricao;
    const estado = raiz.querySelector("[data-estado]");
    const resultado = raiz.querySelector("[data-resultado]");
    const audio = raiz.querySelector("[data-audio]");
    const lista = raiz.querySelector("[data-lista]");
    const botao = form.querySelector("button[type=submit]");

    async function ler(resposta) {
      const corpo = await resposta.json();
      if (!resposta.ok) throw new Error(corpo.detail || "A base não respondeu.");
      return corpo;
    }

    async function atualizarLista() {
      try {
        const vozes = await fetch("/api/desenhos").then(ler);
        if (!vozes.length) {
          lista.innerHTML = '<p class="vazio">Nenhum perfil desenhado ainda.</p>';
          return;
        }
        lista.replaceChildren(...vozes.map((voz) => {
          const item = document.createElement("article");
          const titulo = document.createElement("strong");
          const detalhe = document.createElement("p");
          titulo.textContent = voz.nome;
          detalhe.textContent = `${new Date(voz.criado_em).toLocaleString("pt-BR")} · ${voz.total_geracoes} prévia(s)`;
          item.append(titulo, detalhe);
          return item;
        }));
      } catch (erro) {
        lista.textContent = `Erro ao carregar os perfis: ${erro.message}`;
      }
    }

    raiz.querySelectorAll("[data-exemplo]").forEach((pílula) => {
      pílula.addEventListener("click", () => {
        descricao.value = exemplos[pílula.dataset.exemplo];
        descricao.focus();
      });
    });
    raiz.querySelector("[data-ir-config]").addEventListener("click", (evento) => {
      evento.preventDefault();
      document.querySelector('[data-alvo="config"]')?.click();
    });
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      botao.disabled = true;
      botao.textContent = "Desenhando a voz...";
      estado.textContent = "Carregando o VoxCPM2 e criando a prévia. O primeiro uso pode demorar.";
      try {
        const criado = await fetch("/api/desenhar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            descricao: descricao.value,
            texto_previa: form.elements.texto_previa.value,
            motor: "voxcpm2",
          }),
        }).then(ler);
        const caminhoAudio = String(criado.arquivo).replace(/^\/?saidas\/audio\//, "");
        audio.src = `/saidas/${caminhoAudio}`;
        raiz.querySelector("[data-tempo]").textContent = `${Number(criado.duracao_audio_s).toFixed(1).replace(".", ",")} s`;
        const nome = raiz.querySelector("#desenhar-nome").value.trim();
        raiz.querySelector("[data-resultado-titulo]").textContent = nome || `Perfil ${criado.perfil_id}`;
        resultado.hidden = false;
        estado.textContent = `Perfil salvo em ${Number(criado.duracao_geracao_s).toFixed(1).replace(".", ",")} s.`;
        await atualizarLista();
      } catch (erro) {
        estado.textContent = `Erro: ${erro.message}`;
      } finally {
        botao.disabled = false;
        botao.textContent = "Ouvir e salvar perfil";
      }
    });

    atualizarLista();
  },
});
