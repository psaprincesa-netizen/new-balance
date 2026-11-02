# Continuidade solicitada

O usuário pediu para continuar editando quando retornar e completar as ferramentas da plataforma unificada. Usar `recursos.md` e os documentos/backlog fornecidos como referência de cobertura; não apresentar funcionalidades planejadas como disponíveis.

## Prioridade atual

Manter a plataforma abrindo em https://new-balance-pi.vercel.app e preservar os dados existentes no Neon. O erro 500 de inicialização foi causado pelo método `handle_request` da aplicação, sobrescrito pelo wrapper do runtime Vercel. A aplicação passou a usar `dispatch_application_request`; o teste HTTP de implantação cobre a colisão com o método reservado do runtime.

## Próximas entregas por módulo

1. Núcleo comum: auditoria administrativa e cotas. Rascunhos, comentários e acessos listáveis foram implementados.
2. Documentos e planilhas: ampliar fidelidade de Office, paginação, fidelidade avançada de imagens/Office, pivôs nativos XLSX e conectores. Abas, motor de fórmulas e intercâmbio Office já foram adicionados.
3. Apresentações e diagramas: mestre, áudio/vídeo, animações e bibliotecas de diagramas. Imagens, caixas de texto, formas, camadas e PPTX visual foram adicionados aos slides; conectores e canvas aos diagramas.
4. Projetos, agenda, formulários e tabelas: dependências, convites, quizzes, relacionamentos. Subtarefas, ocorrências repetidas, ICS, coleta pública e tipos de campos foram adicionados.
5. Colaboração, arquivos e portais: equipes, armazenamento binário, permissões organizacionais e coautoria.
6. Integrações externas de correio, chamadas, automação e IA: implementar cada provedor com suas credenciais protegidas e fluxos reais.

Cada entrega deve atualizar o mapa de cobertura, verificar persistência e permissões, executar os testes relevantes, publicar e validar a jornada no domínio real. Status READY do deploy não substitui teste HTTP e navegador. Não alterar dados reais para testes; usar apenas registros sintéticos isolados.

## Marca e integrações

Nome confirmado: DRAP office. Cor: verde-exército #4B5320. Não aplicar a imagem gerada como logo definitiva: ela não garante a geometria exata exigida. Falta o original em arquivo para edição determinística autorizada. Integrações externas foram retiradas do escopo pelo proprietário em 02/11/2026. Nunca pedir segredos no chat.

## Atualização: planilha Univer

Substituída a grade básica por Univer com presets comunitários de núcleo, filtros, ordenação, validação e formatação condicional. Persistência usa `content.workbook`, migração compatível de matrizes legadas e exportação Office. Gráficos próprios vinculados a intervalos ficam em `content.charts` e são exportados como SVG ou gráficos editáveis no XLSX. `tests/browser_spreadsheet.py` verifica operações reais, persistência, exportação e acesso somente leitura. O plugin de proteção interna do Univer não representa o sistema de contas DRAP; menus de gestão dessa proteção foram ocultados. Permissões por arquivo continuam validadas pelo backend.

Pendências de planilhas: pivôs nativos no XLSX, agrupamentos multinível, tipos avançados de gráficos, importação de gráficos, mais fidelidade de temas/rich text e regras Office, impressão paginada, proteção por célula com autorização no backend, conectores e macros. Não declarar inventário 100% completo.

Tabelas dinâmicas DRAP implementadas em `web/pivot.js` / `web/pivot-ui.js`; exportação e validação em `server/pivots.py`. Fixtures compartilhadas verificam agregação equivalente em JS/Python, e `tests/browser_pivots.py` cobre criação, alteração, fórmulas, registros, XLSX, recuperação JSON e leitura.

Revisão visual: `web/slides.js` monta editor de objetos; `server/slides_io.py` valida imagens/objetos e faz intercâmbio PPTX. `tests/browser_slides.py` verifica uso real. Planilha ganhou ações diretas e sincronização da seleção nos campos auxiliares; a jornada existente cobre essas operações.

Fluxos corrigidos em `web/workflows.js`, `web/app.js` e `server/document_io.py`: imagens/tabelas/listas/links DOCX, agenda editável, respostas duplicadas preservadas, CSV e conversão completa de registros, ações permitidas em leitura. Testes em `tests/browser_workflows.py` e unidades correspondentes.

Editor visual: TipTap/ProseMirror 3.32.0, bundle `scripts/document-entry.js`, mantém `content.text` Markdown e `content.images`. Imagens são referências locais, sem buscar URLs. Leitores não ganham edição. `tests/browser_document.py` cobre edição visual, persistência e DOCX. Manter cabeçalho na primeira linha das tabelas evita normalização com linha adicional. Bibliotecas do npm têm versões fixadas; markdown-it-py 4.0.0 sustenta a exportação inline DOCX.

Barra de planilha: salvar não remonta Univer, mantendo seleção, aba e undo. A ponte conserva o objeto de conteúdo montado após atualizar metadados do servidor. O workaround do movimento de seleção fica restrito ao Enter na caixa de endereço: aplicar MOVE_END globalmente também às seleções internas pode cancelar edições pendentes. Fórmulas PT são normalizadas apenas em campos `f` antes da mutação. Teste nativo em `tests/browser_ribbon.py`.

Menus de clipboard: o submenu Univer 1.2 despacha `sheet.command.paste`, mas o comando registrado é `univer.command.paste`. Aliases de copy/cut/paste encaminham para os comandos reais, sem contornar autorização. Usar `getRawValues()` nos leitores de dados: `getValues()` retorna números já formatados como texto. Testes de moeda em gráficos e pivôs impedem regressão.

Google Workspace (26/10/2026): referência adicional em `docs/google-workspace.md`. Novos módulos `web/document-tools.js` e `web/sheet-tools.js` precisam permanecer na lista de assets de `server/app.py` e no pacote. Configuração de texto em `content.page`; slides usam `hidden`, `background`, `foreground`, `transition` com validação de servidor e intercâmbio PPTX. Transformações escrevem valores tipados em destino vazio/sem mesclagem, via uma ação nativa reversível. O parse de intervalos de dados permite uma célula; não usar `parsePivotRange` para isso (ele exige cabeçalho+dados). Notas do apresentador são visíveis na mesma tela. Nenhuma equivalência integral Google foi concluída.

Botão auxiliar confirmado pelo usuário: **＋ Inserir** na barra do editor. Implementação em `web/insert-menu.js`, metadados/binários limitados em `content.attachments`, validação em `server/attachments.py` e parsing autenticado de DOCX em `/api/import/preview` (sem criar item). O editor de texto separa parágrafos mistos de texto/imagens em blocos válidos; não basta usar a imagem padrão do TipTap dentro de um parágrafo com texto. Histórico de desfazer dos slides preserva anexos alterados fora dele. Teste principal: `tests/browser_insert.py`.

Instalação (PWA): `/install`, `web/pwa.js`, `web/manifest.webmanifest` e ícones PNG oferecem instalação pelo navegador. O evento real `beforeinstallprompt` controla a disponibilidade; `appinstalled` confirma conclusão. O clique na barra chama a instalação durante o gesto do usuário, ou abre ajuda em outra aba sem perder edições. O sistema cria o acesso após confirmação; iPhone/iPad exigem Adicionar à Tela de Início. Não há EXE/DMG/APK ou publicação em lojas, nem garantia de todos os modelos. `scripts/build-pwa.mjs` gera o worker com hash da página offline e do template; apenas `/offline.html` é armazenado, nunca API/arquivos. Testes: `tests/browser_install.py` (critérios reais Chromium, eventos simulados de confirmação/cancelamento, edição preservada, offline e responsividade), `tests/test_install.py` e `tests/install-platform.test.js`. Instalação real no sistema operacional não é demonstrada por eventos simulados.

Desempenho e revisão geral: `/api/bootstrap` combina sessão e primeira página da biblioteca; `/api/library` entrega até 100 metadados por página, sem conteúdo, e busca no conteúdo autorizado no servidor. `/api/items` continua paginado com conteúdo completo para backup e compatibilidade. `/api/analytics` calcula indicadores só dos arquivos autorizados e ativos. O frontend usa a resposta de criação/salvamento, evitando refazer a biblioteca e buscar novamente o arquivo recém-criado. `web/csv.js` separa CSV do motor de fórmulas; `scripts/build-app.mjs` gera `web/app.bundle.js`, entrada do HTML. Editores pesados continuam sob demanda; seu carregamento começa junto com a busca do arquivo. Não importar `formula.js` no shell: isso volta a carregar o parser na tela inicial.

PostgreSQL usa `psycopg-pool` com 0–4 conexões por instância, descarte após inatividade, validação na retirada, TLS verify-full e transação por operação. Não há cache de autorização. Imports de validação Office são adiados para escritas. Testes adicionais: `tests/test_library.py`, `tests/browser_library.py`, reutilização/rollback/reconexão em `tests/postgres_smoke.py`. Todos os fluxos de editor devem continuar passando após mudanças no catálogo; especialmente busca por conteúdo, indicadores, backup completo, Inserir da biblioteca e portais.

A navegação agora mostra a biblioteca conhecida imediatamente e revalida os metadados em segundo plano, sem remontar a busca nem perder seu foco. O editor anterior é desmontado antes de aguardar a rede, impedindo edições tardias depois de sair. Respostas atrasadas não substituem a tela ou catálogo de uma navegação mais recente. A jornada de biblioteca mantém a resposta de rede pendente para verificar essa condição.

## Publicação dos recursos avançados

O deploy anterior `dpl_Ez7TmXRfngLgZSC2PSM8EDwYcXCK` continha recursos ainda não integrados à branch principal. A revisão de 02/11/2026 reconcilia essa implementação com `origin/main` (43f75c3), preservando recuperação/MFA, Gantt/caminho crítico, quizzes e links de células. A integração Google foi cancelada pelo proprietário; não solicitar configuração OAuth. Consulte a revisão atual em `docs/revisao-2026-11-02.md`. Publicações futuras devem partir do código versionado e passar pelo workflow de verificação.
