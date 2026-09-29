# 06 · Segurança (local, sem login, sem descuido)

> Arquivo 6 de 10 do manual. O projeto não tem login, e isso **não** quer dizer que não tem
> segurança. Quer dizer que a segurança mudou de lugar: saiu da tela de entrar e foi para a
> arquitetura (loopback), para o consentimento (voz) e para as licenças (uso).
> Padrão do kit: gates, RBAC e segredos. Adaptação: onde o kit fala de JWT e multitenant, aqui se
> fala de loopback, PIN de sessão, chave de API da base e fronteira de arquivo do MCP.

---

## 1. O modelo de segurança em uma página

```text
CAMADA                O QUE PROTEGE                       PADRAO DE FABRICA
--------------------- ----------------------------------- -------------------------
Rede                  nada exposto. Backend em 127.0.0.1   loopback (sem porta aberta)
Acesso remoto         PIN de rede de 6 digitos por sessao ligado na mao, nunca sozinho
Acesso de script      chave de API (OMNIVOICE_API_KEY)    desligada
Rede confiavel        CIDR isenta consumo, nunca admin    vazio
Administracao         /system/* e /api/settings/*         so loopback de verdade
Arquivo (MCP)         OMNIVOICE_MCP_BASE_PATH             sem base path, caminho e recusado
Voz                   consentimento antes de clonar       exigido pela nossa tela + base
Uso comercial         licenca de cada motor               avisada na tela
Segredo               nao existe segredo no recorte       nenhum
Dado do usuario       pasta local, sem nuvem              sem sincronizacao
```

Frase que resume: **a segurança deste projeto é não expor, não guardar, não fingir.**

---

## 2. As duas portas da base (o que liga o quê)

| Porta | Como liga | O que guarda | O que NÃO guarda | Fonte |
|---|---|---|---|---|
| PIN de rede | tela de compartilhamento, por sessão | convidado casual na mesma rede | não guarda admin, não guarda WebSocket de ditado | `docs/sharing.md`, `docs/api-auth.md` |
| Chave de API | variável `OMNIVOICE_API_KEY` no backend | cliente HTTP e WebSocket fora do loopback | não substitui o loopback de verdade para admin no desktop | `docs/api-auth.md` |
| Rede confiável | `OMNIVOICE_TRUSTED_NETWORKS` com CIDR | nada. Isenta consumo de PIN e chave | nunca isenta admin | `docs/api-auth.md` |

Regras operacionais que entram no vídeo:

1. Compartilhamento nunca liga sozinho. Ele morre quando o app fecha ou quando a pessoa desliga.
2. PIN é de 6 dígitos, gerado novo a cada vez, e **nunca** vai para o disco.
3. PIN não é senha de administração e não pode ser tratado como tal.
4. Chave de API nunca vai em URL (`?api_key=` vaza em log e em histórico). Vai em cabeçalho.
5. Chave em rede sem criptografia é chave entregue. Fora da rede de casa, só com túnel ou TLS.
6. CIDR confiável é decisão de rede controlada, não atalho de conveniência.

---

## 3. Superfície de administração (a parte que executa código)

`/system/*` (inclui `set-env`) e `/api/settings/*` são classificados na própria base como
**RCE class**, ou seja, uma chamada ali pode mudar o ambiente do processo, instalar ou remover
motor e mexer em caminho. No app de mesa, essas rotas são **loopback de verdade**: nem PIN, nem
chave, nem CIDR alcançam de outra máquina.

O caso que virou lição (issue real da base, #1213): em server mode, com chave definida **e** CIDR
confiável configurado, um cliente da rede podia chamar `POST /system/set-env` sem credencial
nenhuma, porque o middleware de chave liberava aquilo como host local. Correção: o portão de admin
passou a ser independente das isenções de consumo.

Lição escrita para o aluno: **portão de consumo e portão de administração são portões diferentes.**
Quem mistura os dois abre buraco e não percebe.

Nossa postura no recorte: a nossa camada fina nunca chama rota de admin da base. Se um dia
precisar (por exemplo, ligar um motor), faz por instrução explícita na tela, do loopback, com o
texto do comando visível para a pessoa.

---

## 4. CORS, WebSocket e bilhete de uso único

| Assunto | Regra real | O que a gente faz |
|---|---|---|
| CORS | lista padrão só com loopback e origens do app de mesa. Origem diferente = bloqueio (issue #1348) | servir a nossa tela pela nossa própria camada, na mesma origem, e não brigar com CORS |
| WebSocket de ditado | tem guarda própria além do middleware. PIN não autoriza ditado | não usar ditado de fora do loopback no primeiro dia |
| Bilhete de WebSocket | `POST /api/auth/ws-ticket`, preso a um caminho, validade de 30 s, uso único | não implementar no primeiro dia. Se precisar, usar o do próprio app da base |
| Cookie de sessão | `ov_session`, HttpOnly, SameSite=Strict, teto de 8 h | a nossa camada não usa cookie de sessão da base |
| CSRF | cookie autenticado exige `Origin` exata e `X-VoiceStudio-CSRF: 1` | não se aplica: a nossa camada não usa cookie de terceiro |
| Limite de tentativa | 10 tentativas de troca de sessão por cliente em 60 s, depois 429 | não se aplica no loopback |

---

## 5. Consentimento de voz (a regra mais importante do produto)

O alvo exige verificação de voz antes de liberar clonagem. A gente copia o cuidado, na versão local
e registrada.

| Item | Definição |
|---|---|
| Quando aparece | antes de qualquer clonagem, bloqueando o botão |
| O que pergunta | a voz é sua, ou você tem autorização de quem é dono |
| O que grava | texto literal aceito, origem declarada (`propria` ou `autorizada`), data e hora |
| Onde grava | no nosso banco (`consentimento`) e no perfil da base (`POST /api/profiles/<id>/consent`) |
| Como revoga | botão de revogar, que apaga na base e marca no nosso banco, mais botão de apagar perfil |
| O que bloqueia | geração com perfil sem consentimento devolve 409 e a tela explica |
| O que entra no vídeo | a régua: clonar voz só com autorização. Voz de pessoa pública nunca para fingir fala alheia |

Texto do aviso (idêntico ao PRD e à tela):

```text
Antes de clonar, confirme: esta voz e sua, ou voce tem autorizacao de quem e dono.
Clonar voz de terceiro sem autorizacao e ilegal e antiético.
O audio que voce gerar e seu, mas cada motor tem licenca propria. Leia antes de uso comercial.
```

Declaração de uso de IA: quando o áudio gerado for publicado (vídeo, peça, anúncio), declarar que a
voz é sintética, sempre que o contexto pedir. A base tem recurso de marca d'água no áudio, e ele
fica como opção de segunda fase.

---

## 6. Licenças (o "segredo" que realmente importa aqui)

| Componente | Licença | O que a pessoa pode e não pode |
|---|---|---|
| Base VoiceStudio | AGPL-3.0 | usar local à vontade. Modificar e oferecer como serviço de rede exige publicar o código |
| Nossa camada fina | a definir (sugestão MIT) | pode ser publicada com licença própria |
| Motores e pesos | licença própria de cada projeto | ler antes de uso comercial do áudio gerado |
| FFmpeg | LGPL ou GPL conforme o build | escolher build compatível com o uso pretendido |

Regra que evita dor de cabeça no vídeo e para o aluno: **nunca dizer que o áudio é "livre de tudo".**
O áudio é do usuário, respeitando a licença do motor usado. É a mesma distinção que o alvo vende
como licença comercial, só que aqui de graça e em texto claro.

---

## 7. Segredos e dados (o que este projeto não tem, e por quê)

| Item | Existe aqui | Motivo |
|---|---|---|
| Senha de usuário | não | não existe conta |
| Token de serviço de nuvem | não | não existe nuvem no recorte |
| Chave de API nossa | não | nada fora da máquina chama a nossa camada |
| Chave de API da base | opcional e local | só se um dia expor para a rede, e aí é decisão explícita |
| Cookie de sessão | não | não existe sessão |
| Telemetria | não | não existe coleta. Se um dia existir, é opt in com texto claro |
| Dado enviado para fora | não | a promessa do produto é essa. Tem teste de verificação no checklist |

Teste de verificação da promessa (entra no checklist e no vídeo): com o app gerando áudio, olhar o
monitor de rede e confirmar que **nenhuma** conexão externa sai da máquina, exceto o download de
peso de motor, que é etapa explícita de instalação.

---

## 8. Matriz de ameaças do dia a dia

| Ameaça | Como acontece | Dano | Mitigação |
|---|---|---|---|
| Wi-Fi público com compartilhamento ligado | PIN em HTTP puro, observável na rede | alguém usa a sua GPU | não ligar compartilhamento em rede pública. Preferir Tailscale |
| Outro aparelho da casa curioso | PIN é de 6 dígitos | uso indevido da API | desligar compartilhamento quando não estiver usando |
| Navegador com extensão maliciosa | extensão chama a API local | geração indevida | a API local é da máquina. Vale a mesma regra de qualquer ferramenta local: usar navegador limpo |
| Clipe de voz sensível esquecido | referência fica na pasta | vazamento de voz de terceiro | apagar referência depois do uso, botão na tela |
| Pasta sincronizada em nuvem | Drive e Dropbox pegando a pasta de áudio | voz sai da máquina | manter `saidas\` e `dados\` fora de pasta sincronizada |
| Peso de modelo baixado de origem duvidosa | instalação por fora do caminho oficial | código executável desconhecido | instalar pelo pip oficial e pelo catálogo da base |
| Expor a base na internet | `OMNIVOICE_BIND_HOST=0.0.0.0` e abrir no roteador | execução de código pela admin | não fazer. Não existe caso de uso no recorte |
| Chave de API em print de vídeo | print com a variável visível | credencial vazada | mostrar só no terminal limpo e rotacionar se aparecer |
| Áudio gerado usado para enganar | má fé do usuário | dano real e dano ao canal | régua explícita no vídeo e aviso no produto |
| Backup copiado com voz de terceiro | backup leva referência junto | vazamento por descuido | avisar na tela e documentar o que entra no backup |

---

## 9. Checklist de segurança (20 itens)

- [ ] Nossa camada sobe em `127.0.0.1`, nunca em `0.0.0.0`
- [ ] Base sobe em loopback (padrão de fábrica confirmado antes de gerar)
- [ ] Compartilhamento de rede desligado por padrão e por sessão
- [ ] PIN nunca escrito em disco (confirmado no comportamento da base)
- [ ] Nenhuma chave de API em URL, só em cabeçalho
- [ ] Nenhum segredo em arquivo de código ou de configuração do repositório
- [ ] Nenhum token de serviço de nuvem no projeto
- [ ] Nenhuma chamada externa durante o uso normal (verificado no monitor)
- [ ] Nenhuma rota de admin da base chamada pela nossa camada
- [ ] Fronteira do MCP definida (`OMNIVOICE_MCP_BASE_PATH`) quando usar modo arquivo
- [ ] `OMNIVOICE_MCP_OUTPUT_MODE=files` para não jogar áudio no contexto do agente
- [ ] Consentimento bloqueante antes de clonar
- [ ] Consentimento gravado nos dois lugares, com data e hora
- [ ] Revogação de consentimento e apagar perfil funcionando
- [ ] Clipe de referência apagável com um clique
- [ ] Pasta de áudio fora de pasta sincronizada em nuvem
- [ ] Aviso de licença dos motores visível na tela
- [ ] Declaração de IA documentada no roteiro do vídeo
- [ ] Nenhum dado do usuário saindo da máquina
- [ ] Régua ética escrita (clonar só com autorização) no produto e no vídeo
