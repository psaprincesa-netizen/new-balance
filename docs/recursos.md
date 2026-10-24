# Cobertura do inventário solicitado

A lista recebida inclui centenas de funções de produtos maduros. Esta entrega implementa um núcleo utilizável comum; as funcionalidades abaixo marcadas como pendentes não foram implementadas nem simuladas como ativas. A tela **Recursos** apresenta essa distinção dentro da plataforma.

| Área solicitada | Disponível nesta versão | Próxima implementação necessária |
| --- | --- | --- |
| Planilhas / Excel | Editor Univer, abas, fórmulas, estilos, mesclagem, filtros, ordenação, validação, formatação condicional, CSV e XLSX (detalhes abaixo) | Gráficos avançados, pivôs, macros, Solver, Power Query e equivalência integral ao Excel |
| Power Query | Importação CSV local | Fontes externas, ETL, junções, transformações, atualizações e linguagem M |
| Power Pivot | Não implementado | Modelo relacional, medidas, KPIs, DAX e cubos |
| Documentos / Word | Texto com marcação de títulos, negrito e itálico, visualização, contagem, exportação Markdown, impressão do navegador | DOCX, estilos avançados, paginação, seções, cabeçalhos/rodapés, imagens, tabelas, gráficos, formas, referências acadêmicas, sumário, índices, mala direta, revisão e assinatura |
| Apresentações / PowerPoint | Slides textuais, criação, duplicação, remoção, reordenação, notas, apresentação por teclado, documento → slides | PPTX, mestre, temas, objetos, imagens, mídia, 3D, transições, animações, ações interativas, gravação e vídeo |
| Agenda / Outlook | Compromissos locais com início/fim e apresentação no fuso do navegador | Recorrência, disponibilidade, salas, convites, delegação e sincronização |
| Correio / Outlook | Não implementado | Conexão a provedor, pastas, contatos, mensagens, pesquisa, regras, anexos, envio e recebimento reais |
| Armazenamento / OneDrive | Biblioteca de arquivos próprios do DRAP office, histórico, lixeira e exportação JSON | Arquivos binários, upload/download, sincronização, cofre e armazenamento remoto |
| Notas / OneNote | Notas textuais, formatação simples, busca pela biblioteca | Cadernos/seções, desenho, PDF, multimídia, OCR e manuscritos |
| Comunicação / Teams | Compartilhamento de arquivos entre contas cadastradas | Chat, equipes/canais, menções, reações, áudio/vídeo, tela, legendas e telefonia |
| Formulários / Forms | Perguntas textuais, coleta no editor, histórico das perguntas por resposta e conversão para tabela | Coleta pública, múltipla escolha, escalas, quizzes, avaliações e análises especializadas |
| Dados / Access | Tabelas, campos textuais, registros, filtro, CSV e conversão para planilha | Tipagem, índices configuráveis, relacionamentos, consultas, formulários específicos e relatórios |
| Design editorial / Publisher | Impressão dos documentos pelo navegador | Layout editorial, guias, páginas-mestre e exportação gráfica profissional |
| Diagramas / Visio | Fluxo sequencial editável | Canvas, conectores livres, BPMN, organogramas, rede, engenharia e plantas |
| Projetos / Project | Kanban com prazos e indicadores | Cronogramas, marcos, dependências, recursos, custos, caminho crítico e linhas de base |
| Planner / To Do | Tarefas em três estados, prazos e contagem de conclusão | Subtarefas, etiquetas, prioridades, lembretes, listas pessoais e recorrência |
| Power Automate | Conversões manuais documento → slides, planilha → relatório, respostas → tabela, tabela → planilha | Gatilhos, agendas, conectores, condições, loops, aprovações e designer de fluxos |
| BI / Power BI | Indicadores reais de arquivos, tarefas e respostas do espaço | Modelagem, medidas, fontes externas, painéis configuráveis, mapas e publicação analítica |
| Portais / SharePoint | Página com texto e links para arquivos respeitando permissões | Sites públicos/intranet, listas avançadas, aprovações, biblioteca corporativa e políticas |
| IA / Copilot | Não conectado | Seleção de provedor, chaves seguras, políticas de dados, geração/resumo/análise e avaliações |
| Colaboração | Permissões de leitura/edição, revogação, versões e detecção de conflitos | Comentários, menções, alterações rastreadas e coautoria em tempo real |
| Segurança | scrypt, cookies HttpOnly/SameSite, origem, rate limit persistido no banco, autorização no servidor | Recuperação, MFA, SSO/OAuth, assinaturas, criptografia gerenciada e auditoria |
| Automação de código | Fórmulas analisadas por parser limitado, sem executar código do usuário | VBA, Office Scripts e ambientes de execução isolados |
| Acessibilidade | Labels, controles nativos, foco visível, status anunciados e teclado no apresentador | Auditoria WCAG, testes com leitores de tela, textos alternativos e legendas |
| Publicação | Aplicação executável em desenvolvimento; backup e restauração locais testados | Hospedagem HTTPS, observabilidade, operação, recuperação e teste no ambiente publicado |

## Ampliação implementada

| Área | Implementação adicionada | Limites que permanecem |
| --- | --- | --- |
| Documentos / notas / portais | Listas, checklist, tabelas Markdown, links seguros, busca/substituição; DOCX para documentos/notas | Não há paginação profissional nem fidelidade total de layout DOCX |
| Planilhas | Editor Univer; ver detalhes e limites na seção abaixo | Sem macros, pivôs, gráficos avançados, DAX, Power Query ou equivalência de todas as fórmulas |
| Apresentações | Temas e importação/exportação PPTX de textos e notas | Mídia, animações e objetos não são preservados na importação |
| Projetos | Responsáveis, prioridades e subtarefas | Sem caminho crítico ou planejamento de recursos |
| Agenda | Ocorrências repetidas e intercâmbio ICS | Sem envio de convites; recorrências importadas são expandidas em até 1000 ocorrências |
| Formulários | Tipos de campo, validação e links públicos revogáveis | Sem quizzes/ramificação; até 1000 respostas e limite de conteúdo |
| Tabelas | Tipos, validação, ordenação e remoção de duplicatas | Sem banco relacional configurável |
| Diagramas | Canvas, arraste, teclado, conectores e SVG | Sem bibliotecas BPMN/engenharia |
| Colaboração | Comentários, listagem de acessos e rascunhos locais recuperáveis | Sem coautoria em tempo real ou recuperação de senha |

Esta tabela atualiza os itens básicos da matriz acima. Correio, reuniões, IA e integrações de provedor continuam pendentes; a existência de um plano não os torna implementados.

## Sequência de evolução

1. Estabilizar o núcleo: recuperação de conta, rascunhos recuperáveis, auditoria, compartilhamentos listáveis e testes ampliados de acesso.
2. Profundidade dos editores: arquivos Office com bibliotecas especializadas, texto estruturado e paginação, planilhas com múltiplas abas e fórmulas adicionais, canvas de slides e diagramas.
3. Colaboração e arquivos: armazenamento de binários, comentários, equipes, permissões organizacionais e coautoria.
4. Serviços: correio e calendário via OAuth, chamadas via serviço de mídia, conectores de dados e automações com execução em filas.
5. IA e BI: provedor configurável, controles de privacidade, modelagem e dashboards editáveis.
6. Operação: deploy, testes de carga, segurança, monitoramento, backups externos e recuperação ensaiada.

Essa sequência é um plano técnico, não uma promessa de equivalência concluída. A cobertura de cada recurso deverá ser atualizada com testes à medida que for implementado.

## Planilha integrada — outubro de 2026

A grade inicial foi substituída pelo **Univer 1.2.0**, distribuído com a aplicação (Apache-2.0), com interface em português. Oferece edição no canvas, seleção de intervalos, copiar/colar, preenchimento, desfazer/refazer, fontes/cores/bordas, formatos numéricos, mesclagem, linhas/colunas, abas, fórmulas, filtros, ordenação, validação de dados e formatação condicional. A edição salva o snapshot nativo completo no banco, inclusive regras, mantendo versões e permissões. Planilhas antigas são convertidas ao abrir sem apagar o histórico.

O XLSX importa/exporta valores, fórmulas, estilos básicos, formatos numéricos, mesclagens, dimensões e painéis congelados. A exportação inclui filtros por valores, validações comuns e regras condicionais numéricas/por fórmula; regras avançadas permanecem no snapshot/JSON. A importação também preserva filtros por valores, validações comuns e regras condicionais numéricas/por fórmula. Gráficos de colunas, linhas e pizza vinculados a intervalos são salvos no DRAP e exportados para SVG e XLSX editável. A importação de gráficos Excel, gráficos avançados, tabelas dinâmicas, macros, Power Query e equivalência integral ao Excel continuam pendentes.

Limites persistidos: 20 abas, 50 mil células preenchidas, 2 MB de conteúdo JSON por arquivo, coordenadas até 100 mil linhas × 1024 colunas. Importação XLSX: 2,5 MB comprimidos com inspeção do ZIP. CSV: até 10 mil linhas × 256 colunas, respeitando o total de 50 mil células. Os limites são verificados, sem truncamento silencioso. Fórmulas nativas usam nomes em inglês; o campo auxiliar normaliza nomes portugueses.

O editor usa canvas: o campo auxiliar permite selecionar intervalos e inserir conteúdo por teclado, mas isso não constitui conformidade integral com leitores de tela. O CSS requer estilos inline; a política continua bloqueando scripts inline e `unsafe-eval`.

Gráficos: até dez definições por pasta, cada uma com rótulos e uma série numérica (duas colunas com cabeçalho e até 200 linhas). A vinculação usa endereços literais; inserir/excluir linhas não ajusta automaticamente esses endereços. Gráficos de pizza exigem dados não negativos.
