# 10 · Checklist e Pontos de Atenção (perrengues reais)

> Arquivo 10 de 10 do manual, e o que fica aberto na segunda tela durante a gravação.
> Padrão do kit: cada armadilha com sintoma e solução, e a lista final de "pronto para gravar".
> Aqui entram as armadilhas do kit de referência (que continuam valendo) e as armadilhas específicas
> deste projeto: GPU, motor local, clonagem, MCP e caminho com acento.

---

## 1. Armadilhas de backend e ambiente

| Problema (real) | Sintoma | Solução |
|---|---|---|
| `uvicorn --reload` no Windows | código velho sendo servido, rota nova dando 404 | matar todos os processos Python e subir UM processo sem `--reload`. Reiniciar na mão |
| Variável obrigatória lida no import (`os.environ["X"]`) | subida quebra se a variável faltar | `os.environ.get("X", padrao)` e validação na subida com mensagem clara |
| Falta de `import` no topo do arquivo | erro 500 na primeira chamada real | import sempre no topo, e testar a rota logo depois de editar |
| Caminho com acento e espaço | comando quebrado e caminho cortado | aspas no shell e `pathlib` no código. Nunca concatenar caminho na mão |
| Porta ocupada (3900 ou 7800) | abre o endereço e aparece outro projeto | conferir quem está na porta antes de subir, e trocar por variável de ambiente |
| Nome de arquivo com acento ou emoji | erro de codificação em ferramenta externa | sanitizar nome para ASCII, mantendo data, motor e perfil |
| Dois processos mexendo no mesmo SQLite | erro de banco travado | uma instância por vez, modo WAL ligado, e fechar antes de mexer em arquivo |
| Timeout único para tudo | geração em CPU estoura antes de terminar | tempos distintos: fila 1800 s, acelerado 300 s, CPU 600 s, transcrição 300 s |
| Log sem data e sem hora | impossível casar erro com gravação | log com data e hora em `dados\logs\`, um arquivo por dia |

---

## 2. Armadilhas de GPU e de motor local (as específicas deste projeto)

| Problema (real) | Sintoma | Solução |
|---|---|---|
| VRAM abaixo do piso do motor padrão | render que devia levar segundos leva minutos e estoura o orçamento | o piso do motor padrão é de 6 GB. Abaixo disso, usar variante GGUF ou motor mais leve |
| GPU tomada por outro app (jogo, editor, navegador com vídeo) | erro de memória e queda para CPU | fechar o outro app e conferir com `nvidia-smi` antes de gravar |
| Primeira geração demorada | parece travado, mas é download de peso (cerca de 2,3 GB no motor padrão) | tratar como etapa "baixando peso", com log visível. Ideal: baixar antes de gravar |
| Transcrição falha em ambiente CUDA | erro de cuDNN 8 ausente, e o motor se declara indisponível | usar o motor de transcrição alternativo ou corrigir o ambiente |
| App fecha sozinho no fim de uma transcrição | caso conhecido de descarregamento da biblioteca de fala rápida | usar a variante isolada do motor de transcrição |
| Motor aparece indisponível sem motivo claro | o motivo mostrado é deliberadamente genérico | ler `/api/engines` e, se o motivo vier vazio, instalar o pacote do motor e reiniciar |
| Clipe longo com transcrição | erro `[clone_ref_too_long]` | cortar o clipe para até o limite do motor (20 s no padrão, 30 s no VoxCPM2) e casar transcrição e áudio |
| Transcrição faltando no perfil | cada geração roda transcrição completa e fica lenta | exigir transcrição do clipe na criação do perfil (ou gerar e salvar uma vez) |
| Cache de prompt no disco | primeira geração após reinício mais lenta sem explicação | é comportamento normal (referências longas ranqueiam janela uma vez). Existe variável para manter só em memória |
| Italiano ou texto com acento decomposto | fala distorcida | a base já normaliza o texto (correção da issue #502). Se aparecer distorção, conferir a versão da base |
| Trocar motor e nada mudar | a variável de ambiente da base vence a escolha da interface | conferir `OMNIVOICE_TTS_BACKEND`. Variável manda |

---

## 3. Armadilhas de integração (MCP, API local e arquivo)

| Problema (real) | Sintoma | Solução |
|---|---|---|
| `/mcp` sem barra no fim em versão antiga | erro 405 | usar `/mcp/` com a barra. Funciona em toda versão |
| Áudio em base64 dentro do contexto do agente | conversa inflada e cara em token | `OMNIVOICE_MCP_OUTPUT_MODE=files` para virar caminho em disco |
| Caminho fora da fronteira do MCP | recusa de leitura com motivo | definir `OMNIVOICE_MCP_BASE_PATH` e manter tudo dentro dele |
| Agente em outro host | handshake recusado pela guarda de DNS rebinding | `OMNIVOICE_MCP_ALLOWED_HOSTS` em rede confiável, ou usar o adaptador stdio |
| Interface em outra origem | tela abre e nada carrega, erro de CORS | servir a tela pela nossa camada (mesma origem). Se não der, declarar origem exata |
| Cotar o PIN como segurança de admin | alívio falso | PIN não libera admin. Admin é loopback de verdade no app de mesa |
| Ditado de fora do loopback | handshake fechado com código 1008 | ditado exige rede confiável ou chave. Não tentar no primeiro dia |
| FFmpeg ausente | só ogg e opus falham | manter wav funcionando e avisar o que instalar |
| Chave de API em URL | credencial vazando em log e histórico | sempre em cabeçalho `Authorization` |
| Chamada externa "invisível" | promessa de privacidade furada | monitor de rede aberto no teste de aceitação. Só download de peso sai |

---

## 4. Armadilhas de tela e de conteúdo

| Problema (real) | Sintoma | Solução |
|---|---|---|
| Erro em inglês na cara do usuário | a pessoa não sabe o que fazer | tradução com motivo literal preservado |
| Botão sem estado de erro | pessoa clica várias vezes e piora | todo botão com parado, rodando, pronto e erro |
| Player sem botão de baixar | arquivo existe e ninguém acha | botão de baixar e botão de abrir pasta no mesmo bloco |
| Contador de caractere ausente | erro de limite só no fim | contador e corte com aviso na hora |
| Cor fixa no componente | trocar a cara vira caça ao tesouro | cor por variável CSS, sempre |
| Marca de terceiro no produto | problema de identidade e de licença | nenhum logo e nenhum nome de terceiro na nossa tela |
| Print de tela do alvo usado como se fosse nossa | confusão de público e risco de marca | comparar lado a lado, com legenda dizendo de quem é cada tela |
| Texto do roteiro longo demais para a cena | vídeo arrastado | uma fatia, uma cena, uma frase de conclusão |

---

## 5. Armadilhas de processo, backup e gravação

| Problema (real) | Sintoma | Solução |
|---|---|---|
| Atualizar a base no dia da gravação | quebra na frente da câmera | atualizar antes, rodar o teste de fumaça e congelar a versão |
| Backup nunca testado | na hora do aperto não volta | ensaiar: apagar um áudio, restaurar, confirmar que toca |
| Pasta de áudio dentro de pasta sincronizada | voz sai da máquina sem intenção | manter `saidas\` e `dados\` fora de Drive e Dropbox |
| Clipe de referência esquecido | dado sensível de voz parado no disco | apagar referência depois do uso ou apagar o perfil inteiro |
| Print com caminho ou dado sensível | vazamento no vídeo | revisar print antes de publicar, e mostrar só o que interessa |
| Gravar sem medir | vídeo sem número | tabela de medições aberta durante a gravação |
| Prometer mais do que o teste mostrou | crédito perdido com o público | falar só o que apareceu na tela e no arquivo |
| Rotina de limpeza nunca rodada | disco cheio no meio da gravação | rodar limpeza e conferir espaço antes de gravar |

---

## 6. CHECKLIST FINAL · "estúdio pronto para gravar"

### Fundação

- [ ] Base no ar em `127.0.0.1:3900` com `/health` respondendo
- [ ] Nossa camada no ar em `127.0.0.1:7800` com `/api/saude` respondendo
- [ ] Motor padrão instalado e com peso baixado
- [ ] Motor de qualidade instalado e visível no catálogo
- [ ] Motor de teste gerando wav válido
- [ ] Sete tabelas criadas com migração idempotente
- [ ] Nenhum processo subindo em `0.0.0.0`
- [ ] Nenhuma regra de firewall aberta

### Features (por fatia)

- [ ] FATIA 0: base subindo e áudio de teste tocando
- [ ] FATIA 1: gerar áudio com escolha de motor, 3 arquivos medidos
- [ ] FATIA 2: clonar voz de clipe de 10 s, com consentimento e prévia
- [ ] FATIA 3: comparação de dois motores com a mesma voz
- [ ] FATIA 4: transcrição conferida contra o texto original
- [ ] FATIA 5: desenho de voz com dois exemplos distintos
- [ ] FATIA 6: agente falando na voz clonada, com arquivo em disco
- [ ] FATIA 7: pasta organizada, medições e guia do aluno
- [ ] Toda área da tela com carregando, vazio e erro
- [ ] Todo botão ligado a endpoint real

### Integrações

- [ ] `/mcp/` respondendo com as sete ferramentas
- [ ] Vínculo de voz por agente criado e visível
- [ ] `OMNIVOICE_MCP_OUTPUT_MODE=files` ligado
- [ ] `OMNIVOICE_MCP_BASE_PATH` definido
- [ ] Porta `/v1/audio/speech` respondendo no padrão OpenAI
- [ ] FFmpeg instalado e usado em duração e corte
- [ ] Cada integração com teste de aceitação registrado
- [ ] Nenhuma integração de nuvem ligada

### Segurança e ética

- [ ] Consentimento bloqueando clonagem sem aceite
- [ ] Consentimento gravado nos dois lados, com data e hora
- [ ] Revogação e apagar perfil funcionando
- [ ] Nenhuma chamada externa durante o uso (verificado no monitor)
- [ ] Nenhum segredo em arquivo do projeto
- [ ] Licenças visíveis na tela, com aviso de uso comercial
- [ ] Régua de clonagem no roteiro (só com autorização)
- [ ] Declaração de uso de IA definida para o vídeo

### Deploy local e operação

- [ ] Atalhos de subida criados e testados
- [ ] Teste de fumaça passando de ponta a ponta
- [ ] Backup feito e restauração ensaiada
- [ ] Log escrito em `dados\logs\`
- [ ] Espaço em disco conferido
- [ ] Versão da base anotada
- [ ] Nenhuma atualização agendada para o dia da gravação
- [ ] Guia curto do aluno escrito

### Pós-gravação

- [ ] Pastas de saída organizadas e limpas para o vídeo
- [ ] Tabela de medições fechada (tempo, duração, tamanho, motor)
- [ ] Prints revisados (sem dado sensível e sem caminho absoluto aparente)
- [ ] Clipe de referência apagado ou guardado com decisão explícita
- [ ] Números do vídeo conferidos contra os números do dossiê
- [ ] Rotina de limpeza rodada
- [ ] Repositório do projeto commitado, com o guia do aluno atualizado

---

## 7. As 12 regras que resumem tudo

1. Local por padrão. Loopback é a resposta, não a restrição.
2. A base se orquestra, não se modifica.
3. Motor entra por adaptador e tem modo de teste.
4. Áudio é arquivo, e o banco guarda só o registro.
5. Uma fatia completa antes da próxima.
6. "Deve funcionar" não existe: arquivo tocando, tempo medido, linha no banco.
7. Erro em português, com motivo literal preservado.
8. Consentimento antes de clonar, sempre, com data e hora.
9. Nada de segredo, nada de caminho absoluto, nada de cor fixa.
10. Não prometer mais do que o teste mostrou.
11. Backup ensaiado, versão congelada no dia da gravação.
12. Uma fatia, uma cena, uma frase de conclusão.

> **A regra que resume o manual inteiro:** construa em fatias verticais completas, com o motor de
> teste destravando o caminho, loopback como padrão de segurança e verificação de verdade antes de
> dizer "pronto". É isso que separa um estúdio que funciona de uma tela bonita que não gera áudio.
