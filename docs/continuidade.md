# Continuidade solicitada

O usuário pediu para continuar editando quando retornar e completar as ferramentas da plataforma unificada. Usar `recursos.md` e os documentos/backlog fornecidos como referência de cobertura; não apresentar funcionalidades planejadas como disponíveis.

## Prioridade atual

Manter a plataforma abrindo em https://new-balance-pi.vercel.app e preservar os dados existentes no Neon. O erro 500 de inicialização foi causado pelo método `handle_request` da aplicação, sobrescrito pelo wrapper do runtime Vercel. A aplicação passou a usar `dispatch_application_request`; o teste HTTP de implantação cobre a colisão com o método reservado do runtime.

## Próximas entregas por módulo

1. Núcleo comum: auditoria administrativa, recuperação de conta e cotas. Rascunhos, comentários e acessos listáveis foram implementados.
2. Documentos e planilhas: ampliar fidelidade de Office, paginação, imagens, pivôs e conectores. Abas, motor de fórmulas e intercâmbio Office já foram adicionados.
3. Apresentações e diagramas: imagens e objetos de apresentação; bibliotecas de diagramas. Temas, conectores e canvas de diagramas foram adicionados.
4. Projetos, agenda, formulários e tabelas: dependências, convites, quizzes, relacionamentos. Subtarefas, ocorrências repetidas, ICS, coleta pública e tipos de campos foram adicionados.
5. Colaboração, arquivos e portais: equipes, armazenamento binário, permissões organizacionais e coautoria.
6. Integrações externas de correio, chamadas, automação e IA: implementar cada provedor com suas credenciais protegidas e fluxos reais.

Cada entrega deve atualizar o mapa de cobertura, verificar persistência e permissões, executar os testes relevantes, publicar e validar a jornada no domínio real. Status READY do deploy não substitui teste HTTP e navegador. Não alterar dados reais para testes; usar apenas registros sintéticos isolados.

## Marca e integrações

Nome confirmado: DRAP office. Cor: verde-exército #4B5320. Não aplicar a imagem gerada como logo definitiva: ela não garante a geometria exata exigida. Falta o original em arquivo para edição determinística autorizada. Foi solicitada a escolha Microsoft 365 ou Google Workspace para correio/calendário/reuniões, ainda sem resposta. Nunca pedir segredos no chat.

## Atualização: planilha Univer

Substituída a grade básica por Univer com presets comunitários de núcleo, filtros, ordenação, validação e formatação condicional. Persistência usa `content.workbook`, migração compatível de matrizes legadas e exportação Office. Gráficos próprios vinculados a intervalos ficam em `content.charts` e são exportados como SVG ou gráficos editáveis no XLSX. `tests/browser_spreadsheet.py` verifica operações reais, persistência, exportação e acesso somente leitura. O plugin de proteção interna do Univer não representa o sistema de contas DRAP; menus de gestão dessa proteção foram ocultados. Permissões por arquivo continuam validadas pelo backend.

Pendências de planilhas: pivôs, tipos avançados de gráficos, importação de gráficos, mais fidelidade de temas/rich text e regras Office, impressão paginada, proteção por célula com autorização no backend, conectores e macros. Não declarar inventário 100% completo.
