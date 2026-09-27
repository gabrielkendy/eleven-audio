# 08 · Deploy local (instalação, operação e recuperação no Windows)

> Arquivo 8 de 10 do manual. Onde o kit de referência fala de Docker, Railway e Cloudflare, aqui se
> fala de pasta, atalho, porta local e backup. Mesma disciplina: subir de forma reprodutível,
> verificar de verdade, ter plano B.
> Máquina de referência: Windows, RTX 4080 16 GB, pasta do projeto com acento e espaço no caminho.

---

## 1. O que o "deploy" significa neste projeto

| Conceito de nuvem | Equivalente local |
|---|---|
| Servidor | a sua máquina, em `127.0.0.1` |
| Container | pasta do projeto mais ambiente Python |
| Domínio | `http://127.0.0.1:7800` |
| Deploy | subir os dois processos (base e camada fina) |
| Log de produção | `dados\logs\` |
| Banco de produção | `dados\estudio.db` |
| Backup | copiar `dados\` e `saidas\` |
| Rollback | voltar a versão anterior no Git e reiniciar |
| Health check | `GET /health` da base e `GET /api/saude` da nossa camada |

---

## 2. Pré-requisitos (conferir antes de instalar, não durante)

| Item | Como conferir | Resultado esperado |
|---|---|---|
| Windows 10 21H2 ou mais novo | Configurações do sistema | x64, versão compatível |
| Git | `git --version` | responde versão |
| Python 3.11 ou mais novo | `python --version` | 3.11 ou mais |
| uv | `uv --version` | responde versão |
| Bun (só se houver build de tela) | `bun --version` | responde versão |
| FFmpeg | `ffmpeg -version` | responde versão |
| Driver NVIDIA | `nvidia-smi` | mostra a RTX 4080 e a versão de CUDA |
| Espaço em disco | Explorador de arquivos | 30 GB livres ou mais |
| Fonte de build C++ (só se instalar pacote que compila) | presença do Visual Studio Build Tools | instalado |

---

## 3. Passo a passo de instalação (na ordem, sem pular)

### 3.1 Preparar a base

```bash
# 1. entrar na pasta da base (caminho real, com aspas por causa do acento)
cd "/c/Users/Gabriel/Downloads/YOUTUBE KENDY/02-EM-PRODUCAO/SÉRIE · ENGENHARIA REVERSA DE PRODUTO/2-MATERIAIS-DA-SOLUCAO/4-BASE-VOICESTUDIO"

# 2. instalar dependencias do JS (Electron, workspace)
bun install

# 3. preparar o ambiente Python da base
bun run setup:api

# 4. subir em modo desenvolvimento
bun run dev
```

Alternativa sem Electron (subir só o backend, que é o que a nossa camada precisa):

```bash
uv run uvicorn backend.main:app --host 127.0.0.1 --port 3900
```

### 3.2 Confirmar que a base está de pé (a verificação que não pode faltar)

```bash
curl -s http://127.0.0.1:3900/health
curl -s http://127.0.0.1:3900/api/engines
```

Se o `/health` responder e a lista de motores vier com o motor padrão disponível, a base está no ar.
Se vier motor indisponível, o motivo aparece na resposta e é ali que se resolve (instalar peso,
instalar pacote do motor, escolher outro).

### 3.3 Instalar o motor de qualidade (VoxCPM2)

```bash
# dentro do ambiente Python da base
pip install "voxcpm>=2.0.3"

# conferir depois de reiniciar a base
curl -s http://127.0.0.1:3900/api/engines | grep -i voxcpm
```

Alternativa oficial citada pela base: instalação em um clique dentro do catálogo de modelos dela. A
base coloca o VoxCPM2 no ambiente Python próprio dele, separado do ambiente principal.

### 3.4 Preparar a nossa camada fina

```bash
cd "/c/Users/Gabriel/Downloads/YOUTUBE KENDY/02-EM-PRODUCAO/SÉRIE · ENGENHARIA REVERSA DE PRODUTO/estudio"

# ambiente da nossa camada
uv venv .venv
. .venv/Scripts/activate        # no Git Bash
uv pip install -r requirements.txt

# subir a nossa tela
set ESTUDIO_PORT=7800
python -m uvicorn app.servidor:app --host 127.0.0.1 --port 7800
```

### 3.5 Verificação final da instalação (o teste de fumaça)

```bash
python scripts/fumaca.py
```

Saída esperada: base saudável, motores listados, um áudio gerado, arquivo existindo no disco. Se
qualquer linha falhar, o problema está naquela peça e não no resto.

---

## 4. Portas, rede e firewall

| Porta | Quem usa | Padrão | Expor? |
|---|---|---|---|
| 3900 | base (API, MCP, UI dela) | `OMNIVOICE_PORT` | não |
| 7800 | nossa camada fina | `ESTUDIO_PORT` | não |
| porta de compartilhamento da base | outro aparelho na mesma rede | escolhida pela base ao ligar | só por sessão, e nunca em rede pública |

Regras:

1. Não criar regra de entrada no firewall do Windows para 3900 nem para 7800. Se o firewall
   perguntar, negar acesso em rede pública e privada.
2. Não usar `OMNIVOICE_BIND_HOST=0.0.0.0` nem `--host 0.0.0.0`. O padrão é loopback, e o padrão é
   a resposta certa.
3. Acesso de outro aparelho, quando precisar: ligar compartilhamento na própria base e usar o PIN
   da sessão, ou usar Tailscale (rede privada com túnel).
4. Antes de gravar o vídeo, fechar o navegador com a interface da base aberta em endereço de rede.

---

## 5. Modelo de execução (como o app fica ligado no dia a dia)

| Forma | Como | Quando usar |
|---|---|---|
| Dois prompts abertos | um subindo a base, outro subindo a nossa camada | dia de gravação e de desenvolvimento |
| Atalho `.cmd` | script que sobe os dois em sequência e abre o navegador | uso normal de quem não é técnico |
| Serviço do Windows | tarefa agendada ou serviço | só se o app precisar subir sozinho com o sistema |

Modelo recomendado para o aluno: **dois atalhos**, um chamado "1 Subir a base" e outro "2 Abrir o
estudio". Nada de serviço no primeiro dia, porque serviço esconde erro em vez de mostrar.

```bat
:: 1-subir-base.cmd  (exemplo de atalho)
@echo off
cd /d "C:\caminho\para\4-BASE-VOICESTUDIO"
set OMNIVOICE_DATA_DIR=C:\caminho\para\dados-da-base
uv run uvicorn backend.main:app --host 127.0.0.1 --port 3900
```

```bat
:: 2-subir-estudio.cmd
@echo off
cd /d "C:\caminho\para\estudio"
set ESTUDIO_PORT=7800
.venv\Scripts\python.exe -m uvicorn app.servidor:app --host 127.0.0.1 --port 7800
start "" http://127.0.0.1:7800
```

---

## 6. Onde ficam os dados (e como não perdê-los)

| Pasta | O que tem | Entra no backup? |
|---|---|---|
| `estudio\saidas\audio\` | os áudios gerados | sim, é o trabalho |
| `estudio\dados\estudio.db` | perfis, consentimento, geracoes, transcrições | sim |
| `estudio\dados\referencias\` | clipes de clonagem | decidir: é dado sensível de voz |
| `estudio\dados\logs\` | log de operação | opcional |
| pasta de dados da base (`OMNIVOICE_DATA_DIR`) | pesos dos modelos, banco dela, cache de prompt | não precisa: baixa de novo |
| pasta do repositório da base | código | não precisa: vem do Git |

Recomendação forte: fixar `OMNIVOICE_DATA_DIR` numa pasta fora do repositório, para nunca misturar
peso de modelo com código versionado.

---

## 7. Atualização (da base e da nossa camada)

| O que atualizar | Como | Cuidado |
|---|---|---|
| Base | `git pull` na pasta da base e repetir `bun install` e `bun run setup:api` quando o manifest mudar | ler o `CHANGELOG.md` antes. A base muda rápido |
| Nossa camada | `git pull` na pasta do projeto e reinstalar o requirements quando mexer | nenhum: é código nosso |
| Peso de motor | a base baixa quando o motor pedir | download pode ser grande. Separar do tempo de gravação |
| FFmpeg | `winget upgrade` ou instalador oficial | conferir `-version` depois |

Regra de ouro: **nunca atualize a base no dia da gravação.** Atualize um dia antes, rode o teste de
fumaça, e grave com a versão que você já viu funcionar. Se a atualização quebrar algo, volte um
commit e siga com a versão anterior até resolver.

---

## 8. Backup e restauração (ensaio real, não teoria)

```bash
# backup (com o app parado, evita copiar banco em escrita)
cp -r "/c/.../estudio/dados"        "/d/backup-estudio/dados-$(date +%F)"
cp -r "/c/.../estudio/saidas"       "/d/backup-estudio/saidas-$(date +%F)"

# restauracao
# 1. fechar os dois processos
# 2. copiar de volta as pastas
# 3. subir a base, subir a nossa camada, rodar scripts/fumaca.py
```

Ensaio obrigatório antes do vídeo: apagar um arquivo de áudio de propósito, restaurar do backup e
confirmar que ele volta e toca. Backup que nunca foi testado não é backup, é esperança.

---

## 9. Desinstalação e limpeza

| Ação | Como |
|---|---|
| Parar os processos | fechar os dois prompts, ou `taskkill` pelos nomes quando travar |
| Remover peso baixado | apagar a pasta de modelos da base (ela baixa de novo quando precisar) |
| Remover dados do app | apagar `estudio\dados\` (perde perfis e histórico) |
| Remover áudios | apagar `estudio\saidas\audio\` (perde o trabalho: fazer backup antes) |
| Remover o app | apagar a pasta do projeto. Nada é instalado no sistema além das ferramentas |
| Desinstalar a base (se instalou por MSI) | painel de programas do Windows. O desinstalador da base preserva dado por padrão |

---

## 10. Recuperação de problema (o que fazer quando dá errado)

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Tela abre mas tudo dá erro | base fora do ar | subir a base e conferir `/health` |
| Erro de cabeçalho CORS | origem diferente entre tela e base | servir a tela pela nossa camada, mesma origem |
| Código velho sendo servido | processo órfão de `--reload` | matar todos os processos Python e subir um só, sem `--reload` |
| Motor indisponível | pacote do motor não instalado ou peso ausente | ler o motivo em `/api/engines`, instalar e reiniciar a base |
| Primeira geração travando por minutos | download de peso | aguardar, olhar o log, e nunca tratar como travamento de GPU |
| Geração extremamente lenta | GPU abaixo do piso, VRAM tomada, ou caiu para CPU | fechar outro app de GPU, checar `nvidia-smi`, considerar motor mais leve |
| Erro de cuDNN na transcrição | falta cuDNN 8 no ambiente CUDA | usar o motor de transcrição alternativo ou corrigir o ambiente |
| App fecha sozinho no fim de uma transcrição | caso conhecido de descarregamento do motor de fala rápida | usar a variante isolada do motor de transcrição |
| Porta ocupada | outro projeto na mesma porta | trocar a porta por variável e conferir quem está usando |
| Arquivo não aparece na pasta | permissão de escrita ou caminho diferente | conferir `ESTUDIO_SAIDAS` e o log da geração |
| ogg ou opus falha | FFmpeg ausente | instalar FFmpeg e reiniciar |
| Nada funciona e o tempo é curto | pressa | reiniciar a máquina, subir base, subir app, rodar o teste de fumaça. Na ordem |

---

## 11. Checklist de deploy local (20 itens)

- [ ] Pré-requisitos conferidos por comando, um por um
- [ ] Base clonada e com ambiente preparado
- [ ] Base respondendo em `/health`
- [ ] Motor padrão instalado e com peso baixado
- [ ] Motor de qualidade instalado e visível no catálogo
- [ ] FFmpeg instalado e respondendo
- [ ] Nossa camada com ambiente próprio e requirements instalado
- [ ] Nossa tela respondendo em `127.0.0.1:7800`
- [ ] Pasta de dados da base fixada fora do repositório
- [ ] Pastas `dados\` e `saidas\` criadas
- [ ] Nenhuma regra de firewall aberta para 3900 nem 7800
- [ ] Nenhum processo subindo em `0.0.0.0`
- [ ] Atalhos de subida criados (base e app)
- [ ] Teste de fumaça passando de ponta a ponta
- [ ] Arquivo de áudio gerado, aberto e tocado de dentro da pasta
- [ ] Backup feito e restauração ensaiada
- [ ] Log sendo escrito em `dados\logs\`
- [ ] Versão da base anotada no dia da gravação
- [ ] Nenhuma atualização agendada para o dia da gravação
- [ ] Guia curto de instalação escrito para o aluno
