# Conclusão dos módulos por etapas

Cada entrega deve ter uma jornada utilizável, validação no servidor, permissões,
persistência e testes. Implementado localmente não significa publicado ou módulo completo.
Não há estimativa de prazo nem promessa de equivalência integral ao Microsoft 365.

| Etapa | Entregas | Situação |
| --- | --- | --- |
| 1 — Projetos | Horas planejadas/realizadas, custo por hora, custos adicionais, totais e agrupamento por responsável | Publicado e validado no domínio de produção |
| 1 — continuação | Linha de base do cronograma/orçamento, comparação de desvios, capacidade diária dos responsáveis | Publicado; jornada de produção aprovada |
| 2 — Editores e dados | Paginação e revisão de documentos; pivôs multinível e XLSX nativo; apresentações multimídia; relacionamentos de tabelas; bibliotecas de diagramas | Pendente |
| 3 — Arquivos e colaboração | Binários, equipes, permissões organizacionais, portais e coautoria | Pendente; armazenamento precisa de provedor e política de cotas |
| 4 — Automação | Gatilhos internos, condições, histórico, repetição segura, agendamentos e aprovações | Pendente |
| 5 — Integrações e inteligência | Correio/calendário/reuniões, conectores externos, IA e BI configurável | Pendente; provedores e autorização necessários |
| 6 — Operação e aceite | Cotas, auditoria administrativa, isolamento de ambientes, alertas, carga, restauração PostgreSQL, acessibilidade e jornada publicada | Pendente; deve acompanhar as etapas anteriores |

## Entrega 1: recursos e custos de Projetos

Em **Detalhes** de cada tarefa: responsável, horas planejadas, horas realizadas,
custo por hora e custos adicionais. Valores financeiros em BRL.
**Recursos e custos** mostra horas e custos totais e por responsável.
Custo planejado = horas planejadas × custo por hora + custos adicionais.
Custo realizado = horas realizadas × custo por hora + custos adicionais.
Os custos adicionais são comuns aos dois totais; não são um lançamento financeiro separado.
A diferença é realizado menos planejado. Arredondamento de dinheiro por tarefa,
em centavos, antes de somar. Campos ausentes em projetos antigos equivalem a zero.

O servidor aceita apenas números finitos entre zero e cem mil por campo.
As permissões e o histórico existentes protegem o conteúdo. Não há migração de schema.
Na primeira entrega não havia linha de base ou capacidade. A entrega 2, abaixo,
adiciona esses recursos. Integração contábil e nivelamento automático permanecem pendentes.

Validação local: 29 testes JavaScript, 81 testes Python (incluindo 8 de workspace), verificação de sintaxe,
build e jornada Chromium de Projetos (custos, dependências, ciclo, cronograma,
caminho crítico e persistência). Publicada em produção: deployment `dpl_FZuVeoio86cEHfAAZc9EQpdbUzZW`, em
https://new-balance-pi.vercel.app. A versão mais recente de produção foi incorporada
antes da publicação para preservar melhorias de outros módulos. Após a integração:
108 testes Python, 39 JavaScript, build, sintaxe e Chromium local aprovados.
No domínio publicado: saúde da API com status ok, módulo project.js conferido por
SHA-1 e jornada Chromium de cadastro, custos, dependências, salvamento e reabertura
aprovada com conta sintética isolada.

## Entrega 2: linha de base, capacidade e Gemini

Projetos ganha registro do cronograma efetivo e orçamento, comparação de tarefas
existentes/adicionadas/removidas, desvios de prazo/custo/horas e substituição da
linha de base com confirmação. O conteúdo fica no histórico normal do projeto.
IDs referenciados na linha de base não são reutilizados ao criar novas tarefas.

Capacidade: padrão de 8 h/dia, configurável de 0 a 24 por responsável (até 200 perfis).
Esforço planejado distribuído uniformemente por dias corridos do cronograma efetivo,
inclusive fins de semana. Mostra pico, dias e intervalos de sobrecarga; informa tarefas
sem datas ou responsável. Não nivela o cronograma automaticamente, não calcula feriados,
não distribui uma tarefa entre múltiplos responsáveis e não agrega outros projetos.

IA escolhida pelo proprietário: Google Gemini. Implementação e limites em
[gemini.md](gemini.md). A jornada de IA envolve um provedor real e não está concluída
até validar autenticação, créditos e uma geração no ambiente publicado.

## Entrega 3: ferramentas de Diagramas

Formas de processo, decisão, início/fim, documento e banco de dados; conexão com
rótulo; modelos independentes de fluxograma, organograma e arquitetura de aplicação.
As setas alcançam a borda das formas. O SVG preserva formas, textos e rótulos.
O modelo cria um novo arquivo; os diagramas anteriores continuam compatíveis.
Não implementa semântica de BPMN, simulação, plantas ou bibliotecas de engenharia.

## Evidência da publicação atual

Deployment final: `dpl_ARiXSZLz7agnqrCCnHZofQuYuKN5`, status READY,
https://new-balance-pi.vercel.app. API saudável; Projetos e Diagramas passaram
no Chromium em produção com contas sintéticas isoladas (arquivos de teste para
lixeira e sessões encerradas). Validação local da entrega: 116 testes Python,
44 JavaScript, build/sintaxe e três jornadas Chromium aprovados; os dois testes
adicionais de OIDC/ativação também passaram na suíte focada de oito testes de IA.

Gemini: autenticação OIDC configurada e recebida por requisição. A chamada real
chega ao AI Gateway, que responde HTTP 403 `customer_verification_required`.
O titular precisa ativar/verificar a conta com forma de pagamento válida na
Vercel. Não houve geração real bem-sucedida. O aplicativo apresenta essa ação
sem simular resultados ou divulgar credenciais. Não comprar créditos nem
alterar dados de cobrança automaticamente. Após a ativação, repetir apenas
uma geração sintética e registrar a evidência.

Permanecem pendentes automações com execução/agendamento, coautoria/equipes,
modelagem/BI, recursos avançados de editores e operação/carga/acessibilidade.
As conexões de correio e reuniões removidas anteriormente não foram reativadas.

## Entrega seguinte: relacionamentos entre tabelas

Implementada consulta por igualdade entre campos, com até dez vínculos por tabela,
resultados paginados, persistência/histórico e verificação de acesso às duas tabelas.
Leitores consultam apenas destinos autorizados. O vínculo não concede permissões.
Versões divergentes ou campos de destino alterados/ambíguos recusam a consulta.
Sem SQL, integridade referencial obrigatória ou exclusão em cascata. A definição
é preservada no JSON, sem remapeamento de IDs nas importações.

Testes locais: suíte Python geral aprovada (127 testes na execução registrada),
cinco testes específicos de relações aprovados, build/sintaxe e jornada Chromium
de criação, persistência, consulta, leitura e revogação aprovados.

Publicação de relacionamentos: `dpl_8pipUvACFaVqLoHKGcuQgJY2BtWV`, READY em
https://new-balance-pi.vercel.app. Chromium em produção aprovou criar vínculo,
salvar/reabrir, consultar registros, acesso de leitura e bloqueio imediato após
revogação do destino. Arquivos sintéticos foram movidos à lixeira e sessões
encerradas. A consulta de logs da implantação não retornou erros/falhas fatais.

## Continuação — reconciliação e ramificação

A publicação encontrada no início desta continuação era `dpl_4AXQD9cZxm4vBVLPDwve2CuUJxG6`.
Ela incluía gráficos multissérie e pivôs com subgrupos, mas não continha vários
recursos publicados anteriormente neste chat. O código foi reconciliado usando o
ancestral Git como referência, preservando a formatação rica, abas, apresentações,
proteção de células, MFA, biblioteca, abertura direta, exclusão, relações entre
tabelas e Projetos; e incorporando gráficos com até seis séries, colunas empilhadas,
pivôs com dois níveis, cabeçalhos/rodapés e numeração na impressão/DOCX.

Formulários agora têm exibição condicional por resposta de escolha única anterior,
com cadeias sem ciclos, limpeza dos campos ocultos e pontuação apenas das questões
visíveis. A validação do servidor não confia na visibilidade calculada pelo navegador.
Os limites permanecem registrados no mapa de recursos; não é conclusão de toda a suíte.

## Automação interna: formulário público → tarefa

Implementada regra persistente, administrada pelo dono do formulário, com destino
restrito a projeto do mesmo dono, título por resposta, prioridade, condição opcional,
registro de execuções e reprocessamento de falhas. Formulário, tarefa e execução
confirmam na mesma transação; falhas esperadas do destino são registradas enquanto
a resposta é preservada. Novas tabelas são aditivas. O navegador envia identificador
por tentativa para deduplicação; clientes antigos permanecem compatíveis.

Esta é uma automação síncrona de gatilho interno. Agendamento, conectores externos,
aprovações e designer de fluxos ainda não foram implementados.

## Continuação — BI configurável

Painel pessoal com até 12 indicadores de tabelas/projetos, agregação, agrupamento,
filtro exato, exportação CSV, edição/exclusão individual e controle de conflitos.
Cada leitura revalida a autorização das fontes; fonte alterada, removida ou sem
acesso gera erro localizado. Configuração persistida em tabela aditiva `dashboards`.

## Aprovações de tarefas de formulários

A regra pode guardar solicitações pendentes até uma decisão do proprietário.
Inclui consulta privada da resposta original, aprovar/rejeitar, registro da decisão,
idempotência concorrente e reprocessamento de uma tarefa aprovada que falhou.
Estados e snapshots adicionais usam as tabelas transacionais existentes.
