# Publicação e configuração verificadas

- Projeto: `new-balance`, equipe `psaprincesa-netizens-projects`.
- Produção: https://new-balance-pi.vercel.app
- Download: https://new-balance-pi.vercel.app/downloads/drap-office.zip
- O domínio publicado respondeu HTTP 200; o ZIP de produção foi baixado e sua integridade verificada. As jornadas remotas confirmaram cadastro/login, DOCX, XLSX, comentários, rascunhos e coleta pública com revogação.
- A revisão DRAP office mantém o banco Neon existente e o schema `nexo`; não renomeia tabelas nem contas.
- O erro 500 de execução foi corrigido renomeando o método da aplicação que colidia com `handle_request` do runtime Vercel. A rota de saúde voltou a responder 200 no domínio real.
- Validação desta revisão: 40 testes Python, 16 testes JavaScript e quatro jornadas Chromium aprovadas. Cobertura: dez editores, persistência, conversões, fórmulas, comentários, rascunhos, DOCX/XLSX, coleta pública sem login com revogação, canvas/SVG e tela móvel.
- O build remoto aplica as migrações aditivas de comentários e publicação de formulários antes de liberar a função. Os links públicos são ativados somente pelo proprietário, por formulário.
- Download atual: `/downloads/drap-office.zip`. O link antigo `/downloads/nexo.zip` é mantido como compatibilidade.
- A logo gerada não foi aplicada: não garante a geometria idêntica exigida. A marca textual DRAP office e a cor verde-exército foram aplicadas.
- Correio, reuniões, IA, macros, DAX e equivalência integral a todos os recursos Office continuam pendentes conforme `recursos.md`. Nenhuma integração inexistente é apresentada como ativa.

## Guia oficial Vercel

Foi consultado https://vercel.com/get-started.md.

- CLI 65.2.0 instalada e autenticada como `psaprincesa-netizen`; projeto vinculado e publicação concluída pela CLI.
- Plugin global: instalação falhou porque `/home/agent/.cache/plugins` não pode ser criado neste ambiente. A documentação oficial foi consultada antes do fallback.
- Skills globais: fallback tentou instalar em `/home/agent/.agents`, também indisponível. Nenhuma instalação foi declarada concluída.
- MCP: `codex mcp add vercel --url https://mcp.vercel.com` falhou porque `/run/codex-environment/codex-home/config.toml` está em sistema de arquivos somente leitura. Não houve conexão MCP nem teste autenticado `list_teams`.
- A CLI autenticada permite publicar independentemente da configuração MCP.

A publicação é feita a partir do workspace com a CLI autenticada; o workflow `.github/workflows/verify.yml` valida alterações de código e as quatro jornadas de navegador. O ZIP é uma distribuição do código-fonte, sem dados de contas ou credenciais. Recursos ainda não implementados estão em `recursos.md`; riscos operacionais estão em `auditoria-vercel.md`.

A planilha Univer foi verificada também em produção: edição nativa, fórmulas, estilos, mesclagem, filtros, ordenação, validação, formatação condicional, persistência e XLSX. A revisão atual inclui gráficos vinculados (SVG/XLSX editável), importação de regras, backup JSON e teste de acesso somente leitura. O código está na branch `main` do repositório informado; a verificação automatizada no GitHub Actions passou.

Tabelas dinâmicas DRAP: agrupamento por linhas/colunas, seis agregações, filtro, ordenação por total e consulta dos registros. Os cálculos JS/Python usam os mesmos casos de teste. A jornada de navegador verifica atualização por fórmula, salvamento, recuperação JSON, acesso somente leitura e resultados XLSX como tabelas comuns (sem objetos PivotTable nativos).
