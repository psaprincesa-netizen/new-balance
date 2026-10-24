# Auditoria de implantação na Vercel

Escopo: configuração de build, função Python, persistência, acesso, limites serverless e distribuição de código. A CLI Vercel foi autenticada e vinculada ao projeto existente `new-balance`; os builds remotos são executados com as variáveis protegidas da integração Neon.

## Estado da implantação

O build remoto validou a conexão Neon com certificado e hostname verificados e aplicou o schema dedicado `nexo`. A falha inicial de cadeia de confiança TLS foi corrigida com `certifi`. O empacotamento agora recria os arquivos de exclusão que a Vercel omite do upload.

A implantação utiliza os arquivos locais pela CLI. O checkout ainda não foi enviado ao Git remoto; deployments automáticos por Git exigem essa etapa. A publicação não equivale a auditoria completa de segurança ou teste de carga.

## Achados ainda abertos

### P1 · Isolamento de Preview/Production não confirmado

A integração Neon fornece variáveis nos dois ambientes. Não foi confirmado se apontam para bancos ou branches distintos. Separe-os antes de executar testes em Preview para evitar alterações no banco de produção.

### P1 · Cadastro público sem recuperação/verificação de acesso e cotas

Local: `server/store.py` (`register`), `server/workspace.py` (`create`, `update`) e tela de contas em `web/app.js`.

A autenticação funciona e tem limitação de tentativas no banco, mas não há recuperação de senha, confirmação de e-mail, convite restrito, limite de contas/arquivos ou retenção automática de versões. No lançamento público, pessoas podem perder acesso sem recuperação; criação abusiva de contas e histórico pode aumentar custo de banco e funções. Rate limit por conta/IP reduz tentativas, mas não é quota de armazenamento nem defesa completa contra abuso distribuído.

Ação: implementar recuperação com tokens de uso único, política de cadastro/convites, cotas e alertas de custo.

### P2 · Coleções grandes ainda são agregadas no navegador

Local: `web/app.js` (`allPages`, `refresh`, `analytics`).

A API agora limita cada página a quatro conteúdos, evitando respostas gigantes. Porém o cliente busca todas as páginas para busca e indicadores. Uma conta com muitos documentos pode consumir memória e fazer muitas requisições, mesmo sem exceder o limite individual da função.

Ação: busca no servidor, listagem de metadados, indicadores agregados e paginação incremental da interface, acompanhados de teste de carga.

### P2 · Sem idempotência para criação em falhas de rede

Local: `server/workspace.py` (`create`) e `web/app.js` (criação, importação e conversão).

A criação usa um novo ID a cada pedido. Se a gravação terminar e a resposta se perder, uma repetição pode criar uma cópia adicional. Importações têm múltiplos pedidos e podem terminar parcialmente. Controle de versão protege edições, mas não deduplica criações.

Ação: introduzir chaves de idempotência por operação e lote, armazenadas no banco; testar timeout depois do commit e retomada de importações.

### P2 · Capacidade, proteção e recuperação do provedor não ensaiadas

Local: `server/database.py` (`connect`) e configuração externa de Vercel/PostgreSQL.

Cada operação abre e fecha uma conexão; endpoints com pooler e região próxima são necessários para escala. Queries têm timeout de 15 s e a função tem 30 s, mas algumas requisições fazem múltiplas operações. Latência/carga real podem superar esse orçamento. Sem teste de carga, backups externos ensaiados e alertas, a capacidade permanece desconhecida. O teste SQLite não valida PITR/restauração do PostgreSQL gerenciado.

Ação: configurar pooler, região, limites de conexão, observabilidade e orçamento; testar carga e recuperação no provedor escolhido. Confirmar também como o proxy do projeto trata `x-forwarded-for`: o limite por e-mail é independente desse cabeçalho, mas a proteção por IP depende da cadeia confiável do proxy.

### P2 · O download publica o código-fonte por intenção do produto

Local: `scripts/package_release.py`, `scripts/build.mjs` e `/downloads/nexo.zip`.

O usuário pediu download; o build disponibiliza um ZIP público de código, não um instalador. O pacote foi testado para excluir banco, `.env`, arquivos Git, dependências e caches. Ainda assim, qualquer pessoa com a URL poderá obter a implementação após o deploy. Essa distribuição precisa combinar com a política de propriedade intelectual do responsável.

Ação: caso o código deva ser privado, remover a cópia de `public/downloads` e entregar o ZIP em canal privado. Nunca colocar segredos em código/fixtures/docs, pois os diretórios permitidos são empacotados.

## Riscos corrigidos nesta entrega

| Risco identificado | Correção | Evidência |
| --- | --- | --- |
| SQLite local em funções efêmeras | PostgreSQL externo obrigatório na Vercel; sem fallback | Teste retorna 503 sem configuração; teste PostgreSQL real |
| Colisão de handle_request com runtime Vercel | Dispatch da aplicação renomeado | Regressão HTTP e saúde 200 no domínio real |
| Handler criado só por atribuição não reconhecido | Classe `handler` explícita no nível superior | Builder oficial identificou entrypoint e gerou Lambda |
| Ausência de build e output | `npm run build`, diretório `public`, função e rewrites configurados | Build estático e builder Python locais |
| Timestamps maiores que INTEGER PostgreSQL | DDL usa BIGINT no adaptador | Teste real de criação, versões e reabertura |
| Controle de tentativas em memória por instância | Contadores transacionais no PostgreSQL/SQLite | Teste entre duas instâncias independentes |
| Escritas concorrentes em funções diferentes | Advisory transaction lock por arquivo e versão otimista | Duas gravações reais: uma confirma e outra recebe conflito |
| TLS insuficiente na conexão | `verify-full`, raízes confiáveis do certifi e timeout; sem downgrade | Banco de teste TLS com certificado explicitamente confiado |
| DDL a cada cold start | Migração explícita; runtime sem DDL | Factory usa `initialize=False` |
| Listagens/histórico sem limite de resposta | Paginação em blocos de quatro conteúdos | Testes de duas páginas e navegador com mais de quatro arquivos |
| Cookies sem Secure no runtime serverless | Secure automático em Vercel, mantendo HttpOnly/SameSite | Teste HTTP do cookie |
| Rota interna do rewrite diferente da URL original | Transporte de `route` e normalização no handler | Teste de cadastro/login/listagem pela rota reescrita |
| Vazamento de diagnóstico de banco | Erro 503 sem DSN e sem mensagens do driver | Testes de configuração e revisão do tratamento de erros |
| ZIP incluir dados e credenciais locais | Allowlist de código e metadados + exclusões | Teste abre ZIP e verifica conteúdo; download real no Chromium |

## Verificações realizadas

- Builder oficial `@vercel/python@28.0.1`: Lambda `python3.12`, handler `vc__handler__python.vc_handler`, 335 arquivos no bundle avaliado, incluindo `api/`, `server/` e `web/`, sem `.data`, `.env` ou `.git`.
- Build frontend e verificações de sintaxe JavaScript.
- 30 testes Python e 4 testes JavaScript automatizados.
- PostgreSQL 17 em contêiner descartável com TLS verificado: persistência entre instâncias, autenticação, unicidade, compartilhamento/revogação, concorrência, histórico, lixeira, rate limit distribuído e logout.
- Jornada dos dez editores no Chromium usando PostgreSQL: salvamento, reabertura, conversões, fórmulas, teclado, tarefas, agenda, histórico, lixeira, indicadores e layout móvel.
- Download de ZIP pela interface verificado no navegador.

Não executados: teste de carga, auditoria completa de segurança, recuperação de conta e restauração/PITR do banco gerenciado. Os testes automatizados acima descrevem a execução local. A preparação do schema e a verificação TLS também passaram no build remoto Vercel.
