# Ativar Google Workspace no DRAP office

A integração implementa Gmail (buscar, ler, enviar, responder, marcar como lido e mover para a lixeira), Google Agenda (listar/criar eventos) e criação de links Meet. Cada usuário conecta sua própria conta. Não sincroniza Drive, anexos de e-mail ou convites de participantes.

## Configuração do proprietário

1. No [Google Cloud Console](https://console.cloud.google.com/), selecione/crie o projeto da organização e habilite **Gmail API** e **Google Calendar API**.
2. Em **Google Auth Platform**, configure Branding, Audience e Data Access. Para uma organização Workspace, use aplicativo interno quando disponível. Para testes externos, adicione os usuários de teste. A publicação externa com escopos Gmail pode exigir verificação do Google.
3. Crie um cliente OAuth do tipo **Aplicativo da Web**, com redirecionamento autorizado exatamente:
   `https://new-balance-pi.vercel.app/google-callback.html`
4. Nas [variáveis do projeto Vercel](https://vercel.com/psaprincesa-netizens-projects/new-balance/settings/environment-variables), configure no ambiente **Production**:
   - `GOOGLE_CLIENT_ID`: ID do cliente Google.
   - `GOOGLE_CLIENT_SECRET`: segredo do cliente, como variável sensível.
   - `GOOGLE_TOKEN_ENCRYPTION_KEY`: chave Fernet, como variável sensível. Gere localmente com `.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Mantenha a mesma chave entre deploys; trocá-la exige reconectar as contas.
   - `GOOGLE_REDIRECT_URI`: URL acima (opcional enquanto esse for o domínio de produção).
5. Reimplante o projeto para carregar as variáveis. Abra **Google Workspace → Conectar conta Google**, escolha a conta e autorize Gmail e Agenda.

Não envie senhas, client secrets, chaves Fernet ou tokens pelo chat. Eles são configurados diretamente na Vercel.

## Autorização e armazenamento

OAuth com PKCE S256, estado aleatório válido por dez minutos, vinculado à sessão DRAP e consumido uma única vez. Refresh/access tokens são criptografados com Fernet no banco; o navegador recebe apenas estado da conexão e e-mail. O código de autorização é removido da URL antes da troca no servidor. Revogação remove a conexão local e solicita revogação ao Google.

Escopos: `openid email`, `gmail.modify`, `gmail.send`, `calendar.events`. As ações de envio e criação de evento partem de botões explícitos do usuário. Nenhum convite de calendário é enviado automaticamente.

## Verificação

Os testes locais usam respostas simuladas do provedor para verificar PKCE, isolamento entre usuários, replay/expiração, escopos, criptografia, renovação, envio e criação de Meet. Uma conexão real depende das credenciais acima e do consentimento do titular; não foi validada com uma conta Google real nesta entrega.
