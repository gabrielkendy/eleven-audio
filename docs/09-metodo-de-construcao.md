# 09 · Método de Construção (com IA, por fatias verticais, com o prompt mestre)

> Arquivo 9 de 10 do manual, e o mais importante para quem vai executar. Aqui está o método para
> tirar o Estúdio de Voz Local do papel **sem receber meia obra**: sem botão sem endpoint, sem tela
> que não salva, sem "deve funcionar".
> Padrão do kit: documento-mãe do método, o diagnóstico de por que a IA entrega pela metade, o
> método em passos, o prompt mestre pronto para colar, os anti-padrões e a definição de pronto.
> Adaptação: o caso local, sem login, com um motor de teste e um servidor MCP já pronto na base.

---

## 1. Por que a IA entrega meia obra (o diagnóstico, aplicado a este projeto)

| Causa | Como aparece aqui | Antídoto |
|---|---|---|
| Prompt horizontal | "faz a tela do estúdio" e depois "faz a geração" | fatia vertical: banco, endpoint, tela, ligação e teste na mesma entrega |
| Falta de contrato | a tela inventa um campo que o endpoint não aceita | o PRD é o contrato. Todo botão aponta para um endpoint da lista |
| Sem verificação | a IA diz que gerou áudio e não olhou o disco | o critério é o arquivo tocar, com tempo medido |
| Escopo grande de uma vez | "constrói o estúdio completo com dublagem" | escopo travado: 16 funções do núcleo, o resto vai para próximo vídeo |
| Dependência de peso e download | a IA quer testar e não tem peso baixado | motor de teste (mock) entra na fatia 1 e destrava tudo |
| Login e multiusuário "para depois" | alguém sugere conta para "organizar" | não existe conta neste projeto. Se aparecer sugestão, ela é recusada por escrito |
| Integração com terceiro sem adaptador | chamada de motor direto na rota | adaptador de motor com modo de teste |

---

## 2. A fatia vertical (o tijolo do método)

Uma fatia vertical é uma funcionalidade **completa e testada**, ponta a ponta:

```text
   ┌──────────── FATIA VERTICAL "gerar audio" ────────────┐
   │ 1. Banco: tabela geracao e evento                    │
   │ 2. Endpoint: POST /api/gerar, GET /api/gerar/{id}    │
   │ 3. Tela: area GERAR com todos os estados             │
   │ 4. Ligacao: botao chama o endpoint e mostra o audio  │
   │ 5. TESTE: o arquivo toca no disco, com tempo medido  │
   └──────────────────────────────────────────────────────┘
```

Só depois de a fatia atual tocar áudio de verdade é que a próxima começa. Em qualquer ponto do
projeto, o que existe funciona.

---

## 3. O método em 7 passos (adaptado do kit, para o caso local)

### Passo 1 · Blueprint antes de codar
Entidades com dono e tipo, endpoints com corpo e resposta, telas com botão ligado a endpoint,
integrações com o que é real e o que é teste, e a ordem das fatias. Isso é o PRD mais este manual.
Nenhuma linha de código antes disso.

### Passo 2 · Esqueleto que sobe
Base no ar em 3900 respondendo `/health`, nossa camada no ar em 7800 com `/api/saude` respondendo e
o motor de teste gerando um wav. Antes de qualquer feature, o esqueleto precisa subir e responder.

### Passo 3 · Contrato de dados primeiro
Sete tabelas criadas com migração na subida, mais o espelho de perfil e consentimento. Toda feature
que vier depois nasce gravando e medindo, porque o banco já existe.

### Passo 4 · Fatias verticais, uma por vez
Gerar, clonar, comparar, transcrever, desenhar, agente, fechamento. Cada uma com banco, endpoint,
tela, ligação e teste. Só fecha quando o critério da seção 8.1 estiver marcado.

### Passo 5 · Motor de teste (o mock-first daqui)
Toda a parte de tela e fluxo é construída com o motor `mock`, sem GPU e sem peso. O motor real entra
quando a fatia pede, e o teste de aceitação é sempre com áudio real.

### Passo 6 · Verificar de verdade
Endpoint chamado, arquivo no disco, tempo medido, linha no banco, desconexão de rede conferida.
"Deve funcionar" é proibido.

### Passo 7 · Empacotar cedo e incremental
Atalhos de subida, guia curto do aluno, backup ensaiado. Empacotar no fim dá erro em cima de erro.

---

## 4. PROMPT MESTRE (preenchido, pronto para colar no agente de código)

```text
Voce vai construir o ESTUDIO DE VOZ LOCAL, uma ferramenta de voz que roda na maquina do usuario,
SEM LOGIN, sem nuvem e sem cobranca. Ela NAO constroi motor de voz: ela orquestra a base
VoiceStudio, que ja esta clonada e funcional na pasta indicada.

ARQUITETURA OBRIGATORIA:
- Base: VoiceStudio em C:\...\4-BASE-VOICESTUDIO (AGPL-3.0). NAO modificar nenhum arquivo dela.
  Ela expoe: POST /api/generate, GET /api/engines, /api/profiles, /api/transcribe,
  /api/design/describe, /api/mcp/bindings, /mcp/ (MCP), /v1/* (padrao OpenAI), GET /health.
  Ela sobe em 127.0.0.1:3900.
- Camada fina nossa (o que voce escreve): FastAPI em 127.0.0.1:7800, servindo a tela e /api/*.
  Arquivos: app/servidor.py, app/rotas.py, app/motor.py, app/base.py, app/cofre.py,
  app/saidas.py, app/tarefas.py, app/agente.py, app/config.py, app/log.py.
- Motor por adaptador: omnivoice (padrao), voxcpm2 (qualidade), indextts (emocao, 2a fase),
  mock (tom de 440 Hz, sem GPU, sempre disponivel).
- Banco: SQLite em dados/estudio.db, com migracao na subida. SETE tabelas: perfil_voz,
  consentimento, geracao, transcricao, vinculo_agente, configuracao, evento.
- Armazenamento: audio sempre em arquivo. saidas/audio/ com nome
  AAAA-MM-DD_HHMMSS_motor_perfil.wav. NUNCA audio no banco.
- Configuracao 100% por variavel de ambiente com padrao. NADA de caminho absoluto no codigo.
- NADA de login, conta, senha, token de nuvem, cobranca, telemetria ou credencial de servico.

ENTIDADES (do PRD, com campo e tipo):
[colar a tabela da secao 3.1 do PRD]

ENDPOINTS NOSSOS (17): estado, motores, motores/ativo, gerar, gerar/{id}, saidas, clonar, perfis,
perfis/{id} (DELETE), desenhar, transcrever, agente/status, agente/ligar, agente/desligar,
config, saude.
[colar a tabela da secao 4.2 do PRD]

TELAS (uma tela, 4 areas + rodape + bloco de agente):
GERAR, CLONAR, DESENHAR, TRANSCREVER, RODAPE DE ESTADO, AGENTE.
[colar a tabela da secao 5.1 do PRD]

REGRAS DE EXECUCAO (siga a risca):
1. Construa por FATIAS VERTICAIS COMPLETAS, na ordem do PRD: FATIA 0 ate FATIA 7.
   NUNCA faca "todas as telas" nem "todo o backend" separados.
2. Comece pelo esqueleto que sobe: base no ar, nossa camada no ar, motor de teste gerando wav.
3. Depois o banco com as sete tabelas e a migracao.
4. Para CADA fatia: ao terminar, TESTE de verdade (chame o endpoint, abra o arquivo, mostre o
   tempo medido) e liste o que testou. Sem isso, a fatia nao esta pronta.
5. Use o motor de teste sempre que a tarefa for tela, fila, banco ou erro. Use motor real so no
   teste de aceitacao da fatia.
6. Consentimento bloqueia clonagem. Sem aceite gravado, POST /api/clonar devolve 409.
7. Transcricao do clipe de referencia e obrigatoria na criacao do perfil (gere e salve se a
   pessoa nao digitar). Isso evita transcricao completa em cada geracao.
8. Todo erro aparece em portugues, com o motivo literal vindo da base preservado.
9. Toda geracao grava: motor, texto, arquivo, duracao do audio, tempo de parede, dispositivo,
   tamanho e status. Tempo e MEDIDO, nunca estimado.
10. Nada de segredo no codigo. Nada de caminho absoluto. Nada de cor fixa no componente.
11. Ao final de cada fatia, escreva: o que foi feito, como foi testado, o que ficou faltando.
12. Se algo do recorte nao for possivel com a base, DIGA na hora. Nao invente caminho.

NAO ENTREGUE CASCA: todo botao chama endpoint real, todo endpoint grava no banco, toda area da
tela tem estado de carregando, vazio e erro.
```

---

## 5. O prompt de uma fatia (o formato que se repete nas 8 fatias)

```text
FATIA N: <nome da fatia>

ENTREGA: <o que existe no fim, em uma frase>
BANCO: <tabelas envolvidas>
ENDPOINTS: <lista, com metodo e rota>
TELA: <area e componentes, com os estados>

FAZER NESTA ORDEM:
1. banco (ou ajuste de banco) com migracao
2. endpoint com validacao e mensagem em portugues
3. tela com estados de carregando, vazio e erro
4. ligacao real do botao com o endpoint
5. teste de aceitacao: <como provar>

TESTE DE ACEITACAO: <passos exatos, com o arquivo que precisa existir e o tempo que precisa
estar medido>

NAO FACA: <o que extrapolaria o escopo desta fatia>
```

### 5.1 Exemplo preenchido (FATIA 2, clonar voz)

```text
FATIA 2: clonagem a partir de clipe de 5 a 15 segundos

ENTREGA: area CLONAR funcionando, com consentimento bloqueante, perfil criado na base e espelhado
no nosso banco, e geracao de teste na voz clonada.
BANCO: perfil_voz, consentimento, geracao (com perfil_id)
ENDPOINTS: POST /api/clonar, GET /api/perfis, DELETE /api/perfis/{id} (nosso);
           POST /api/profiles, POST /api/profiles/{id}/consent, GET /api/profiles,
           DELETE /api/profiles/{id} (base)
TELA: campo de nome, entrada de clipe (subir ou gravar), medidor de duracao com aviso fora da
      faixa de 5 a 15 s, campo de transcricao, aviso de consentimento bloqueante, botao clonar,
      previa comparativa (original contra clonada), lista de perfis com apagar.

FAZER NESTA ORDEM:
1. tabelas perfil_voz e consentimento com migracao e indice unico de consentimento
2. endpoint POST /api/clonar: valida nome, valida aceite, grava clipe em dados/referencias/,
   corta acima do limite do motor, chama a base com kind=clone, transcreve se faltar texto,
   chama o consentimento na base e grava o espelho
3. tela com todos os estados, inclusive "sem perfil" e "perfil sem consentimento"
4. botao de apagar perfil removendo dos dois lados e limpando o clipe
5. teste de aceitacao abaixo

TESTE DE ACEITACAO: gravar um clipe de 10 segundos, clonar, gerar a mesma frase no motor padrao,
ouvir o original e o clonado, e conferir no banco: perfil gravado, consentimento com data e hora,
transcricao salva, geracao com duracao de audio e tempo de parede medidos.

NAO FACA: modo profissional (treino longo), dublagem, mistura de vozes, ou qualquer ajuste no
codigo da base.
```

---

## 6. Anti-padrões (o que faz a obra sair pela metade, e o antídoto)

| Anti-padrão | Por que é ruim | Antídoto |
|---|---|---|
| "Cria o estúdio inteiro" | escopo gigante, entrega rasa | uma fatia por vez, com critério |
| "Faz a tela" e depois "faz o backend" | metades que não se encaixam | fatia vertical |
| Copiar código da base para dentro do nosso | problema de licença e dívida dupla | só API local, nunca código copiado |
| Chamar motor direto na rota | amarra o produto a um motor | adaptador com modo de teste |
| Testar com mock e chamar de pronto | número falso de qualidade | aceitação sempre com motor real |
| Guardar áudio no banco | backup lento, corrupção | áudio é arquivo |
| Caminho absoluto no código | quebra ao mover a pasta | `pathlib` mais variável de ambiente |
| Esconder erro em inglês | a pessoa não sabe o que fazer | traduzir com motivo literal preservado |
| Ligar compartilhamento de rede "para facilitar" | expõe a máquina | loopback por padrão, PIN só por sessão |
| Prometer qualidade de nuvem | mentira que o vídeo expõe | admitir o limite e mostrar o ganho real |
| Clonar voz sem consentimento | ilegal e antiético | bloqueio no produto e no roteiro |
| Atualizar a base no dia da gravação | quebra na frente da câmera | atualizar antes, testar, congelar |

---

## 7. Como pedir de volta (o que exigir da IA a cada entrega)

Ao final de cada fatia, o relatório tem que responder, nesta ordem:

1. O que foi feito (arquivos criados e alterados, com caminho).
2. Como foi testado (comando rodado e saída real, não descrição).
3. Qual arquivo de áudio existe no disco e quanto tempo levou.
4. O que ficou faltando e por quê.
5. O que seria o próximo passo.

Se o relatório não tem comando e saída real, não é entrega, é promessa.

---

## 8. Definição de pronto

### 8.1 Por fatia (copiar e marcar a cada entrega)

- [ ] Migração rodando na subida e idempotente
- [ ] Endpoint chamado de verdade, com resposta real registrada
- [ ] Validação de entrada com mensagem em português
- [ ] Tela com estado de carregando, vazio e erro
- [ ] Botão ligado ao endpoint, sem caminho falso
- [ ] Arquivo de áudio no disco com nome legível
- [ ] Arquivo aberto e tocado
- [ ] Duração de áudio e tempo de parede medidos
- [ ] Linha gravada no banco com motor, dispositivo e status
- [ ] Erro da base traduzido com motivo literal preservado
- [ ] Nada de caminho absoluto no código
- [ ] Nada de segredo no código
- [ ] Nada de cor fixa no componente
- [ ] Nada escrito na pasta da base
- [ ] Teste de fumaça atualizado e passando
- [ ] Relatório da fatia com comando e saída real
- [ ] Print ou gravação guardada para o vídeo

### 8.2 Do produto (antes de gravar)

- [ ] Fluxo inteiro roda sem terminal aberto na frente da câmera
- [ ] Comparação de motores com áudio real dos dois
- [ ] Agente respondendo falando na voz clonada
- [ ] Transcrição acertando o texto gerado
- [ ] Desenho de voz produzindo vozes distintas
- [ ] Consentimento bloqueando de verdade
- [ ] Rodapé com dispositivo, motor ativo e tempo medido
- [ ] Nenhuma chamada externa durante o uso
- [ ] Guia do aluno escrito
- [ ] Licenças visíveis na tela

---

## 9. Ordem de execução recomendada (8 sessões de trabalho)

| Sessão | Fatia | Saída da sessão |
|---|---|---|
| 1 | FATIA 0 | base no ar, health respondendo, áudio de teste tocando |
| 2 | FATIA 1 | tela com área GERAR funcionando, 3 áudios gerados com tempos medidos |
| 3 | FATIA 2 | clonagem funcionando com consentimento e prévia comparativa |
| 4 | FATIA 3 | comparação de motores com a mesma voz, dois arquivos lado a lado |
| 5 | FATIA 4 | transcrição funcionando e conferida contra o texto original |
| 6 | FATIA 5 | desenho de voz com dois exemplos distintos |
| 7 | FATIA 6 | agente falando na voz clonada, com vínculo e arquivo em disco |
| 8 | FATIA 7 | pasta organizada, medições no relatório, guia do aluno e ensaio do roteiro |

Regra de calendário: uma sessão, uma fatia. Fatia que atravessa duas sessões costuma ser fatia mal
recortada, e o ajuste é reduzir o escopo da fatia, não estender o prazo.

---

## 10. Checklist do método (20 itens)

- [ ] Blueprint aprovado antes da primeira linha de código
- [ ] Esqueleto que sobe antes de qualquer feature
- [ ] Banco com migração antes das features
- [ ] Oito fatias recortadas, com entrega e teste escritos
- [ ] Motor de teste disponível desde a primeira fatia
- [ ] Cada fatia com teste de aceitação em passos exatos
- [ ] Relatório de fatia com comando e saída real
- [ ] Nenhum prompt horizontal ("faz tudo", "faz a tela")
- [ ] Nenhuma cópia de código da base para dentro do projeto
- [ ] Nenhuma promessa de qualidade antes de medir
- [ ] Degrau de qualidade medido por motor, com número no relatório
- [ ] Comparação de motores gravada para o vídeo
- [ ] Consentimento testado com recusa e com aceite
- [ ] Teste de fumaça rodando antes de cada gravação
- [ ] Backup ensaiado antes de gravar
- [ ] Base congelada na versão testada no dia da gravação
- [ ] Guia do aluno escrito com o mesmo passo a passo validado
- [ ] Armadilhas registradas no arquivo 10 deste manual
- [ ] Roteiro do vídeo amarrado às fatias (uma fatia, uma cena)
- [ ] Nada de login, nuvem ou cobrança em nenhuma entrega
