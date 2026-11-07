# Comparação com Google Docs, Planilhas e Apresentações

Referências consultadas em 26/10/2026. Os três endereços enviados levam às páginas públicas dos produtos. Este inventário compara capacidades com o DRAP office; não representa acesso ao código do Google, conexão à conta Google ou equivalência integral. As funções abaixo são implementações próprias.

## Documentos

| Grupo | Estado no DRAP |
| --- | --- |
| Edição visual, títulos, negrito/itálico, links, imagens, tabelas, listas, checklist, desfazer/refazer | Existente |
| Estrutura navegável pelos títulos | Adicionado nesta entrega; acompanha edições |
| Contagem de palavras, caracteres e caracteres sem espaços; contagem da seleção | Adicionado nesta entrega |
| Lista numerada, citação, bloco de código e linha horizontal | Controles adicionados ao editor visual, persistidos em Markdown |
| Papel A4/Carta, retrato/paisagem e margens | Adicionado para impressão/PDF e DOCX; edição contínua, sem simulação de paginação |
| Fonte, tamanho, alinhamento e espaçamento | Fonte global e formatação individual por trecho com fonte, tamanho, cores, realce, sublinhado, tachado e sobrescrito/subscrito, persistidos no formato rico e DOCX |
| Largura de página/largura livre | Adicionado para visualização; não é o formato paginado completo do Google |
| Importação/exportação DOCX | Existente; agora preserva papel/orientação/margens e fonte básica suportados. Não preserva layouts/seções arbitrários |
| Abas, sumário e notas de rodapé | Implementados; sumário atualizado pelo botão, notas reais no DOCX. Marcadores e citações acadêmicas continuam pendentes |
| Cabeçalho/rodapé e numeração | Implementados; numeração de páginas no DOCX. Seções, colunas e paginação profissional permanecem pendentes |
| Sugestões e alterações rastreadas, comparação de documentos, tradução e digitação por voz | Pendente |
| Modelos | Relatório, ata, carta e proposta inseridos sem apagar conteúdo. Chips, variáveis e criação de modelos personalizados pendentes |

## Planilhas

| Grupo | Estado no DRAP |
| --- | --- |
| Abas, fórmulas, formatos, mesclagem, ordenação, filtros, congelamento, validação e formatação condicional | Existente no Univer; fidelidade e limites registrados em recursos.md |
| Gráficos de colunas/linhas/pizza, tabelas dinâmicas de um nível, CSV/XLSX | Existente; não equivale a todos os gráficos e pivôs do Google |
| Remover espaços extras, duplicatas e linhas vazias | Adicionado |
| Dividir texto pelo separador informado e transpor linhas/colunas | Adicionado |
| Substituição literal com opção de diferenciar maiúsculas | Adicionado |
| Estatísticas de intervalo: preenchidas, números, soma, média, mínimo e máximo | Adicionado; valores de texto não são convertidos em números |
| Gráficos adicionais | Área, rosca, barras horizontais, dispersão e radar, com SVG e objetos nativos no XLSX. Segmentações, múltiplas séries e pivôs multinível pendentes |
| Proteção por intervalo | Proprietário define intervalos; servidor recusa alterações por editores compartilhados. Filtros por usuário e notificações condicionais pendentes |
| Funções exclusivas Google, funções nomeadas, Connected Sheets, fontes externas e atualização agendada | Pendente |
| Apps Script, macros e complementos | Pendente |

As transformações criam uma **cópia de valores calculados**, sem fórmulas/estilos da origem, em uma área vazia da mesma aba. Rejeitam destinos ocupados ou mesclados; o texto começando com `=` permanece texto. Não deslocam nem removem linhas da origem. A barra nativa permite desfazer. Limites: 10 mil linhas, 256 colunas e 50 mil células, respeitando também a cota persistida do documento. A primeira linha pode ser preservada como cabeçalho na remoção de duplicatas/vazias. A divisão usa um separador literal (não é um parser CSV com aspas).

## Apresentações

| Grupo | Estado no DRAP |
| --- | --- |
| Criar, duplicar, reordenar, excluir slides; texto, formas, imagens e camadas | Existente |
| Alinhar objeto à esquerda/centro/direita/topo/meio/base | Adicionado, relativo à página |
| Distribuir todos os objetos horizontal/verticalmente | Adicionado, pelo espaço livre entre objetos; exige três objetos e espaço suficiente |
| Fundo e cor do título/conteúdo por slide; aplicar estilo a todos | Adicionado; cores dos objetos continuam individuais |
| Ocultar slides na apresentação | Adicionado; slide permanece no editor, impressão e PPTX |
| Transições dissolver/deslizar | Adicionado no navegador e PPTX; respeita preferência de movimento reduzido no navegador |
| Notas durante a apresentação, próximo título, cronômetro | Adicionado; notas aparecem na mesma tela e podem ser vistas ao compartilhar essa tela |
| Tela preta, tela cheia, avanço a cada cinco segundos, Home/End/PageUp/PageDown | Adicionado |
| PPTX com fundos, slides ocultos e transições suportadas | Adicionado à importação/exportação existente |
| Organização de objetos e estilos | Seleção múltipla, agrupamento, arraste/teclado em grupo, rotação e exportação/importação PPTX. Layout em duas colunas e estilo para novos slides. Mestre completo, conectores e layouts herdados pendentes |
| Áudio/vídeo, animação individual, recorte/máscaras, gráficos e tabelas vinculados | Pendente |
| Apresentador em janela separada | Implementado: notas e cronômetro na tela de controle; janela do público sem notas. Legendas, perguntas, gravação e vídeo pendentes |

## Capacidades compartilhadas

Compartilhamento entre contas DRAP, permissões por arquivo, comentários, histórico de versões e recuperação de rascunhos já existem. Coautoria em tempo real, menções/notificações, modo offline completo, sincronização Drive, publicação incorporável, complementos Google e Gemini continuam pendentes. A integração externa com Gmail, Agenda e Meet foi retirada do escopo e da interface em 02/11/2026 por solicitação do proprietário. A agenda interna e a importação/exportação ICS continuam disponíveis. A implementação dessas capacidades exige arquitetura e, em alguns casos, conexão a provedores; não foram simuladas com botões sem funcionamento.

## Fontes oficiais

- [Google Docs](https://workspace.google.com/products/docs/), [Google Sheets](https://workspace.google.com/products/sheets/) e [Google Slides](https://workspace.google.com/products/slides/).
- [Estrutura do documento](https://support.google.com/docs/answer/6367684), [contagem de palavras](https://support.google.com/docs/answer/39003), [configuração de página](https://support.google.com/docs/answer/10296604), [páginas/largura contínua](https://support.google.com/docs/answer/11528737), [abas de documentos](https://support.google.com/docs/answer/15499791).
- [Limpeza e divisão de dados](https://support.google.com/docs/answer/6325535), [funções do Google Sheets](https://support.google.com/docs/table/25273).
- [Fundos e layouts](https://support.google.com/docs/answer/1705254), [transições e animações](https://support.google.com/docs/answer/1689475), [organização e ocultação de slides](https://support.google.com/docs/answer/1694830).

## Verificação

`tests/sheet-tools.test.js` cobre transformações, tipos, substituição literal, limites e estatísticas. `tests/test_google_tools.py` cobre contratos e roundtrip DOCX/PPTX. `tests/browser_google_tools.py` percorre os controles reais, rejeição de destino ocupado, persistência depois de recarregar, apresentação sem o slide oculto e arquivos Office baixados. As jornadas existentes de documentos, slides e planilhas verificam regressões e permissões.

## Outros editores ampliados em 28/10/2026

Projetos: dependências verificadas no servidor, ciclos rejeitados, bloqueio de início até predecessoras concluídas e cronograma visual. Agenda: mês navegável e abertura do compromisso pelo dia. Formulários: texto longo, avaliação de 1 a 5, quiz com gabarito privado, correção no servidor e notas nas exportações. Não incluem caminho crítico, convites automáticos, anexos nas respostas ou ramificação.
