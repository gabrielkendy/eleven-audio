window.AREAS = window.AREAS || [];

window.AREAS.push({
  id: "config",
  titulo: "Configuração",
  async montar(raiz) {
    const LICENCAS = [
      ["Estudio de Voz Local", "licenca a definir"],
      ["VoiceStudio", "AGPL-3.0"],
      ["OmniVoice", "licenca propria do projeto"],
      ["VoxCPM2", "licenca propria do OpenBMB"],
      ["IndexTTS 2.5", "licenca propria do projeto"],
      ["Faster-Whisper", "licenca propria do projeto"],
      ["WhisperX", "licenca propria do projeto"],
    ];

    async function ler(url) {
      const resposta = await fetch(url);
      return resposta.ok ? resposta.json() : null;
    }

    raiz.classList.add("area-config");
    raiz.innerHTML = `
      <div class="config-grade" aria-live="polite"></div>
      <button class="config-abrir" type="button">Abrir pasta de saídas</button>
      <p class="config-aviso">O aplicativo avisa se não conseguir abrir a pasta.</p>
      <section class="config-licencas">
        <h3>Licenças dos motores</h3>
        <div class="config-lista-licencas"></div>
        <p>Leia a licença de cada motor antes de usar o áudio comercialmente.</p>
      </section>`;

    const lista = raiz.querySelector(".config-lista-licencas");
    for (const [nome, tipo] of LICENCAS) {
      const linha = document.createElement("p");
      const rotulo = document.createElement("strong");
      rotulo.textContent = nome;
      linha.append(rotulo, `: ${tipo}`);
      lista.append(linha);
    }

    let config = null;
    let saude = null;
    let estado = null;
    try {
      [config, saude, estado] = await Promise.all([ler("/api/config"), ler("/api/saude"), ler("/api/estado")]);
    } catch (erro) {
      console.warn("Configuracao indisponivel", erro);
    }

    const campos = [
      ["Porta do app", config?.porta || 7800],
      ["Porta da base", config?.porta_base || 3900],
      ["Pasta de saidas", estado?.pasta_saidas || config?.saidas || config?.pasta_saidas || "saidas/audio"],
      ["Pasta de dados", config?.dados || config?.pasta_dados || "dados"],
      ["Espaco livre", saude?.disco_livre_gb == null ? "indisponivel" : `${saude.disco_livre_gb} GB`],
      ["Estado da base", saude?.base || estado?.base || "indisponivel"],
      ["Motor ativo", estado?.motor_ativo || config?.motor || saude?.motor_ativo || "indisponivel"],
    ];
    const grade = raiz.querySelector(".config-grade");
    for (const [nome, valor] of campos) {
      const cartao = document.createElement("div");
      const rotulo = document.createElement("span");
      const dado = document.createElement("strong");
      rotulo.textContent = nome;
      dado.textContent = String(valor);
      cartao.append(rotulo, dado);
      grade.append(cartao);
    }

    const aviso = raiz.querySelector(".config-aviso");
    raiz.querySelector(".config-abrir").addEventListener("click", async () => {
      aviso.textContent = "Abrindo a pasta...";
      try {
        const resposta = await fetch("/api/saidas/abrir", { method: "POST" });
        aviso.textContent = resposta.ok
          ? "Pasta aberta."
          : "O endpoint de abrir pasta ainda nao existe nesta versao.";
      } catch (_) {
        aviso.textContent = "Nao foi possivel pedir ao app para abrir a pasta.";
      }
    });
  },
});
