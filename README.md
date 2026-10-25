# DRAP office · Plataforma unificada de produtividade

Uma interface em português para trabalhar com documentos, planilhas, apresentações, notas, projetos, agenda, formulários, tabelas, diagramas e portais. Os dez editores compartilham contas, biblioteca, busca, permissões, histórico e lixeira.

Esta é uma **primeira versão funcional**, não a implementação completa de todos os recursos do Microsoft 365 listados no documento enviado. O [mapa de cobertura](docs/recursos.md) registra o que existe e o que ainda precisa ser implementado. Não há integração ativa com Microsoft, correio, chamadas ou IA.

## Vercel e download

Produção: https://new-balance-pi.vercel.app · [Baixar código-fonte ZIP](https://new-balance-pi.vercel.app/downloads/drap-office.zip).

A adaptação para Vercel inclui frontend estático, função Python e backend PostgreSQL com TLS, sem usar disco temporário para persistir dados. Siga [o guia de publicação](docs/vercel.md) e [a auditoria de riscos](docs/auditoria-vercel.md). O projeto Vercel `new-balance` está vinculado ao Neon existente; o build aplica o schema antes de disponibilizar a função.

`npm run build` prepara `public/` e o ZIP servido pelo botão **Baixar plataforma**. `npm run download` gera `dist/drap-office.zip`. Esses pacotes contêm código-fonte, não dados de contas ou instalador desktop.

## Executar

Requisitos: Python 3.12+; Node 24+ para o build e testes de JavaScript. Instale as dependências Python de `requirements.txt` e as dependências JavaScript com `npm ci`. O build empacota o motor de fórmulas e o editor Univer; o modo local usa SQLite e o modo Vercel usa PostgreSQL.

```sh
cd /workspace/new-balance
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
npm run build
.venv/bin/python -m server.app
```

Abra a aplicação servida na porta 8000 pelo seu ambiente de desenvolvimento. Crie sua própria conta; não há senha padrão ou conta de demonstração. A autenticação exige senha com pelo menos 12 caracteres. O banco é criado em `.data/platform.sqlite`, fora do controle de versão.

Configurações opcionais: `HOST` (padrão `127.0.0.1`), `PORT` (8000), `DATABASE_PATH` e `COOKIE_SECURE=1` para cookies em HTTPS. Nunca use credenciais reais como dados de teste.

## Recursos ampliados

- DOCX, XLSX e PPTX reais para importar/exportar texto, células, abas, slides e notas. A importação informa perdas de layout, imagens, gráficos e mídia; não promete fidelidade completa ao Office.
- Até 20 abas por pasta, fórmulas entre abas e motor de expressões com funções de busca, datas, texto, estatística e finanças. Funções de rede são bloqueadas; macros não são executadas. Importação Office: até 2,5 MB e 24 MB expandidos, conteúdo de cada arquivo limitado a 2 MB.
- Comentários privados por arquivo, lista de acessos para o proprietário e recuperação de rascunhos no mesmo navegador. Os rascunhos não substituem o salvamento no servidor.
- Formulários com texto, e-mail, número, data e escolha única; link público ativado/revogado pelo proprietário. Respostas públicas não expõem a coleção de respostas e são limitadas por IP, tamanho e quantidade.
- Tarefas com responsável, prioridade e subtarefas; agendas com repetições em ocorrências individuais e intercâmbio ICS; tabelas tipadas, ordenação e deduplicação; diagramas com canvas, conexões e SVG; temas de apresentações.

A marca visível é **DRAP office**, em verde-exército. A logo gerada foi rejeitada como definitiva porque não garante geometria idêntica à referência. A aplicação utiliza apenas o nome até receber um arquivo original apropriado para edição exata.

## Jornada integrada

1. Crie um documento com títulos `#` e `##`; escreva e salve.
2. Use **Criar apresentação** para gerar slides a partir das seções. Apresente com as setas do teclado; Esc encerra.
3. Crie uma planilha e insira valores e fórmulas: `=A1+B1`, `=SOMA(A1:A5)`, `=MÉDIA(A1:A5)`. Use a barra do editor para formatação, mesclagem, filtros, ordenação e regras. Importe/exporte CSV e XLSX; salve para persistir as alterações. No editor nativo, use funções em inglês; o campo auxiliar aceita nomes portugueses.
4. Gere um relatório da planilha. Respostas de formulários podem virar tabelas; tabelas podem virar planilhas.
5. Organize tarefas no Kanban e compromissos na agenda. Consulte os indicadores calculados desses dados.
6. Compartilhe um arquivo com outra conta cadastrada, em modo leitura ou edição. Revogue usando o mesmo e-mail.
7. Use Histórico para carregar uma versão antiga como rascunho e Salvar para confirmar a restauração. A lixeira permite recuperar arquivos.

As conversões são cópias pontuais e não mantêm sincronização contínua. Antes de converter, o editor salva alterações da origem. Links de portais preservam o controle de acesso de cada arquivo. Coautoria simultânea usa versões otimistas: gravações conflitantes recebem HTTP 409; a tela mantém o rascunho e permite exportar JSON antes de reabrir o arquivo.

## Validação

```sh
python3 -m unittest discover -v
npm test
npm run check
```

Teste opcional de interface real, com Playwright Python e Chromium instalados:

```sh
python3 -m tests.browser_smoke
```

O script de navegador usa `/usr/bin/chromium` por padrão, configura servidor e banco temporários e apaga seus dados ao terminar. Não usa nem altera contas reais. Gere a mesma configuração instalando `playwright==1.62.0` em um virtualenv se necessário. O build inclui o motor de fórmulas e suas licenças. As bibliotecas Python geram e leem arquivos Office e ICS reais.

Validação realizada: **30 testes Python e 4 testes JavaScript aprovados**, verificações de sintaxe aprovadas e jornada no Chromium aprovada nos dez editores, incluindo persistência, conversões, fórmulas, teclado, tarefas, eventos, lixeira, restauração e layout de 390 px. Nenhum erro JavaScript ou CSP na jornada. O teste inclui apresentação e tabela criadas por conversão.

## Backup e restauração

Para uma cópia completa de contas, arquivos, permissões e versões, use a API de backup SQLite:

```sh
python3 scripts/backup.py .data/platform.sqlite .data/backups/nexo-001.sqlite
```

A origem pode estar em uso. O destino deve ser novo; o comando nunca substitui uma cópia existente. Ele verifica integridade antes e depois. Guarde backups em armazenamento privado com política de retenção.

Para ensaiar restauração, copie para outro banco e inicie uma instância separada:

```sh
python3 scripts/backup.py .data/backups/nexo-001.sqlite .data/restaurado.sqlite
DATABASE_PATH=.data/restaurado.sqlite PORT=8001 python3 -m server.app
```

Confira contas e arquivos antes de trocar o caminho da instância principal. Preserve o banco anterior para permitir retorno. O teste `tests/test_backup.py` verifica restauração de conta e conteúdo. As sessões também fazem parte da cópia; antes de uma recuperação de produção, revogue-as administrativamente.

**Exportar meu espaço** baixa um JSON dos arquivos próprios; a importação cria novas cópias privadas. Não é backup integral: não inclui contas, permissões ou histórico, não mantém IDs e não remapeia os links dos portais. Importações com falha de rede podem terminar parcialmente; a interface informa a quantidade já criada.

## Arquitetura e operação

- `server/store.py`: contas, senhas scrypt com salt e sessões cujo token é armazenado como hash.
- `server/workspace.py`: autorização por proprietário/compartilhamento, transações, versões e lixeira.
- `server/schema.py`: contratos de conteúdo e limites de cada editor.
- `server/app.py`: HTTP/JSON, cookies HttpOnly/SameSite, proteção de origem, rate limit persistido no banco e arquivos estáticos.
- `web/`: interface responsiva sem dependências; fórmulas analisadas sem `eval`, execução de JavaScript ou macros.
- `tests/`: testes isolados de banco, API, concorrência, backup, fórmulas e navegador.

A interface não envia conteúdo para ferramentas de IA ou serviços Office. No modo Vercel, o backend persiste os dados no PostgreSQL configurado. Requisições `POST /api/items` criam arquivos; `POST /api/items/{id}` altera usando a versão atual; `GET /api/items/{id}/history` retorna versões autorizadas; `POST /api/items/{id}/share` administra permissões. Listagem e histórico HTTP usam páginas de até quatro arquivos/versões, ajustadas ao limite de bytes (`items`, `next_offset`). Cada edição e sua versão são gravadas na mesma transação. Limites: 2 MB por conteúdo; planilhas com até 20 abas e 50 mil células preenchidas; tabelas com 200 linhas × 26 colunas; 100 slides. Falhas de salvamento mantêm o rascunho. Há recuperação de rascunhos locais no mesmo navegador e conta, sujeita à disponibilidade do armazenamento do navegador.

O servidor da biblioteca padrão é para desenvolvimento. A Vercel fornece HTTPS e o runtime de produção. Ainda faltam recuperação de conta, auditoria administrativa, observabilidade, backups ensaiados e testes de carga. A preparação do schema foi validada no build remoto Vercel. Testes de carga e restauração do banco gerenciado ainda não foram realizados.

A verificação automatizada está em `.github/workflows/verify.yml`: build, testes de domínio/API e quatro jornadas reais no Chromium. O ZIP inclui essa configuração.

Em Planilhas, selecione um intervalo com cabeçalhos e clique em **Tabela dinâmica** para configurar agrupamentos, cálculo e filtro. Os resumos seguem os valores da fonte; no XLSX são exportados como tabelas comuns. O JSON preserva a configuração dinâmica.
