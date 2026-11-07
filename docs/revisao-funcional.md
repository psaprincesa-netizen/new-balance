> Registro histórico. A revisão atual e o cancelamento da integração Google estão em [revisao-2026-11-02.md](revisao-2026-11-02.md). As referências à configuração OAuth abaixo descrevem uma etapa encerrada.

# Revisão funcional e de desempenho

Escopo: ferramentas disponíveis no DRAP office e seus fluxos de trabalho. Recursos indicados como planejados no mapa de cobertura continuam pendentes; esta revisão não declara equivalência completa com Google Workspace ou Microsoft 365.

## Correções

- Biblioteca e entrada carregam metadados, sem baixar conteúdo/anexos de todos os arquivos. Busca por conteúdo permanece disponível no servidor, respeitando acessos.
- A troca para a biblioteca é imediata, com atualização em segundo plano. O editor anterior é desmontado antes da espera, e a busca mantém o foco.
- Criar e salvar aproveitam a resposta já recebida, evitando recarregar toda a biblioteca e repetir a consulta do arquivo.
- CSV é separado do parser de fórmulas. O JavaScript inicial é empacotado e os editores pesados começam a carregar junto da abertura do arquivo.
- PostgreSQL reutiliza conexões limitadas, com verificação TLS, rollback e recuperação de conexões encerradas. Usuários sem sessão não provocam consulta de sessão ao banco.
- Indicadores são calculados sob demanda; backups continuam completos.

## Verificação

| Área | Fluxos verificados |
| --- | --- |
| Documentos e notas | Edição visual e Markdown, formatação, tabelas, imagens, colagem, rascunho, histórico, DOCX, página e estrutura |
| Planilhas | Edição nativa, fórmulas, múltiplas abas, seleção, desfazer/refazer, formatos, filtros, ordenação, validação, formatação condicional, gráficos, tabelas dinâmicas, CSV/XLSX |
| Apresentações | Objetos, texto, imagem, alinhamento, arraste, camadas, tema, ocultação, apresentação, notas e PPTX |
| Projetos | Tarefas, status, subtarefas, persistência e indicadores |
| Agenda | Eventos, edição, repetição e ICS |
| Formulários | Campos tipados, respostas, publicação, revogação e conversão para tabela |
| Tabelas | Tipos, filtros, registros, CSV e conversão para planilha |
| Diagramas e portais | Canvas, teclado, SVG, texto, vínculos e acesso somente de leitura |
| Biblioteca | Busca no conteúdo, catálogo com 103 itens, backup completo, compartilhamento/revogação, histórico, lixeira e restauração |
| Inserir | DOCX/TXT, imagem, arquivos binários, vínculos, download, limites e persistência |
| Instalação | Manifesto/ícones, critérios Chromium, fluxo de confirmação simulado, preservação da edição, página offline e tamanhos móveis |

Resultado local: 59 testes Python, 27 testes JavaScript e 12 jornadas de navegador aprovados. Testes adicionais com PostgreSQL 17 real verificaram TLS, concorrência, permissões entre instâncias, reaproveitamento, rollback e recuperação de conexão encerrada.

Limites da validação: Chromium automatizado e layouts móveis; não constitui teste em todos os modelos físicos, carga de produção ou instalação nativa em Windows/macOS/iOS/Android. O aplicativo continua dependendo de internet para login, abertura e salvamento. Integrações externas e recursos planejados continuam identificados no mapa de cobertura.

## Medição anterior em produção

Conta sintética isolada com seis arquivos: 8,44 s para entrar na biblioteca, 6,98 s para navegar até todos os arquivos e 2,90 s para abrir um projeto. A listagem transferiu 621.529 bytes de JSON contendo documentos. Medição feita pelo mesmo navegador automatizado e proxy; não representa promessa de tempo em todas as redes.

## Medição após publicação

| Etapa | Antes | Depois |
| --- | ---: | ---: |
| Abrir tela de entrada | 5.80 s | 1.54 s |
| Entrar na biblioteca | 8.44 s | 2.29 s |
| Navegar para todos os arquivos | 6.98 s | 1.92 s |
| Abrir um projeto | 2.90 s | 1.91 s |

A resposta inicial passou de 621.529 bytes de conteúdo para 1.485 bytes de sessão e metadados. Os valores são de uma medição comparativa com a mesma conta sintética, Chromium e proxy; latência, rede, tamanho dos arquivos e início do banco podem variar.

Conferência no domínio oficial: os dez editores abriram, salvaram alterações e preservaram versão/histórico no PostgreSQL. DOCX, XLSX, PPTX e ICS foram baixados como arquivos reais. Indicadores abriram sem erros JavaScript. Foram usados apenas contas e arquivos sintéticos; os arquivos criados foram enviados à lixeira ao final.

Na conferência da publicação final, a navegação mostrou a biblioteca já conhecida em 0,04 s, enquanto a revalidação estava pendente. Abrir e editar um projeto durante essa atualização preservou a tela e salvou a tarefa corretamente; a resposta atrasada não substituiu o editor. A função publicada não registrou erros/falhas fatais na janela de logs consultada.

## Implementação adicional — 28/10/2026

Esta etapa acrescenta funções, além da revisão anterior: formatação rica por trecho, abas de documentos, notas reais no DOCX, cabeçalho/rodapé e numeração, sumário atualizável, modelos e tabelas mescladas; cinco gráficos adicionais e proteção de intervalos; grupos/rotação em PPTX e apresentador separado; dependências/cronograma; agenda mensal; quizzes com gabarito privado, pontuação e novos campos; integração Google com OAuth/PKCE e tokens criptografados.

Verificação local desta etapa: **71 testes Python, 29 testes JavaScript e 13 jornadas de navegador**. Inclui persistência e exportação dos novos recursos, rejeição de alterações em células protegidas, grupos em PPTX, notas privadas fora da janela do público, ciclos de tarefas, correção de quizzes e sigilo do gabarito. A jornada Google usa respostas simuladas do provedor; a conexão real requer cliente OAuth e consentimento do titular. Detalhes em configuração OAuth (retirada do escopo).

Os demais recursos ainda pendentes estão discriminados em [google-workspace.md](google-workspace.md) e no mapa de cobertura do aplicativo. Esta entrega não declara paridade integral com Google Workspace.

Publicação desta etapa: `dpl_Ez7TmXRfngLgZSC2PSM8EDwYcXCK`, promovida para https://new-balance-pi.vercel.app. Saúde da API e novos arquivos estáticos responderam corretamente. A jornada dos novos recursos passou no domínio principal, incluindo formatação/abas/DOCX, grupos e notas privadas em janela separada, gráficos/proteção, dependências, mês da agenda e quiz. A tela Google e o endpoint autenticado confirmaram `configured: false`, pois o ID/segredo OAuth ainda não foram cadastrados; a chave de criptografia já está provisionada como segredo Production.

PostgreSQL local com TLS também verificou as novas tabelas Google, consumo atômico do estado OAuth, persistência criptografada e desconexão com provedor simulado. Nenhum e-mail ou convite real foi enviado. Uma primeira passagem geral em produção teve falha de rede no navegador ao salvar uma nota; a revisão foi repetida com diagnóstico de requisições. Os logs consultados não indicaram erros/falhas fatais da função publicada.

Na segunda passagem, os dez editores e os indicadores passaram em produção: abertura, salvamento, persistência, versões/histórico e DOCX/XLSX/PPTX/ICS aplicáveis, sem erros JavaScript ou falhas de requisição registradas. A nota que sofreu a interrupção de rede também salvou e exportou normalmente. Arquivos sintéticos foram enviados à lixeira e as sessões de teste encerradas.
