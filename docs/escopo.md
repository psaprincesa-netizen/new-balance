# Escopo e rastreabilidade

## Decisão de produto

O usuário esclareceu que deseja uma única plataforma reunindo recursos de planilhas, documentos, apresentações e demais ferramentas de produtividade, conforme `Texto colado.txt`. Isso substitui a dúvida anterior sobre o produto principal. Nome confirmado pelo usuário: **DRAP office**, sem copiar marcas, código ou credenciais das ferramentas citadas.

Os documentos anteriores (`roteiro-de-implementacao.md`, `plano-de-plataforma (2).md`, `backlog-plataforma (1).csv`, `roteiro-para-criar-plataforma (3).md`) fornecem requisitos de qualidade. As referências estáticas a OAuth não comprovam comportamento real e não foram usadas como especificação de uma integração Microsoft.

## Resultado implementado

Jornada: criar um arquivo, editar, salvar, reabrir, transformar em outro tipo, compartilhar com uma conta e recuperar versões. Há dez módulos iniciais, biblioteca única e indicadores locais. Veja `recursos.md` para a cobertura e o README para execução.

| Requisito | Evidência atual | Pendente |
| --- | --- | --- |
| P001 Jornada | Direção do produto confirmada pelo usuário; jornada implementada | Entrevistas e testes com público real |
| P002 Continuidade | SQLite, versões, restauração, lixeira, reabertura e teste de concorrência real | Sincronização offline completa; rascunhos locais recuperáveis foram implementados |
| P003 Acesso | Cadastro, login/logout, expiração, isolamento de conta/arquivo, compartilhamento e revogação testados | Recuperação de senha, MFA, auditoria |
| P004 Integrações | Quatro conversões internas sem envio externo | OAuth, serviços externos, retry e sincronização |
| P005 Navegação | Interface responsiva e jornada no Chromium; teclado em apresentações | Auditoria completa WCAG, testes com usuários |
| P006 Estrutura | API, domínio, contratos e persistência separados; testes automatizados | Monitoramento contínuo e processo operacional de releases |
| P007 Compatibilidade | JSON próprio, texto Markdown, CSV, DOCX, XLSX, PPTX e ICS com limites documentados | Fidelidade integral de layout Office, PDF nativo; sem execução AppX/App-V |
| P008 Diferencial | Integração de editores via biblioteca e conversões | Comparação medida com alternativas reais |
| P009 Qualidade | 35 testes Python, 5 JS e jornada de navegador aprovados | Meta de produto “100%” precisa de denominador e medição com usuários |
| P010 Recuperação | Backup SQLite, verificação de integridade e restauração testada | Monitoramento e ensaio de rollback em produção |

## Limites da evidência

Os testes foram executados nesta máquina, com dados sintéticos. Eles não comprovam equivalência com Microsoft 365, adoção de mercado, cumprimento de normas de segurança ou funcionamento em um ambiente publicado. A suíte ainda não cobre integralmente o inventário solicitado. A plataforma foi publicada na Vercel com persistência no Neon. Correio, reuniões e IA ainda não têm provedores conectados.
