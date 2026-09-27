# Rebuild White V2

## Resultado implementado

A interface web passou a usar uma estrutura clara, monocromática e orientada ao trabalho. A navegação lateral tem 210 px, o topo tem 64 px e a área Gerar prioriza texto, voz, motor, ação e reprodução. O tema claro é o padrão. O tema escuro continua disponível em Configuração.

As sete áreas foram mantidas: Gerar, Clonar, Comparar motores, Desenhar voz, Transcrever, Agente e Configuração. IDs, `data-campo`, rotas e o contrato `window.AREAS` foram preservados.

## Arquivos

- `web/index.html`: remove CDN e serifa, simplifica cabeçalho e marca, carrega apenas o stylesheet V2.
- `web/estilo-v2.css`: novo sistema visual completo, responsivo e sem camada de overrides.
- `web/app.js`: ícones SVG inline, títulos da navegação e migração única do tema legado.
- `web/gerar.js`: remove navegação duplicada, esconde o motor mock, mantém Compor e Histórico e usa player nativo.
- `web/desenhar.js`: título revisado e player nativo.
- `web/comparar.js`: título revisado, mock oculto e players nativos.
- `web/transcrever.js`, `web/agente.js`, `web/config.js`: textos e hierarquia visual revisados.
- `web/LICENCA-TABLER.md`: licença MIT dos ícones inline derivados de Tabler Icons.

## Verificações executadas

- Parser ECMAScript aplicado aos nove arquivos JavaScript: todos válidos.
- Auditoria dos contratos estáticos existentes para Gerar, Clonar, áreas de apoio, Agente, Configuração e shell: todos atendidos.
- Auditoria estrutural do CSS: `[hidden] !important`, foco visível, `prefers-reduced-motion`, fonte local, temas claro/escuro e chaves balanceadas.
- Teste comportamental da migração de tema: preferência escura legada migra uma vez para papel, escolha escura explícita é preservada e uma migração já concluída não se repete.
- Auditoria dos players: nenhuma onda sintética permanece; os resultados usam `<audio controls>`.
- Auditoria de runtime: nenhuma CDN é carregada por `index.html`; o motor `mock` não aparece nas seleções do produto.

## Comandos ainda bloqueados pelo ambiente

O runner desta sessão falhou antes de iniciar qualquer processo com o erro Windows 1920 ao abrir `C:\Users\<usuario>\AppData\Local\Microsoft\WindowsApps\pwsh.exe`. Por isso, estes comandos não foram executados e não são reportados como aprovados:

```powershell
$env:PYTHONPATH = $null
C:\caminho\para\o-venv-do-projeto\Scripts\python.exe -m pytest -q
C:\caminho\para\o-venv-do-projeto\Scripts\python.exe -m ruff check app tests scripts
Get-ChildItem web\*.js | ForEach-Object { node --check $_.FullName }
```

## Screenshots e responsividade

Os breakpoints de 390, 768, 1280 e 1440 px estão definidos no stylesheet. Não foram gerados screenshots do worktree nesta sessão porque o preview em 7820 depende do mesmo runner bloqueado. O servidor em 7800 foi mantido somente para leitura e confirmou servir outra cópia do projeto, portanto não foi usado como evidência do rebuild.

## Limitações verificáveis

- A clonagem permanece em 5 a 30 segundos porque esse é o contrato real em `app/clonar.py` e nos testes atuais. O roteiro externo cita 5 a 15 segundos, mas também proíbe alterar `app/`.
- A fonte usa `@font-face` com fontes locais instaladas e fallback sans. Não há download nem CDN em runtime.
- `web/estilo.css` e `web/estilo-config.css` permanecem no repositório para evitar exclusões, mas não são mais carregados.
- Não houve commit, push, reinício das portas 3900/7800 nem acesso de escrita ao banco real.
