# Publicar o DRAP office na Vercel

O repositório contém frontend, backend Python serverless e configuração de PostgreSQL persistente. O projeto `new-balance` está vinculado à conta Vercel autorizada. O Neon existente fornece a variável protegida `DATABASE_URL`. O build remoto já validou a conexão TLS e inicializou o schema dedicado `nexo`.

## Antes do deploy

1. Use a raiz do repositório: preset **Other**, build `npm run build`, output `public`, Node 24.x. A função é `api/index.py`.
2. Vincule o projeto existente com a CLI autenticada (`vercel link`). É possível publicar diretamente os arquivos locais; integração Git exige que o código também seja enviado ao repositório remoto.
3. Configure `DATABASE_URL` como variável protegida. O driver força `sslmode=verify-full` e utiliza o pacote `certifi` para validar certificado e hostname, inclusive quando a URL do provedor usa `sslmode=require`. Certificados privados exigem raiz confiável fornecida pelo operador.
4. Separe bancos/credenciais de **Preview** e **Production** antes de usar Preview para testes. A integração existente disponibiliza bindings nos dois ambientes; o isolamento dos bancos não foi confirmado.
5. Publique com `vercel deploy --prod` após validar as alterações. Na Vercel, `npm run build` instala as dependências Python da migração e executa `python3 -m scripts.migrate` com o segredo disponível apenas no ambiente remoto. Se a migração falhar, o build falha.

A migração é aditiva, usa o schema `nexo` e não cria contas de exemplo. As funções não executam DDL em cold starts. Para execução manual segura, instale `requirements.txt`, configure `DATABASE_URL` no ambiente do processo e execute `python3 -m scripts.migrate`. Mantenha migrações futuras compatíveis com a versão em operação.

## O que é implantado

- `scripts/build.mjs`: aplica o schema durante builds Vercel, verifica sintaxe, copia os assets para `public/` e gera o download de código.
- `public/index.html`, JS e CSS: frontend estático servido pela CDN Vercel.
- `api/index.py`: classe `handler` exportada explicitamente, reconhecida pelo builder oficial.
- `server/`: backend com autenticação, autorização, arquivos, histórico, compartilhamento e paginação.
- `vercel.json`: rewrites para API, inclusão dos arquivos Python/web, limite de 30 s e cabeçalhos de segurança.
- `requirements.txt`: psycopg e certifi para PostgreSQL/TLS, bibliotecas para DOCX/XLSX/PPTX/ICS.

O rewrite transporta o caminho original no parâmetro `route`, funcionando também quando o runtime recebe `/api/index` como caminho interno. O frontend usa a mesma origem; não há domínio de API separado ou configuração CORS aberta.

Não existe fallback de banco local na Vercel. Ausência de configuração ou falha de banco resulta em HTTP 503, sem expor a URL de conexão. A rota de saúde consulta o schema real. Cookies recebem `Secure` automaticamente quando `VERCEL` está presente; continue usando HTTPS.

## Verificação após publicação

1. Carregar página, JS/CSS e conferir ausência de 404 e erros CSP.
2. Consultar `/api/health`: esperar 200 e `status: ok`; 503 indica conexão/schema a corrigir.
3. Cadastrar conta de teste, entrar, criar documento, salvar e reabrir após novo acesso/cold start.
4. Compartilhar com uma segunda conta e testar leitura/edição/revogação; tentar acessar uma conta não autorizada.
5. Abrir duas sessões e salvar a mesma versão: uma grava e outra recebe 409 sem perder seu rascunho aberto.
6. Criar mais de quatro arquivos e verificar paginação; testar histórico com mais de quatro versões.
7. Executar conversões, fórmulas e download do ZIP, inclusive no celular.
8. Verificar cookie `Secure`, `HttpOnly`, `SameSite=Strict`, logs sem credenciais e conectividade TLS do banco gerenciado.

O build remoto confirmou o acesso ao Neon e a preparação do schema com TLS verificado. A jornada completa dos dez editores foi testada localmente com PostgreSQL; as verificações remotas devem ser registradas separadamente.

## Download

A interface oferece **Baixar plataforma**, servindo `/downloads/drap-office.zip`. O arquivo contém código-fonte e instruções para executar ou implantar, **não é um instalador de desktop**. O ZIP não inclui contas, senhas, banco, `.env`, `node_modules` ou arquivos Git. Por intenção do produto, quem tiver acesso à URL poderá baixar esse código. Se o código precisar permanecer privado, remova essa publicação antes do deploy e distribua o ZIP por um canal privado.

Para gerar um pacote local:

```sh
npm run download
```

O resultado é `dist/drap-office.zip` acompanhado de SHA-256. Para desenvolvimento sem PostgreSQL, use `python3 -m server.app`; sem `DATABASE_URL` e sem `VERCEL`, o banco continua sendo SQLite.

## Backup e operação

Na Vercel, use backups/PITR do provedor PostgreSQL ou `pg_dump` administrado de forma segura. `scripts/backup.py` é somente para o banco SQLite local. Ensaiar restauração do banco gerenciado e revogar sessões após recuperação faz parte da preparação de produção.

Configure alertas para erros, falhas de login, conexões e custo. A listagem/histórico paginam quatro conteúdos por resposta para respeitar limites de resposta serverless. A interface ainda carrega todas as páginas em memória: coleções muito grandes exigirão busca e indicadores no servidor. Não há paginação infinita de UI nem teste de carga.

O [relatório de auditoria](auditoria-vercel.md) descreve riscos remanescentes, incluindo recuperação de conta, retenção, verificação de e-mail e custos de cadastro público.
