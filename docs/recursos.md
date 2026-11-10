# Cobertura do inventário solicitado

A lista recebida inclui centenas de funções de produtos maduros. Esta entrega implementa um núcleo utilizável comum; as funcionalidades abaixo marcadas como pendentes não foram implementadas nem simuladas como ativas. A tela **Recursos** apresenta essa distinção dentro da plataforma.

| Área solicitada | Disponível nesta versão | Próxima implementação necessária |
| --- | --- | --- |
| Planilhas / Excel | Editor Univer, abas, fórmulas, estilos, mesclagem, filtros, ordenação, validação, formatação condicional, CSV e XLSX (detalhes abaixo) | Gráficos avançados, pivôs nativos no XLSX, macros, Solver, Power Query e equivalência integral ao Excel |
| Power Query | Importação CSV local | Fontes externas, ETL, junções, transformações, atualizações e linguagem M |
| Power Pivot | Não implementado | Modelo relacional, medidas, KPIs, DAX e cubos |
| Documentos / Word | Texto com títulos, negrito/itálico, listas, tabelas, links e imagens incorporadas; DOCX, Markdown ou HTML com imagens, impressão | Estilos avançados, paginação, seções, cabeçalhos/rodapés, gráficos, formas, referências acadêmicas, sumário, índices, mala direta, revisão e assinatura |
| Apresentações / PowerPoint | Slides com imagens, caixas de texto e formas editáveis; posição/tamanho/camadas, desfazer/refazer, criação, duplicação, remoção, reordenação, notas, temas, apresentação por teclado, documento → slides, PPTX | Mestre, áudio/vídeo, 3D, transições, animações, ações interativas, gravação e vídeo |
| Agenda / Outlook | Criação e edição de compromissos, descrição/local, ocorrências repetidas, ICS e apresentação no fuso do navegador | Disponibilidade, salas, convites, delegação e sincronização |
| Correio / Outlook | Não implementado | Conexão a provedor, pastas, contatos, mensagens, pesquisa, regras, anexos, envio e recebimento reais |
| Armazenamento / OneDrive | Biblioteca de arquivos próprios do DRAP office, histórico, lixeira e exportação JSON | Arquivos binários, upload/download, sincronização, cofre e armazenamento remoto |
| Notas / OneNote | Notas textuais, formatação simples, busca pela biblioteca | Cadernos/seções, desenho, PDF, multimídia, OCR e manuscritos |
| Comunicação / Teams | Compartilhamento de arquivos entre contas cadastradas | Chat, equipes/canais, menções, reações, áudio/vídeo, tela, legendas e telefonia |
| Formulários / Forms | Perguntas textuais, coleta no editor, histórico das perguntas por resposta e conversão para tabela | Coleta pública, múltipla escolha, escalas, quizzes, avaliações e análises especializadas |
| Dados / Access | Tabelas, campos textuais, registros, filtro, CSV e conversão para planilha | Tipagem, índices configuráveis, relacionamentos, consultas, formulários específicos e relatórios |
| Design editorial / Publisher | Impressão dos documentos pelo navegador | Layout editorial, guias, páginas-mestre e exportação gráfica profissional |
| Diagramas / Visio | Fluxo sequencial editável | Canvas, conectores livres, BPMN, organogramas, rede, engenharia e plantas |
| Projetos / Project | Kanban, cronograma (Gantt), marcos, dependências, caminho crítico e folga | Recursos, custos e linhas de base |
| Planner / To Do | Tarefas em três estados, prazos e contagem de conclusão | Subtarefas, etiquetas, prioridades, lembretes, listas pessoais e recorrência |
| Power Automate | Conversões manuais documento → slides, planilha → relatório, respostas → tabela, tabela → planilha | Gatilhos, agendas, conectores, condições, loops, aprovações e designer de fluxos |
| BI / Power BI | Indicadores reais de arquivos, tarefas e respostas do espaço | Modelagem, medidas, fontes externas, painéis configuráveis, mapas e publicação analítica |
| Portais / SharePoint | Página com texto e links para arquivos respeitando permissões | Sites públicos/intranet, listas avançadas, aprovações, biblioteca corporativa e políticas |
| IA / Copilot | Não conectado | Seleção de provedor, chaves seguras, políticas de dados, geração/resumo/análise e avaliações |
| Colaboração | Permissões de leitura/edição, revogação, versões e detecção de conflitos | Comentários, menções, alterações rastreadas e coautoria em tempo real |
| Segurança | scrypt, cookies HttpOnly/SameSite, origem, rate limit persistido no banco, autorização no servidor, recuperação de senha por pergunta secreta, verificação em duas etapas (TOTP) e registro de atividade da conta | SSO/OAuth, assinaturas, criptografia gerenciada e auditoria administrativa da organização |
| Automação de código | Fórmulas analisadas por parser limitado, sem executar código do usuário | VBA, Office Scripts e ambientes de execução isolados |
| Acessibilidade | Labels, controles nativos, foco visível, status anunciados e teclado no apresentador | Auditoria WCAG, testes com leitores de tela, textos alternativos e legendas |
| Publicação | Aplicação executável em desenvolvimento; backup e restauração locais testados | Hospedagem HTTPS, observabilidade, operação, recuperação e teste no ambiente publicado |

## Ampliação implementada

| Área | Implementação adicionada | Limites que permanecem |
| --- | --- | --- |
| Documentos / notas / portais | Listas, checklist, tabelas Markdown, links seguros, busca/substituição; imagens e DOCX para documentos/notas | Não há paginação profissional nem fidelidade total de layout DOCX |
| Planilhas | Editor Univer; ver detalhes e limites na seção abaixo | Sem macros, pivôs nativos no XLSX, gráficos avançados, DAX, Power Query ou equivalência de todas as fórmulas |
| Apresentações | Imagens, texto, formas, camadas, arraste/redimensionamento, temas e PPTX com imagens/objetos | Importação preserva imagens e objetos de texto/formas criados pelo DRAP; grupos, recortes, temas externos, animações e vídeos não são preservados |
| Projetos | Responsáveis, prioridades e subtarefas | Sem caminho crítico ou planejamento de recursos |
| Agenda | Ocorrências repetidas e intercâmbio ICS | Sem envio de convites; recorrências importadas são expandidas em até 1000 ocorrências |
| Formulários | Tipos de campo, validação e links públicos revogáveis | Sem quizzes/ramificação; até 1000 respostas e limite de conteúdo |
| Tabelas | Tipos, validação, ordenação e remoção de duplicatas | Sem banco relacional configurável |
| Diagramas | Canvas, arraste, teclado, conectores e SVG | Sem bibliotecas BPMN/engenharia |
| Colaboração | Comentários, listagem de acessos e rascunhos locais recuperáveis | Sem coautoria em tempo real |
| Contas | Recuperação de senha por pergunta e resposta secreta escolhidas no cadastro; troca da pergunta com a senha atual | Sem MFA nem recuperação por e-mail |

Esta tabela atualiza os itens básicos da matriz acima. Correio, reuniões, IA e integrações de provedor continuam pendentes; a existência de um plano não os torna implementados.

## Sequência de evolução

1. Estabilizar o núcleo: rascunhos recuperáveis, auditoria, compartilhamentos listáveis e testes ampliados de acesso.
2. Profundidade dos editores: arquivos Office com bibliotecas especializadas, texto estruturado e paginação, planilhas com múltiplas abas e fórmulas adicionais, canvas de slides e diagramas.
3. Colaboração e arquivos: armazenamento de binários, comentários, equipes, permissões organizacionais e coautoria.
4. Serviços: correio e calendário via OAuth, chamadas via serviço de mídia, conectores de dados e automações com execução em filas.
5. IA e BI: provedor configurável, controles de privacidade, modelagem e dashboards editáveis.
6. Operação: deploy, testes de carga, segurança, monitoramento, backups externos e recuperação ensaiada.

Essa sequência é um plano técnico, não uma promessa de equivalência concluída. A cobertura de cada recurso deverá ser atualizada com testes à medida que for implementado.

## Planilha integrada — outubro de 2026

A grade inicial foi substituída pelo **Univer 1.2.0**, distribuído com a aplicação (Apache-2.0), com interface em português. Oferece edição no canvas, seleção de intervalos, copiar/colar, preenchimento, desfazer/refazer, fontes/cores/bordas, formatos numéricos, mesclagem, linhas/colunas, abas, fórmulas, filtros, ordenação, validação de dados e formatação condicional. A edição salva o snapshot nativo completo no banco, inclusive regras, mantendo versões e permissões. Planilhas antigas são convertidas ao abrir sem apagar o histórico.

O XLSX importa/exporta valores, fórmulas, estilos básicos, formatos numéricos, mesclagens, dimensões e painéis congelados. A exportação inclui filtros por valores, validações comuns e regras condicionais numéricas/por fórmula; regras avançadas permanecem no snapshot/JSON. A importação também preserva filtros por valores, validações comuns e regras condicionais numéricas/por fórmula. Gráficos de colunas, linhas e pizza vinculados a intervalos são salvos no DRAP e exportados para SVG e XLSX editável. A importação de gráficos Excel, gráficos avançados, pivôs nativos no XLSX, macros, Power Query e equivalência integral ao Excel continuam pendentes.

Limites persistidos: 20 abas, 50 mil células preenchidas, 2 MB de conteúdo JSON por arquivo, coordenadas até 100 mil linhas × 1024 colunas. Importação XLSX: 2,5 MB comprimidos com inspeção do ZIP. CSV: até 10 mil linhas × 256 colunas, respeitando o total de 50 mil células. Os limites são verificados, sem truncamento silencioso. Fórmulas nativas são armazenadas em inglês; células, barra de fórmulas, colagem e campo auxiliar normalizam os aliases portugueses suportados (por exemplo, SOMA/SE/PROCV), preservando texto entre aspas. A entrada numérica nativa usa o locale brasileiro: vírgula decimal.

O editor usa canvas: o campo auxiliar permite selecionar intervalos e inserir conteúdo por teclado, mas isso não constitui conformidade integral com leitores de tela. O CSS requer estilos inline; a política continua bloqueando scripts inline e `unsafe-eval`.

Gráficos: até dez definições por pasta, cada uma com rótulos e uma série numérica (duas colunas com cabeçalho e até 200 linhas). A vinculação usa endereços literais; inserir/excluir linhas não ajusta automaticamente esses endereços. Gráficos de pizza exigem dados não negativos.

Backups JSON reconhecem o formato nativo novo da planilha e o formato antigo. A importação aceita até 100 arquivos em um JSON de até 64 MB, enviados individualmente e validados no servidor; restaura cópias privadas, sem herdar compartilhamentos. Falhas parciais informam a quantidade importada.


## Tabelas dinâmicas DRAP

O botão **Tabela dinâmica** cria resumos vinculados a um intervalo de uma aba. Permite escolher um campo de linhas, um de colunas (opcional), o campo de valores, soma, média, mínimo, máximo, contagem preenchida ou contagem de linhas; filtro por correspondência exata e ordenação pelo total. Os totais são calculados a partir dos registros originais, incluindo médias com quantidades diferentes em cada grupo. Texto é ignorado nas operações numéricas; erros de fórmula impedem um resumo numérico incorreto.

Os resultados acompanham mudanças de valores e fórmulas. Clicar em um resultado abre os registros que o compõem: são exibidas até 200 linhas, com CSV de todos os registros selecionados. A definição persiste em `content.pivots`, funciona na recuperação JSON e respeita acesso de leitura/edição. O XLSX adiciona abas `Resumo N` com os resultados atuais como tabelas comuns. **Não cria o objeto PivotTable nativo do Excel**; para manter a configuração dinâmica do DRAP, use JSON.

Limites: dez resumos por pasta, até 50 mil células/256 colunas na fonte e dez mil células por resultado. Cabeçalhos precisam ser preenchidos e únicos. O intervalo é fixo: inserir/excluir linhas ou colunas não ajusta sua definição automaticamente. Filtros da grade não afetam o resumo; use o filtro do próprio resumo. Múltiplos níveis de agrupamento, segmentações, atualização de fontes externas e importação de PivotTables Excel continuam pendentes.

## Slides visuais e ações de planilha

Slides usam coordenadas proporcionais em uma página 16:9. Imagens PNG/JPEG/WebP locais são otimizadas para PNG e salvas com o documento; até 30 objetos por slide e 100 slides, respeitando 2 MB por documento. O editor limita novas imagens/duplicações antes de 1,8 MB e imagens individuais a cerca de 300 KB otimizados. O PPTX contém imagens incorporadas e textos/formas editáveis. Impressão/PDF inclui todos os slides, sem notas. Leitores podem navegar e apresentar, sem editar.

Planilhas: campos de intervalo/valor acompanham a seleção; atalhos para inserir linha/coluna, limpar valores, colar dados tabulados e criar soma/média/mínimo/máximo/contagens. O assistente rejeita resultado dentro da própria origem para evitar referência circular. Fórmulas continuam atualizando após inserção de linhas e colunas.

## Correções de fluxos entre módulos

- Documentos/notas: inserção de até 20 imagens raster otimizadas, descrição/largura, remoção, exportação HTML autocontida e DOCX com imagens, tabelas, listas e hyperlinks. Imagens de parágrafos DOCX são importadas; imagens dentro de tabelas, cabeçalhos/rodapés e posições flutuantes não são preservadas. Documentos com imagens podem gerar slides com essas imagens. Permanece o limite de 2 MB por documento.
- Agenda: edição de título, início/fim, local e descrição de cada ocorrência; validação do intervalo considera o instante real, incluindo fusos diferentes.
- Formulários: rótulos/obrigatoriedade são atualizados no formulário de resposta; perguntas com títulos repetidos mantêm colunas distintas. Conversão para tabela verifica 200 registros/26 campos e orienta usar planilha ou CSV. Planilhas aceitam até 50 mil células nessa conversão.
- Tabelas: importação CSV, ordenação nos dois sentidos, filtro preservado, conversão dos 200 registros mais cabeçalho. Textos iniciados com `=` permanecem texto na planilha gerada.
- Somente leitura: navegação do portal, filtro de tabelas e downloads autorizados ficam acessíveis; edição continua bloqueada no servidor.
- Diagramas: mover etapas para baixo amplia a área visível em vez de esconder as etapas fora do canvas.

## Edição visual de documentos e notas

Editor visual com títulos, parágrafos, negrito/itálico combinados, listas/checklists, tabelas com edição de células/linhas/colunas, imagens, desfazer/refazer e substituição do texto visível. Markdown continua disponível; imagens e conteúdo antigo permanecem compatíveis. A primeira linha de tabelas é mantida como cabeçalho para evitar linhas artificiais ao reabrir. Colagem recebe texto simples; imagens usam upload local. Paginação profissional, fontes/cores arbitrárias, coautoria e fidelidade completa ao Word continuam fora dessa implementação.

## Barra nativa da planilha

Salvar preserva a instância do editor: célula selecionada, aba da barra, rolagem e histórico de desfazer/refazer da sessão. Alterações posteriores continuam sendo persistidas e geram novas versões. A caixa de endereço nativa atualiza os controles para a seleção atual; valores colados também atualizam o campo auxiliar. `tests/browser_ribbon.py` verifica comandos reais da barra e o XLSX, sem usar a API do editor para aplicar formatação. A memória de desfazer continua restrita à sessão aberta; reabrir o arquivo usa o histórico de versões do DRAP.

O menu Colar e as variantes de colagem usam os comandos nativos registrados, mantendo permissões, valores e estilos. A leitura de intervalos para edição auxiliar, gráficos e tabelas dinâmicas usa os valores numéricos originais, mesmo quando a grade mostra moeda ou percentual. Os testes de gráficos e resumos incluem fontes formatadas como moeda.

## Comparação com Google Workspace — 26/10/2026

Veja o [inventário Google](google-workspace.md), com recursos existentes, adicionados e pendentes e links às fontes oficiais. Esta seção atualiza a matriz inicial: documentos agora têm estrutura navegável, estatísticas, listas numeradas, citação/código/linha horizontal e configuração global de página/fonte/espaçamento; planilhas têm seis transformações para um destino vazio e estatísticas; apresentações têm alinhamento/distribuição, fundos, ocultação, transições simples e controles do apresentador. As opções suportadas de página chegam ao DOCX; fundo, cor, ocultação e transições chegam ao PPTX. A edição de texto permanece contínua; coautoria e paginação profissional, animação de objetos, serviços Google e IA continuam pendentes.

## Botão auxiliar ＋ Inserir

Disponível na barra de todos os editores. **Documento** insere o conteúdo de DOCX/TXT/Markdown em documentos/notas, preservando o texto existente e remapeando imagens para evitar colisões. TXT exige UTF-8 e trata a marcação como texto literal. DOCX passa pelo importador validado e informa perdas de layout. **Arquivo / outros** anexa qualquer formato como bytes para download (PDF, Office, ZIP, áudio etc.); não executa nem pré-visualiza conteúdo ativo. **Da biblioteca** adiciona vínculo ou copia o conteúdo de documento/nota autorizado. **Link**, **Imagem** e **Tabela** completam o menu conforme o editor.

Anexos: até 1 MB por arquivo, 20 anexos/vínculos e limite total do documento. A seleção múltipla é validada antes de aplicar alterações. Persistem em `content.attachments`, no histórico, nos rascunhos e no JSON. Compartilhar o arquivo disponibiliza seus anexos; vincular outro arquivo não concede acesso ao original. Leitores podem baixar/abrir itens autorizados, mas não inserir/remover. Exportações Office não incluem a lista de anexos/vínculos, e a interface informa essa diferença. A inserção de DOCX analisa o documento sem criar um arquivo adicional na biblioteca.

Verificação: `tests/browser_insert.py` percorre os controles reais com DOCX/imagem, TXT literal, PDF, links, biblioteca, limites, download byte a byte, reabertura, permissões/revogação, celular e planilha. `tests/test_attachments.py` cobre validação, histórico, acesso e parsing autenticado sem criação de itens. `tests/insert-menu.test.js` cobre isolamento das imagens e limites de conteúdo.

## Instalação no computador e celular

O botão **Instalar e criar atalho** solicita a instalação como aplicativo web quando o navegador oferece essa função. A confirmação é obrigatória; depois dela, o sistema disponibiliza o ícone. `/install` contém orientações por sistema, detecção do aparelho, link copiável/compartilhável e ajuda para Safari/iPhone/iPad. Windows, macOS, Linux/ChromeOS e Android dependem de navegador compatível; não há garantia para todos os modelos ou instaladores nativos EXE/DMG/APK. O ZIP continua disponível como código-fonte para desenvolvimento.

Login, abertura e salvamento exigem internet. A página offline não exibe dados privados; o cache do service worker contém apenas esse aviso. A instalação e as atualizações não recarregam editores abertos. Os testes verificam manifesto/ícones, critérios reais de instalação no Chromium, fluxo de confirmação simulado, preservação da edição, tamanhos de tela e ausência de dados privados no cache. A validação não substitui instalação manual em dispositivos Windows/macOS/Android/iOS reais.

## Desempenho da biblioteca

A entrada consulta sessão e lista leve de arquivos em uma chamada. A lista não transfere o conteúdo dos documentos: ele é buscado ao abrir um arquivo. Busca por conteúdo e indicadores são consultados sob demanda com as mesmas permissões; exportar o espaço continua incluindo o conteúdo completo. Criar e salvar atualiza o catálogo local pela resposta do servidor. O JavaScript inicial é empacotado e não inclui o parser de fórmulas; documentos e planilhas carregam seus editores quando usados.

## Ampliação dos editores — 28/10/2026

Documentos armazenam uma árvore de texto rico junto ao Markdown de compatibilidade. Fonte, cor, tamanho e marcas por trecho, abas, notas, sumário atualizável, cabeçalho/rodapé, modelos, mesclagem e HTML. A edição manual de Markdown converte a aba para formatação básica e avisa essa perda. DOCX exporta todas as abas em seções de conteúdo separadas por quebras; reimportação não reconstrói as abas.

Planilhas têm cinco tipos adicionais de gráficos e proteção de intervalos aplicada pelo servidor. A proteção controla gravações compartilhadas no DRAP, não é senha de XLSX. Slides têm grupos, rotação, estilo para novos slides, layout de duas colunas e janela separada do apresentador.

Projetos têm dependências e cronograma; agenda tem visão mensal; formulários têm quizzes, texto longo e avaliação. A integração externa Google foi retirada em 02/11/2026 por solicitação do proprietário; a agenda interna continua disponível.
## App instalável e modo offline (PWA)

O DRAP office pode ser instalado pelo navegador (Chrome/Edge: ícone de instalar na barra de endereço; Android: "Adicionar à tela inicial"; iPhone: Compartilhar → "Adicionar à Tela de Início"). `web/manifest.webmanifest` define nome, cor #4B5320 e ícones; `web/sw.js` guarda a interface do aplicativo (HTML, CSS e scripts) para abrir sem internet.

Política de cache: rede primeiro, com o cache usado apenas como reserva, porque os nomes dos arquivos não têm hash de versão. Nada de `/api/` nem de `/downloads/` é guardado: arquivos, contas e respostas de formulários nunca ficam no Cache Storage, e sair da conta não deixa dados legíveis no aparelho. Links com parâmetros (como `?form=`) também não são guardados.

Sem conexão: aparece um aviso no topo; ao salvar, a alteração fica como rascunho local (o mesmo mecanismo de rascunhos já existente) e o usuário salva novamente quando a internet voltar. Se o aplicativo for aberto sem internet, a interface carrega, explica a falta de conexão e reabre sozinha quando a rede volta.

Limites: não há leitura de arquivos sem internet nem sincronização automática em segundo plano; o editor de planilhas e o editor visual de documentos só ficam disponíveis offline depois de terem sido abertos uma vez com internet. O ícone atual usa apenas o nome DRAP office e deve ser substituído quando houver o arquivo original da logo. `tests/browser_pwa.py` verifica manifesto, ícones, cache sem dados da API, aviso offline, rascunho e reabertura.

## Recuperação de senha por pergunta secreta

No cadastro, o usuário escolhe uma pergunta de uma lista fixa (`SECURITY_QUESTIONS` em `server/store.py`) e digita a resposta. A resposta é normalizada (sem diferença de maiúsculas, acentos ou espaços repetidos) e guardada apenas como hash scrypt com sal próprio, na tabela `account_recovery`.

Em **Esqueci minha senha**, o usuário informa o e-mail, vê a pergunta, responde e escolhe a nova senha. A troca encerra todas as sessões abertas. Proteções: limite de tentativas por IP e por e-mail, bloqueio de 15 minutos após 5 respostas erradas e mensagem genérica para resposta errada ou conta sem pergunta. Logado, o botão **Pergunta secreta** do menu lateral troca a pergunta mediante a senha atual; contas criadas antes desse recurso recebem um convite para cadastrar a pergunta uma vez por sessão.

Limites: perguntas secretas são mais fracas que confirmação por e-mail ou MFA, porque respostas podem ser adivinhadas por pessoas próximas. Informar um e-mail mostra se ele tem pergunta cadastrada (o cadastro já revelava contas existentes). `tests/test_recovery.py` e `tests/browser_recovery.py` cobrem o fluxo.

## Etapa 1 da revisão de módulos — novembro de 2026

**Projetos.** Tarefas ganharam identificador estável, data de início, marcos e dependências. A visão **Cronograma** mostra um Gantt calculado pelo método do caminho crítico (`web/project.js`): período do projeto, caminho crítico, folga de cada tarefa e aviso quando uma tarefa começa antes de as dependências terminarem (o cronograma mostra a data mais cedo possível). Ciclos são recusados no editor e no servidor (`valid_task_graph`). Prazos antigos em formato livre continuam aceitos e ficam fora do cronograma. Testes: `tests/project.test.js`, `tests/browser_projects.py`.

**Formulários.** Novos tipos: múltipla seleção (respostas unidas por `; `; opções não podem conter ponto e vírgula) e escala de 1 até 2–10. **Modo quiz**: resposta correta e pontos (0–100) por pergunta; a nota é calculada no editor e, nas respostas públicas, no servidor. O formulário público nunca recebe o gabarito. Respostas e exportações ganham a coluna **Nota**. Texto é comparado sem diferenciar maiúsculas, acentos ou espaços. Testes: `tests/test_forms.py`, `tests/workflows.test.js`, `tests/browser_quiz.py`.

**Segurança.** Verificação em duas etapas com app autenticador (TOTP, RFC 6238, 6 dígitos a cada 30 s, tolerância de ±30 s), QR code gerado no navegador (`qrcode-generator`, MIT) e chave para digitação manual; 8 códigos de backup de uso único (guardados como hash); o mesmo código não pode ser reutilizado; limite de 5 códigos por minuto por e-mail. Ativar e desativar exigem a senha atual (e um código, para desativar). A recuperação de senha por pergunta secreta não dispensa o código. A tela **Segurança da conta** mostra a atividade recente (cadastro, entradas, falhas de senha e de código, uso de código de backup, mudanças de MFA e pergunta secreta, compartilhamentos e saídas; últimos 200 eventos com IP). Limite: a chave TOTP fica no banco sem criptografia adicional; quem perder o celular e os códigos de backup perde o acesso. Testes: `tests/test_mfa.py`, `tests/browser_security.py`.

## Planilha: botão ＋ Inserir (vínculos de células)

O botão **＋ Inserir** da planilha coloca numa célula um vínculo para outro arquivo do DRAP office (documento, apresentação, formulário, tabela etc.) ou para um site `https://`. A célula recebe o texto escolhido (ou o nome do arquivo); ao selecionar a célula, uma barra acima da grade mostra o vínculo com **Abrir** e **Remover vínculo**. A lista **Arquivos e links vinculados**, abaixo da grade, reúne todos os vínculos da pasta com atalhos para abrir e ir até a célula. Os vínculos ficam em `content.links` (até 200), são validados no servidor (somente `https://`) e respeitam as permissões: abrir um arquivo vinculado exige acesso a ele. Limites: o vínculo usa o endereço fixo da célula (inserir/excluir linhas não o move, como nos gráficos) e o XLSX leva apenas o texto da célula. Teste: `tests/browser_sheet_links.py`.

## Etapa 1: recursos e custos de Projetos

Implementação local: tarefas aceitam horas planejadas/realizadas, custo por hora e
custos adicionais em reais. O painel **Recursos e custos** soma horas e custos por
responsável e no projeto. Valores validados no servidor e preservados pelo salvamento,
versões e exportação JSON. Custos adicionais entram no planejado e no realizado;
não há lançamentos separados. Linha de base, capacidade e conflitos de recursos
continuam pendentes. Plano de conclusão e limites em [etapas.md](etapas.md).

## Linha de base e capacidade de Projetos; Gemini

Projetos: snapshot do orçamento e cronograma efetivo, diferenças por tarefa e total,
tarefas adicionadas/removidas, capacidade diária por responsável e intervalos de
sobrecarga. Distribuição por dias corridos, sem nivelamento automático ou feriados.
A referência anterior permanece no histórico de versões após salvar.

Gemini: geração, resumo e análise de texto sob demanda, com seleção explícita de
arquivo salvo autorizado, confirmação do envio e resultado revisável. Pode salvar
novo documento privado. A disponibilidade depende da autenticação e dos créditos
no AI Gateway; sem ferramentas, envio automático ou análise de anexos/imagens.
Detalhes em [gemini.md](gemini.md). Demais módulos e integrações continuam sujeitos
às pendências registradas; esta entrega não representa paridade integral com Office.

## Abertura direta dos módulos na home

Os dez atalhos de ferramentas abrem um editor novo imediatamente, sem pedir nome
ou criar um arquivo no servidor. O primeiro **Salvar** solicita o nome do projeto
se ele ainda não foi informado; cancelar mantém a edição. Após salvar, os próximos
salvamentos atualizam o mesmo arquivo. Rascunhos locais não salvos são recuperados
ao reabrir o mesmo módulo neste navegador e conta. Há um rascunho local por módulo.
Histórico, comentários e compartilhamento ficam disponíveis depois de salvar.
DOCX/XLSX/PPTX/ICS podem ser exportados sem salvar o arquivo no servidor.

## Exclusão individual na biblioteca

Arquivos recentes e biblioteca mostram **Excluir** em cada arquivo editável.
A confirmação identifica o arquivo; a operação move apenas esse arquivo para a
lixeira, preservando conteúdo e histórico. Na lixeira, **Restaurar** devolve esse
arquivo à biblioteca. Leitores não recebem ações de alteração. A gravação usa a
versão atual e o controle de concorrência existente; conflitos não são sobrescritos.

## Relacionamentos entre tabelas

Cada tabela pode manter até dez vínculos nomeados com outras tabelas da biblioteca.
Escolha o campo de origem e o campo de destino. Em cada vínculo, selecione um
registro de origem e clique em **Consultar** para ver registros do destino com
valor exatamente igual (diferenciando maiúsculas, espaços e representação numérica).
Valores vazios não correspondem. Resultados são paginados de 50 em 50.

É necessário salvar antes de configurar ou consultar. A definição é preservada
no JSON e no histórico; a consulta sempre verifica acesso às duas tabelas. Um leitor
da origem não ganha acesso ao destino pelo vínculo. Revogação e lixeira são
respeitadas. Alterações de versão da origem ou de campo do destino impedem uma
consulta com correspondência incorreta. Excluir um campo de origem remove seus
vínculos; renomeá-lo na interface atualiza a referência local.

Não há integridade referencial obrigatória, exclusão em cascata, linguagem SQL,
edição do destino pela consulta ou garantia de unicidade de chave. CSV/XLSX
exportam os dados da tabela; use JSON para preservar as definições dos vínculos.

Os campos usados nos vínculos precisam ter nomes únicos nas respectivas tabelas.
A importação JSON preserva os IDs de destino originais; não remapeia automaticamente
os vínculos para outras cópias importadas. As permissões continuam sendo verificadas.
## Etapa 2 da revisão de módulos — documentos e planilhas

**Documentos e notas.** **Sumário** gera, na posição do cursor, uma lista aninhada com os títulos (`#`, `##`, `###`) do documento; é estático — ao mudar os títulos, insira um novo. **Quebra de página** insere `---` (aparece como divisória rotulada na tela, quebra a página na impressão/PDF e vira quebra real no DOCX). **Cabeçalho e rodapé** guardam `header`, `footer` e `pageNumbers` no conteúdo: na impressão/PDF usam as margens da página do navegador (Chrome/Edge recentes) e, no DOCX, cabeçalho, rodapé e campos `PAGE`/`NUMPAGES` (“Página X de Y”). Testes: `tests/test_document_io.py`, `tests/browser_stage2.py`.

**Gráficos.** Tipos: colunas, colunas empilhadas, barras horizontais, linhas, área, pizza, rosca e dispersão. O intervalo tem uma coluna de rótulos (na dispersão, X numérico) e de 1 a 6 colunas de séries com cabeçalho; pizza e rosca usam uma série. Legenda automática com várias séries. A exportação XLSX cria o gráfico nativo correspondente (BarChart empilhado/horizontal, AreaChart, DoughnutChart, ScatterChart). Testes: `tests/chart.test.js`, `tests/test_spreadsheet.py`, `tests/browser_stage2.py`.

**Tabelas dinâmicas.** Campo opcional **Subgrupo de linhas**: cada grupo lista seus subgrupos seguidos de uma linha “Total <grupo>” e, no fim, o “Total geral”. A ordenação pelo total ordena os grupos; os subgrupos mantêm a ordem da fonte. Clicar em subgrupo, subtotal ou total abre os registros correspondentes. Os motores JS e Python usam os mesmos casos de teste (`tests/pivot-cases.json`); o XLSX recebe a aba “Resumo N” com os dois níveis.

## Perguntas condicionais em formulários

Em **Exibição da pergunta**, escolha uma pergunta anterior de escolha única e a
resposta que deve mostrar a pergunta atual. As condições podem formar cadeias,
mas não apontam para perguntas posteriores nem para si mesmas. Perguntas ocultas
ficam desabilitadas e suas respostas são limpas quando a condição deixa de valer.
Não são obrigatórias e não entram na pontuação do quiz.

O servidor recalcula a visibilidade: respostas forjadas para perguntas ocultas
são descartadas e não alteram a nota. A configuração entra no identificador do
formulário; mudanças exigem reabertura antes de responder. O formulário público
recebe as condições, mas não recebe gabaritos ou pontos. Exportações mantêm as
colunas das perguntas e usam vazio nas perguntas que não foram exibidas.

Remover uma pergunta, mudar seu tipo ou remover uma opção usada por uma condição
remove as condições que dependiam dessa referência. Revise as regras após alterar
a estrutura. Esta entrega não inclui saltos de página, condições numéricas ou
expressões compostas com múltiplas regras.

A exibição condicional orienta o preenchimento, mas não restringe o acesso ao texto
das perguntas: a definição de todas as perguntas faz parte do formulário público.

## Automação de resposta pública para tarefa

Em **Formulários → Automação de tarefas**, ou **Conexões → Automações de formulários**,
o proprietário pode ativar uma regra: cada nova resposta recebida pelo link público
cria uma tarefa em um projeto do mesmo proprietário. O título combina um prefixo
com uma resposta escolhida ou o nome do formulário. Há prioridade configurável e
condição opcional por resposta exata de uma pergunta de escolha única. Perguntas
usadas na regra precisam ter títulos únicos; alterações incompatíveis falham com
um registro, sem usar outro campo silenciosamente.

As execuções mostram conclusão, condição não atendida ou falha, com paginação de
50 registros. Uma falha no destino não descarta a resposta do formulário. O dono
pode corrigir/restaurar o projeto e reprocessar execuções recuperáveis. O destino,
título e prioridade são os definidos no envio; mudar a regra vale para próximos
envios. Tarefas e histórico do projeto usam o mesmo salvamento transacional.

O navegador identifica cada tentativa de envio. Repetir o mesmo identificador e
conteúdo retorna o resultado anterior sem criar outra resposta ou tarefa, inclusive
com requisições concorrentes e após reinício. Reutilizar o identificador com conteúdo
diferente é recusado. Clientes antigos sem identificador continuam compatíveis,
mas não têm essa deduplicação. Recarregar o formulário inicia um novo envio.
Reprocessar uma execução concluída não recria uma tarefa removida posteriormente.

Somente o proprietário configura a regra e lê/reprocessa o histórico. Compartilhar
um formulário não concede administração da automação; projetos de terceiros não
podem ser destinos, mesmo quando compartilhados para edição. Respostas registradas
apenas no editor não acionam a regra. Não há envio de e-mail, chamadas externas,
execução em segundo plano, agendamento ou designer genérico de fluxos nesta etapa.
Configurações, deduplicação e execuções pertencem ao banco; o JSON de arquivos não
é backup dessas tabelas. Backups integrais do PostgreSQL/SQLite as preservam.

## BI: painel pessoal configurável

Em **Indicadores**, cada conta tem um painel privado persistente com até 12
indicadores sobre tabelas ou projetos acessíveis. Há contagem de registros, soma,
média, mínimo e máximo; filtro por igualdade exata de um campo e agrupamento em até
50 categorias. Agrupamentos aparecem como barras e tabela com valores, inclusive
negativos. Campos vazios são ignorados nas medidas; uma medida sem valores mostra
“Sem valores”. Texto não numérico gera erro, sem descarte silencioso. Medidas usam
números canônicos com ponto decimal, sem moeda ou separador de milhar. A interface
arredonda a exibição a seis casas; não é cálculo contábil de precisão arbitrária.

O painel permite adicionar, editar e excluir indicadores individualmente,
renomear, atualizar e exportar os resultados atuais em CSV protegido contra
fórmulas. Cada resultado identifica a versão da fonte consultada. Modificações nas
fontes são refletidas ao abrir/atualizar o painel; não há atualização automática
em segundo plano. Alterações incompatíveis/ambíguas nos campos exigem reconfiguração.

O servidor revalida acesso e lixeira ao calcular os valores. Revogar acesso remove
os valores do próximo resultado, sem cache de totais. Configurações são privadas,
sem publicação ou compartilhamento de painel. Edições simultâneas são recusadas
por versão. Até 500 fontes são listadas no seletor. Dados permanecem nas fontes;
a configuração do painel reside no banco e depende do backup integral, não do JSON
de arquivos. Não há DAX, cruzamento entre fontes, cubos, mapas ou conectores externos.

## Aprovação manual de solicitações de tarefa

A regra de formulário → tarefa pode exigir aprovação do proprietário. O envio
público registra a resposta normalmente e aguarda a decisão no painel de execuções;
nenhuma tarefa existe antes da aprovação. O proprietário consulta a resposta
original do envio, destino, título e prioridade e escolhe aprovar ou rejeitar.
A cópia original é privada e permanece disponível mesmo se a resposta no editor
for alterada. Respostas ocultas por condição continuam vazias nessa cópia.

Decisão, autor e horário ficam registrados. Aprovar e gravar a tarefa usam a mesma
transação; reenvios concorrentes da decisão não duplicam tarefas. Rejeições são
definitivas. Uma aprovação com destino indisponível gera falha recuperável; após
corrigir o destino, o proprietário pode reprocessar. Editores compartilhados não
podem decidir nem consultar as respostas originais pelo painel. Desativar a regra
não cancela pendências já registradas. Não há delegação, múltiplos aprovadores,
e-mail, expiração automática, agendas ou designer genérico de fluxos nesta etapa.

## Colaboração: menções e notificações internas

Ao comentar um arquivo salvo, o autor pode informar até dez e-mails de pessoas
que já têm acesso ao arquivo. A menção é explícita no campo dedicado; escrever um
e-mail apenas no texto não notifica ninguém. Endereços repetidos geram uma única
menção e mencionar a própria conta não cria uma notificação. O sistema valida todos
os destinatários antes de confirmar comentário, menções e notificações na mesma
transação. Uma menção não compartilha o arquivo. Os comentários mostram nomes,
sem transformar o painel em diretório de e-mails dos participantes.

A opção **Notificações** mostra menções recebidas com autor, arquivo, prévia e data.
Há leitura/não leitura, marcar todas como lidas, exclusão individual e atalho para o
comentário específico, destacado no editor. Excluir uma notificação não exclui o
comentário. A lista é paginada em 50 registros. O contador do menu é consultado ao
abrir telas; a central possui atualização manual. Não há push, e-mail ou atualização
em tempo real nesta etapa.

Lista e contador revalidam permissões e lixeira no servidor. Ao revogar acesso ou
excluir o arquivo, suas notificações ficam ocultas na próxima consulta; restaurar o
acesso pode torná-las visíveis novamente, preservando a leitura. Cada conta administra
apenas suas notificações. A regra original permanece: leitores podem ler comentários,
mas precisam de permissão de edição para publicar. Os registros adicionais fazem
parte do backup integral do banco, não do JSON individual dos arquivos. Não há
coautoria simultânea, chat, canais ou menções em qualquer posição do documento.

## Automações agendadas: tarefas por data

Em **Conexões → Tarefas agendadas**, cada conta pode manter até 50 agendas fora da
lixeira, com projeto próprio, nome, título da tarefa, prioridade, primeira data,
fuso IANA e prazo de 0 a 365 dias depois da ocorrência. Há execução única, diária,
semanal e mensal. Meses curtos usam o último dia, retomando o dia original nos
meses seguintes (31/jan → 28/fev → 31/mar). Não é agendamento com precisão de minuto.

O Cron Job nativo da Vercel está configurado para uma verificação diária às 03:00 UTC.
A data de cada regra é avaliada em seu próprio fuso. O cron exige `CRON_SECRET` via
Authorization, sem autenticação por cookie ou confiança apenas no User-Agent.
Uma consulta autenticada com `?probe=1` verifica configuração sem executar regras.
A interface informa quando a execução automática não está configurada no ambiente.

A rodada automática é limitada a 200 ocorrências, cinco por agenda, com orçamento
de tempo; as demais permanecem pendentes. Processamento manual consulta apenas
agendas do usuário, até 20 ocorrências por rodada ou cinco por agenda individual.
Volumes superiores à capacidade diária precisam de rodadas manuais ou ampliação
operacional da frequência/capacidade. Atrasos não antecipam ocorrências futuras.

Cada ocorrência e sua tarefa/histórico/avanço de agenda usam a mesma transação.
Chamadas concorrentes e repetidas não duplicam uma ocorrência da mesma agenda e
data. Interrupções retomam pendências. Falhas de destino são registradas e a agenda
avança; o proprietário pode restaurar/corrigir o projeto e reprocessar a ocorrência.
A execução preserva o título, prioridade, destino e prazo originais, mesmo após
editar a agenda. Agendas e histórico são privados ao proprietário.

Pausar impede futuras rodadas; excluir move a agenda para sua própria lixeira e
restaurar a mantém pausada. Nenhuma dessas ações remove tarefas já criadas. Há
controle de versão e paginação de 50 registros em listas/histórico. Configurações,
execuções e deduplicação dependem do backup integral do banco. Não há scripts
arbitrários, conectores externos, disparos a cada minuto ou designer geral de fluxos.
