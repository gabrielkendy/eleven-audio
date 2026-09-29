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
          <p class="aviso" data-aviso-motor>Verificando se o motor de desenho está disponível...</p>
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
    // O desenho depende de um motor só. Se ele está fora, a tela PRECISA dizer
    // isso e travar o botão: antes ela mandava o aluno para a CONFIGURAÇÃO, que
    // não tem seletor de motor, e ele só descobria no erro depois de preencher tudo.
    const avisoMotor = raiz.querySelector("[data-aviso-motor]");
    let motorLiberado = false;

    async function conferirMotor() {
      try {
        const catalogo = await fetch("/api/motores").then(ler);
        const motor = catalogo.find((item) => item.id === "voxcpm2");
        if (motor && motor.disponivel) {
          motorLiberado = true;
          botao.disabled = false;
          avisoMotor.textContent = "O desenho usa o VoxCPM2, que está disponível nesta máquina.";
          return;
        }
        motorLiberado = false;
        botao.disabled = true;
        // O motivo vem do backend como frase fechada, começando com maiúscula
        // ("Derruba a base ao gerar..."). Emendado no meio da nossa frase ele soa
        // quebrado, então entra depois de "Motivo:".
        const porque = (motor?.motivo || "o motor não está instalado nesta máquina")
          .trim()
          .replace(/\.$/, "");
        avisoMotor.textContent =
          `Esta área está indisponível. Motivo: ${porque}. ` +
          `O desenho depende do ${motor?.nome || "VoxCPM2"}, que o estúdio não pode ligar aqui. ` +
          "Para criar uma voz, use Clonar (com um áudio seu) ou Gerar (com uma voz da lista).";
      } catch (erro) {
        motorLiberado = false;
        botao.disabled = true;
        avisoMotor.textContent = `Não deu para conferir o motor de desenho: ${erro.message}`;
      }
    }
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      if (!motorLiberado) {
        estado.textContent = "Esta área está indisponível nesta máquina. Veja o motivo no aviso acima.";
        return;
      }
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
        // Só devolve o botão se o motor continua liberado: sem isso, um erro
        // reabilitava o botão e o aluno voltava a levar 409.
        botao.disabled = !motorLiberado;
        botao.textContent = "Ouvir e salvar perfil";
      }
    });

    conferirMotor();
    atualizarLista();
  },
});
