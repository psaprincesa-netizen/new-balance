# Gemini no DRAP office

Menu **Gemini**: gerar texto, resumir ou analisar um arquivo salvo. O usuário escolhe
um arquivo ao qual tem acesso e confirma o envio do pedido e do conteúdo textual
para Google Gemini, via Vercel AI Gateway. Não há envio automático ao abrir arquivos.
O resultado aparece como texto revisável e pode virar um novo documento privado.
O arquivo original não é alterado. A IA não recebe ferramentas, não executa código,
não navega na web e não envia e-mails.

## Configuração

A integração Python usa a API HTTP Chat Completions do AI Gateway. Modelo padrão
`google/gemini-3.8-flash`, confirmado no catálogo público durante a implementação.
Pode ser alterado por `AI_GATEWAY_MODEL`, exclusivamente para modelos
`google/gemini-*` válidos do catálogo. Em Vercel Functions, usa o token OIDC do cabeçalho
`x-vercel-oidc-token` injetado pela plataforma a cada requisição; o fallback
`VERCEL_OIDC_TOKEN` é aceito em ambientes configurados; localmente ou em outros provedores, configure `AI_GATEWAY_API_KEY`
como segredo do ambiente. Nunca coloque chaves em código, no navegador ou no chat.

A autenticação é necessária, mas não garante créditos ou acesso ao modelo. Erros de
autenticação, ativação/verificação da conta, créditos, limite de uso e timeout são
mostrados sem divulgar respostas internas ou credenciais do provedor.

## Limites e dados

- 4.000 caracteres de instrução; 24.000 caracteres de contexto; 2.048 tokens de saída;
  até 18 segundos de espera pelo provedor. Não há repetição automática de pedidos.
- Planilhas: até 1.000 células por aba, com valor e fórmula, limitadas também pelo
  contexto total; toda análise de planilha nativa é identificada como amostra.
- Formulários enviam perguntas; não enviam respostas individuais nem gabarito.
  Para analisar respostas, o proprietário deve convertê-las para tabela e selecioná-la.
- Imagens e anexos não são enviados; documentos usam o texto da aba principal.
  Slides incluem título, corpo e notas. Não há análise multimodal nesta entrega.
- 5 pedidos por minuto por conta; cota diária UTC de 20 por conta e 200 por projeto.
  Variáveis: `AI_DAILY_USER_LIMIT`, `AI_DAILY_PROJECT_LIMIT` (1–10.000).
  São limites de tentativas; erros do provedor também consomem cota. As duas cotas
  são reservadas na mesma transação. Isso não substitui orçamento monetário no Gateway.
- Uma nova tabela `ai_daily` guarda somente identificador, dia e quantidade; retenção
  de sete dias. A migração é aditiva e ocorre no build remoto.
- O servidor não registra prompts, contexto, respostas ou tokens em logs. O tratamento
  pelo Google/Vercel segue as condições configuradas nas respectivas contas.

Testes com provedor simulado cobrem conteúdo, consentimento, acesso, erros e cotas
concorrentes; Chromium verifica pedido autenticado, revisão e criação de documento.
O teste real do Gemini deve ser registrado separadamente após a publicação.

## Resultado real em produção

No deployment `dpl_ARiXSZLz7agnqrCCnHZofQuYuKN5`, OIDC está configurado,
mas a geração recebeu HTTP 403 `customer_verification_required`. É necessária
a ativação/verificação da conta com forma de pagamento válida no painel do
AI Gateway pelo titular. Ainda não há geração real aprovada.
