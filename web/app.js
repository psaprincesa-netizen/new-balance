import {responseTable,recordsWorkbook,answerError,localDateTime,safeCsv,documentSlides,scoreResponse,MULTI_SEPARATOR} from './workflows.js';
import {mountSlides,slideMarkup,printSlides,raster} from './slides.js';
import {mountPivots} from './pivot-ui.js';
import {chartSvg,chartData,CHART_TYPES} from './chart.js';
import {ensureTaskIds,findCycle,schedule,taskSpan,isoDay} from './project.js';
import { cellValue, parseCSV, toCSV } from "./formula.js";
const app = document.querySelector("#app"),
  modal = document.querySelector("#modal");
const TYPES = {
  document: {
    name: "Documentos",
    single: "Documento",
    icon: "D",
    color: "#e5edfa",
    ink: "#416da7",
    desc: "Escreva e organize ideias",
  },
  sheet: {
    name: "Planilhas",
    single: "Planilha",
    icon: "P",
    color: "#e1efdf",
    ink: "#477b3a",
    desc: "Calcule e visualize dados",
  },
  slides: {
    name: "Apresentações",
    single: "Apresentação",
    icon: "A",
    color: "#f9e9dc",
    ink: "#ae7341",
    desc: "Dê forma às suas histórias",
  },
  note: {
    name: "Anotações",
    single: "Anotação",
    icon: "N",
    color: "#eee5f5",
    ink: "#86619c",
    desc: "Guarde o que importa",
  },
  board: {
    name: "Projetos",
    single: "Projeto",
    icon: "✓",
    color: "#e5ecfb",
    ink: "#5c76ad",
    desc: "Da ideia à entrega",
  },
  calendar: {
    name: "Agenda",
    single: "Agenda",
    icon: "24",
    color: "#fae7e9",
    ink: "#b26c77",
    desc: "Organize seu tempo",
  },
  form: {
    name: "Formulários",
    single: "Formulário",
    icon: "F",
    color: "#e2efee",
    ink: "#468982",
    desc: "Pergunte, aprenda, decida",
  },
  table: {
    name: "Banco de dados",
    single: "Tabela",
    icon: "B",
    color: "#e9e8f4",
    ink: "#77739f",
    desc: "Informações estruturadas",
  },
  diagram: {
    name: "Diagramas",
    single: "Diagrama",
    icon: "◇",
    color: "#faefd8",
    ink: "#a5833b",
    desc: "Conecte etapas e processos",
  },
  portal: {
    name: "Portais",
    single: "Portal",
    icon: "⌂",
    color: "#e6eedf",
    ink: "#6f854b",
    desc: "Um ponto de encontro",
  },
};
let user = null,
  items = [],
  view = "home",
  current = null,
  dirty = false,
  selectedSlide = 0,
  query = "",
  busy = false;
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const icon = (k) =>
  `<span class="icon" data-color="${k}">${esc(TYPES[k]?.icon || "?")}</span>`;
// Dynamic styles are applied through the DOM below to respect the CSP.
function colors() {
  document.querySelectorAll("[data-color]").forEach((n) => {
    const t = TYPES[n.dataset.color];
    if (t) {
      n.style.setProperty("--tint", t.color);
      n.style.setProperty("--ink", t.ink);
    }
  });
  document
    .querySelectorAll("[data-height]")
    .forEach((n) => (n.style.height = n.dataset.height + "px"));
}
function notify(text) {
  document.querySelector("#notice").textContent = text;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(
    () => (document.querySelector("#notice").textContent = ""),
    6500,
  );
}
const OFFLINE_MESSAGE = "Sem conexão com a internet. Tente novamente quando a conexão voltar.";
async function api(path, data) {
  let r;
  try {
    r = await fetch(path, {
      method: data === undefined ? "GET" : "POST",
      headers: data === undefined ? {} : { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
  } catch {
    // fetch only rejects on network failure: report it plainly instead of "Failed to fetch".
    const e = Error(OFFLINE_MESSAGE);
    e.offline = true;
    throw e;
  }
  let result;
  try { result=await r.json(); }
  catch { throw Error('O servidor não respondeu corretamente (HTTP '+r.status+'). Tente novamente.'); }
  if (!r.ok) {
    const e = Error(result.error || "Não foi possível concluir.");
    e.status = r.status;
    e.data = result;
    throw e;
  }
  return result;
}
function download(name, data, type = "application/json") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([data], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function date(n) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(n));
}
function bind(id, fn, event = "click") {
  document.getElementById(id)?.addEventListener(event, fn);
}
function setDirty() {
  dirty = true;
  clearTimeout(stashDraft.timer);
  stashDraft.timer=setTimeout(stashDraft,300);
  const s = document.querySelector("#save-state");
  if (s) s.textContent = "Alterações não salvas";
}
function defaults(kind) {
  switch (kind) {
    case "document":
    case "note":
      return { text: "" };
    case "sheet":
      return { cells: Array.from({ length: 12 }, () => Array(6).fill("")) };
    case "slides":
      return {
        slides: [
          {
            title: "Uma nova ideia",
            body: "Sua história começa aqui.",
            notes: "",
          },
        ],
      };
    case "board":
      return { tasks: [] };
    case "calendar":
      return { events: [] };
    case "form":
      return { questions: ["Como podemos melhorar?"], responses: [] };
    case "table":
      return { columns: ["Nome", "Descrição", "Status"], rows: [] };
    case "diagram":
      return { nodes: ["Início", "Planejamento", "Entrega"] };
    case "portal":
      return { text: "", links: [] };
  }
}
function auth(register = false) {
  app.innerHTML = `<main class="auth"><section class="auth-aside"><div class="brand"><span class="brand-name">DRAP <span>office</span></span></div><h1>Um espaço.<br>Infinitas<br>possibilidades.</h1><p>Documentos, dados e ideias conectados.<br>Seu trabalho ganha um novo lugar.</p><small>PLATAFORMA DE PRODUTIVIDADE • VERSÃO INICIAL</small></section><section class="auth-panel"><form id="auth"><p class="eyebrow">SEU ESPAÇO DE TRABALHO</p><h2>${register ? "Crie sua conta" : "Bem-vindo de volta"}</h2><p class="muted">${register ? "Comece a organizar suas ideias." : "Entre para continuar de onde parou."}</p>${register ? '<label class="field">Nome<input name="name" autocomplete="name" maxlength="100" required></label>' : ""}<label class="field">E-mail<input name="email" type="email" autocomplete="email" maxlength="254" required></label><label class="field">Senha<input name="password" type="password" autocomplete="${register ? "new-password" : "current-password"}" minlength="${register ? 12 : 1}" maxlength="128" required></label>${register ? "<small>Use pelo menos 12 caracteres. Não reutilize senhas.</small>" + recoveryFields() : ""}<p id="auth-error" class="error" role="alert"></p><button class="primary" type="submit">${register ? "Criar conta" : "Entrar no DRAP office"} →</button>${register ? "" : '<p class="field"><button id="forgot-password" type="button">Esqueci minha senha</button></p>'}<p class="field"><button id="toggle-auth" type="button">${register ? "Já tenho conta" : "Criar minha conta"}</button></p><small>Seus arquivos são privados até você compartilhá-los.</small></form></section></main>`;
  bind("toggle-auth", () => auth(!register));
  bind("forgot-password", () => recoveryScreen());
  if (register) loadRecoveryQuestions(app);
  bind(
    "auth",
    async (e) => {
      e.preventDefault();
      const button = e.target.querySelector("[type=submit]");
      button.disabled = true;
      const data = Object.fromEntries(new FormData(e.target));
      try {
        if (register) await api("/api/register", data);
        try {
          user = await api("/api/login", data);
        } catch (err) {
          if (!err.data?.mfa_required) throw err;
          // Password accepted: ask for the authenticator code in the same form.
          if (!e.target.querySelector('[name="code"]')) {
            e.target.querySelector('#auth-error').insertAdjacentHTML('beforebegin', '<label class="field">Código de verificação<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="20" required></label><small>Digite os 6 dígitos do app autenticador ou um código de backup.</small>');
            e.target.querySelector('[name="code"]').focus();
          }
          throw err;
        }
        await refresh();
        render();
        askRecoverySetup();
      } catch (err) {
        document.querySelector("#auth-error").textContent = err.message;
      } finally {
        button.disabled = false;
      }
    },
    "submit",
  );
}
// Secret question used to recover the account and choose a new password.
let recoveryQuestions = null;
function recoveryFields(intro = "") {
  return `<fieldset class="recovery-fields"><legend>Recuperação da conta</legend>${intro}<label class="field">Pergunta secreta<select name="question" aria-label="Pergunta secreta" required><option value="">Escolha uma pergunta…</option></select></label><label class="field">Resposta secreta<input name="answer" type="password" autocomplete="off" minlength="3" maxlength="100" required></label><small>Se esquecer a senha, você responde a esta pergunta para criar uma nova. Escolha uma resposta que só você saiba; maiúsculas e acentos não fazem diferença.</small></fieldset>`;
}
async function loadRecoveryQuestions(root, selected = "") {
  try {
    recoveryQuestions ??= (await api("/api/recovery/questions")).items;
    const select = root.querySelector('select[name="question"]');
    if (!select) return;
    for (const q of recoveryQuestions) select.add(new Option(q.text, q.id, false, q.id === selected));
  } catch (e) { notify(e.message); }
}
function recoveryScreen(email = "") {
  app.innerHTML = `<main class="auth"><section class="auth-aside"><div class="brand"><span class="brand-name">DRAP <span>office</span></span></div><h1>Recupere<br>seu acesso.</h1><p>Responda à sua pergunta secreta<br>e crie uma nova senha.</p></section><section class="auth-panel"><form id="recovery-email"><p class="eyebrow">RECUPERAR CONTA</p><h2>Esqueci minha senha</h2><p class="muted">Informe o e-mail da sua conta.</p><label class="field">E-mail<input name="email" type="email" autocomplete="email" maxlength="254" required value="${esc(email)}"></label><p id="recovery-error" class="error" role="alert"></p><button class="primary" type="submit">Continuar →</button><p class="field"><button id="back-login" type="button">Voltar para o login</button></p></form></section></main>`;
  bind("back-login", () => auth());
  bind("recovery-email", async (e) => {
    e.preventDefault();
    const button = e.target.querySelector("[type=submit]");
    button.disabled = true;
    const address = new FormData(e.target).get("email");
    try {
      const { text } = await api("/api/recovery/question", { email: address });
      recoveryAnswer(address, text);
    } catch (err) {
      document.querySelector("#recovery-error").textContent = err.status === 404
        ? "Não encontramos uma pergunta secreta para esse e-mail. Contas sem pergunta cadastrada não podem ser recuperadas."
        : err.message;
      button.disabled = false;
    }
  }, "submit");
}
function recoveryAnswer(email, question) {
  const form = document.querySelector(".auth-panel");
  form.innerHTML = `<form id="recovery-reset"><p class="eyebrow">RECUPERAR CONTA</p><h2>Pergunta secreta</h2><p class="muted">${esc(email)}</p><p><strong id="recovery-question">${esc(question)}</strong></p><label class="field">Resposta secreta<input name="answer" type="password" autocomplete="off" maxlength="100" required></label><label class="field">Nova senha<input name="password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><label class="field">Confirmar nova senha<input name="confirm" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><small>Use pelo menos 12 caracteres. Ao trocar a senha, todas as sessões abertas da conta são encerradas.</small><p id="recovery-error" class="error" role="alert"></p><button class="primary" type="submit">Criar nova senha →</button><p class="field"><button id="back-login" type="button">Voltar para o login</button></p></form>`;
  bind("back-login", () => auth());
  bind("recovery-reset", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    const error = document.querySelector("#recovery-error");
    if (data.password !== data.confirm) { error.textContent = "As senhas não conferem."; return; }
    const button = e.target.querySelector("[type=submit]");
    button.disabled = true;
    try {
      await api("/api/recovery/reset", { email, answer: data.answer, password: data.password });
      auth();
      document.querySelector('#auth input[name="email"]').value = email;
      notify("Senha alterada. Entre com a nova senha.");
    } catch (err) {
      error.textContent = err.message;
      button.disabled = false;
    }
  }, "submit");
}
function recoveryDialog(required = false) {
  const intro = required ? "<p>Sua conta ainda não tem pergunta secreta. Sem ela, não será possível recuperar o acesso se você esquecer a senha.</p>" : "";
  showDialog(`<form id="recovery-setup"><h2>${user.recovery_question ? "Alterar pergunta secreta" : "Cadastrar pergunta secreta"}</h2>${recoveryFields(intro)}<label class="field">Senha atual<input name="password" type="password" autocomplete="current-password" maxlength="128" required></label><p id="recovery-setup-error" class="error" role="alert"></p><div class="row"><button type="button" id="recovery-later">${required ? "Agora não" : "Cancelar"}</button><button class="primary" type="submit">Salvar</button></div></form>`, () => {
    loadRecoveryQuestions(modal, user.recovery_question || "");
    bind("recovery-later", closeDialog);
    bind("recovery-setup", async (e) => {
      e.preventDefault();
      const button = e.target.querySelector("[type=submit]");
      button.disabled = true;
      try {
        user = await api("/api/account/recovery", Object.fromEntries(new FormData(e.target)));
        closeDialog();
        notify("Pergunta secreta salva.");
      } catch (err) {
        document.querySelector("#recovery-setup-error").textContent = err.message;
        button.disabled = false;
      }
    }, "submit");
  });
}
// Account security: two-step verification and recent activity.
async function securityDialog() {
  let events = [];
  try { events = (await api("/api/account/events")).items; } catch (e) { notify(e.message); }
  showDialog(`<h2>Segurança da conta</h2><section class="card"><h3>Verificação em duas etapas</h3><p id="mfa-status">${user.mfa_enabled ? "Ativa: ao entrar, além da senha, é pedido um código do app autenticador." : "Desativada. Ative para exigir um código do celular além da senha."}</p><button id="mfa-toggle" class="${user.mfa_enabled ? "danger" : "primary"}">${user.mfa_enabled ? "Desativar" : "Ativar verificação em duas etapas"}</button></section><section class="card"><h3>Pergunta secreta</h3><p>${user.recovery_question ? "Cadastrada." : "Não cadastrada: sem ela não é possível recuperar a senha."}</p><button id="security-recovery">${user.recovery_question ? "Alterar" : "Cadastrar"}</button></section><section class="card"><h3>Atividade recente</h3><ul class="activity" id="activity-list">${events.map(ev => `<li><strong>${esc(ev.label)}</strong>${ev.detail ? " · " + esc(ev.detail) : ""}<small> · ${date(ev.at)}${ev.ip ? " · IP " + esc(ev.ip) : ""}</small></li>`).join("") || "<li>Nenhuma atividade registrada.</li>"}</ul></section><div class="row"><button id="security-close">Fechar</button></div>`, () => {
    bind("security-close", closeDialog);
    bind("security-recovery", () => recoveryDialog(false));
    bind("mfa-toggle", () => (user.mfa_enabled ? mfaDisableDialog() : mfaSetupDialog()));
  });
}
function mfaSetupDialog() {
  showDialog(`<form id="mfa-password"><h2>Ativar verificação em duas etapas</h2><p>Você vai precisar de um app autenticador no celular, como Google Authenticator, Microsoft Authenticator ou Authy.</p><label class="field">Senha atual<input name="password" type="password" autocomplete="current-password" maxlength="128" required></label><p id="mfa-error" class="error" role="alert"></p><div class="row"><button type="button" id="mfa-cancel">Cancelar</button><button class="primary">Continuar</button></div></form>`, () => {
    bind("mfa-cancel", securityDialog);
    bind("mfa-password", async (e) => {
      e.preventDefault();
      try {
        const setup = await api("/api/account/mfa/setup", Object.fromEntries(new FormData(e.target)));
        let qr = "";
        try { qr = (await import("/qr.js")).qrSvg(setup.uri); } catch {}
        const key = setup.secret.match(/.{1,4}/g).join(" ");
        showDialog(`<form id="mfa-enable"><h2>Escaneie o QR code</h2><p>No app autenticador, adicione uma conta e escaneie o código abaixo.</p><div class="mfa-qr" role="img" aria-label="QR code para o app autenticador">${qr}</div><p>Se não conseguir escanear, digite esta chave no app: <code id="mfa-secret">${esc(key)}</code></p><p><a href="${esc(setup.uri)}">Abrir no app autenticador deste aparelho</a></p><label class="field">Código de 6 dígitos mostrado no app<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required></label><p id="mfa-error" class="error" role="alert"></p><div class="row"><button type="button" id="mfa-cancel">Cancelar</button><button class="primary">Ativar</button></div></form>`, () => {
          bind("mfa-cancel", securityDialog);
          bind("mfa-enable", async (ev) => {
            ev.preventDefault();
            try {
              const { backup_codes } = await api("/api/account/mfa/enable", Object.fromEntries(new FormData(ev.target)));
              user = { ...user, mfa_enabled: true };
              showDialog(`<h2>Verificação ativada</h2><p>Guarde estes códigos de backup em local seguro. Cada um funciona uma única vez, caso você perca o celular. Eles não serão mostrados de novo.</p><ul class="backup-codes" id="backup-codes">${backup_codes.map(c => `<li><code>${esc(c)}</code></li>`).join("")}</ul><div class="row"><button id="backup-download">Baixar códigos</button><button class="primary" id="backup-done">Já guardei</button></div>`, () => {
                bind("backup-download", () => download("drap-office-codigos-de-backup.txt", "Códigos de backup do DRAP office (" + user.email + ")\nCada código funciona uma vez.\n\n" + backup_codes.join("\n") + "\n", "text/plain"));
                bind("backup-done", securityDialog);
              });
            } catch (err) { document.querySelector("#mfa-error").textContent = err.message; }
          }, "submit");
        });
      } catch (err) { document.querySelector("#mfa-error").textContent = err.message; }
    }, "submit");
  });
}
function mfaDisableDialog() {
  showDialog(`<form id="mfa-disable"><h2>Desativar verificação em duas etapas</h2><p>Sua conta voltará a ser protegida apenas pela senha.</p><label class="field">Senha atual<input name="password" type="password" autocomplete="current-password" maxlength="128" required></label><label class="field">Código do app ou de backup<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="20" required></label><p id="mfa-error" class="error" role="alert"></p><div class="row"><button type="button" id="mfa-cancel">Cancelar</button><button class="danger">Desativar</button></div></form>`, () => {
    bind("mfa-cancel", securityDialog);
    bind("mfa-disable", async (e) => {
      e.preventDefault();
      try {
        await api("/api/account/mfa/disable", Object.fromEntries(new FormData(e.target)));
        user = { ...user, mfa_enabled: false };
        notify("Verificação em duas etapas desativada.");
        securityDialog();
      } catch (err) { document.querySelector("#mfa-error").textContent = err.message; }
    }, "submit");
  });
}
function askRecoverySetup() {
  // Older accounts were created before the secret question existed; ask once per session.
  if (!user || user.recovery_question) return;
  try { if (sessionStorage.getItem("drap:recovery-asked")) return; sessionStorage.setItem("drap:recovery-asked", "1"); } catch {}
  recoveryDialog(true);
}
async function allPages(path) {
  const result = [];
  let offset = 0;
  do {
    const page = await api(path + "?offset=" + offset);
    result.push(...page.items);
    offset = page.next_offset;
  } while (offset !== null);
  return result;
}
async function refresh() {
  items = await allPages("/api/items");
}
let spreadsheet = null,documentEditor=null;
function shell(body) {
  spreadsheet?.dispose(); spreadsheet=null;documentEditor?.dispose();documentEditor=null;
  app.innerHTML = `<div class="layout"><aside class="sidebar"><div class="brand"><span class="brand-name">DRAP <span>office</span></span><span class="badge">beta</span></div><div class="workspace">◉ &nbsp; Meu espaço de trabalho<br><small>&nbsp;&nbsp;&nbsp;&nbsp; ${esc(user.name)}</small></div><nav class="nav" aria-label="Navegação principal">${[
    ["home", "⌂", "Visão geral"],
    ["files", "▤", "Todos os arquivos"],
    ["shared", "♧", "Compartilhados"],
    ["analytics", "▥", "Indicadores"],
    ["automation", "⌘", "Conexões"],
    ["coverage", "⊞", "Recursos"],
    ["trash", "♲", "Lixeira"],
  ]
    .map(
      ([id, i, n]) =>
        `<button data-nav="${id}" class="${view === id ? "active" : ""}"><span>${i}</span>${n}</button>`,
    )
    .join(
      "",
    )}</nav><footer>FEITO PARA CONECTAR<br>Uma conta. Todas as suas ideias.<br><button id="backup">Exportar meu espaço</button><button id="import">Importar JSON</button><button id="import-office">Importar Office / Agenda</button><button id="recovery-settings">Pergunta secreta</button><button id="security-settings">Segurança da conta</button><a class="download-platform" href="/downloads/drap-office.zip" download="drap-office.zip">Baixar plataforma ↓</a></footer></aside><main class="main"><header class="topbar"><input class="search" id="search" type="search" placeholder="Buscar em todos os arquivos…" aria-label="Buscar arquivos" value="${esc(query)}"><div class="row"><span class="user-name muted">${esc(user.name)}</span><span class="avatar">${esc(user.name.slice(0, 2).toUpperCase())}</span><a class="download-top" href="/downloads/drap-office.zip" download="drap-office.zip" aria-label="Baixar plataforma" title="Baixar código da plataforma">↓</a><button id="logout" title="Sair da conta">Sair</button></div></header><div class="content">${body}</div></main></div>`;
  document
    .querySelectorAll("[data-nav]")
    .forEach((n) => (n.onclick = () => navigate(n.dataset.nav)));
  bind("import-office", importOffice);
  bind("recovery-settings", () => recoveryDialog(false));
  bind("security-settings", securityDialog);
  bind("logout", async () => {
    if (!(await leave())) return;
    await api("/api/logout", {});
    user = null;
    items = [];
    current = null;
    query = "";
    auth();
  });
  bind(
    "search",
    (e) => {
      query = e.target.value;
      if (current) {
        if (dirty) {
          notify("Salve ou exporte seu rascunho antes de buscar na biblioteca.");
          return;
        }
        current = null;
        view = "files";
        render();
        const search = document.querySelector("#search");
        search.focus();
        search.setSelectionRange(query.length, query.length);
        return;
      }
      const target = document.querySelector("#file-list");
      if (target) target.innerHTML = fileList(filtered());
      wireFiles();
    },
    "input",
  );
  bind("backup", () =>
    download(
      "drap-office-espaco.json",
      JSON.stringify(
        { format: "drap-office/1", items: items.filter((i) => i.owner === user.id) },
        null,
        2,
      ),
    ),
  );
  bind("import", importBackup);
  colors();
}
async function leave() {
  await spreadsheet?.flush();
  if (!dirty) return true;
  const discard = await askConfirm(
    "Descartar alterações?",
    "Você tem alterações não salvas. Cancele para salvar ou exportar um rascunho antes de sair.",
  );
  if (discard) { clearTimeout(stashDraft.timer); try { localStorage.removeItem(draftKey()); } catch {} }
  return discard;
}
async function navigate(next) {
  if (!(await leave())) return;
  dirty = false;
  current = null;
  view = next;
  query = "";
  await refresh();
  render();
}
function filtered() {
  return items.filter(
    (i) =>
      (view === "trash" ? i.deleted : !i.deleted) &&
      (view !== "shared" || i.owner !== user.id) &&
      `${i.title} ${TYPES[i.kind]?.name} ${JSON.stringify(i.content)}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
}
function fileList(list) {
  if (!list.length)
    return '<div class="empty">Seu próximo projeto começa aqui.<br><br>Crie um arquivo ou importe seu trabalho.</div>';
  return (
    `<div class="file header"><span>Nome</span><span class="kind">Ferramenta</span><span class="date">Última edição</span><span>Acesso</span></div>` +
    list
      .map(
        (i) =>
          `<div class="file"><button class="open" data-open="${i.id}">${icon(i.kind)}<span class="name">${esc(i.title)}</span></button><span class="kind muted">${esc(TYPES[i.kind]?.single)}</span><span class="date muted">${date(i.updated)}</span><span class="badge">${i.role === "owner" ? "Privado" : i.role === "edit" ? "Edição" : "Leitura"}</span></div>`,
      )
      .join("")
  );
}
function wireFiles() {
  document
    .querySelectorAll("[data-open]")
    .forEach((n) => (n.onclick = () => openItem(n.dataset.open)));
  colors();
}
function render() {
  if (current) return editor();
  if (view === "analytics") return analytics();
  if (view === "automation") return automation();
  if (view === "coverage") return coverage();
  const home = view === "home";
  shell(
    `<div class="row between"><div><p class="eyebrow">${home ? "TUDO O QUE VOCÊ PRECISA, JUNTO" : "ESPAÇO DE TRABALHO"}</p><h1>${home ? `Olá, ${esc(user.name.split(" ")[0])}. Vamos criar?` : { files: "Todos os arquivos", shared: "Compartilhados comigo", trash: "Lixeira" }[view]}</h1><p class="muted">${home ? "Ideias, dados e projetos. Um lugar para conectar tudo." : view === "trash" ? "Seus arquivos podem ser restaurados ao abrir." : "Seu trabalho organizado, sempre à mão."}</p></div><button id="new" class="primary">＋ Criar novo</button></div>${
      home
        ? `<section class="hero"><div><p class="eyebrow">MENOS ABAS. MAIS POSSIBILIDADES.</p><h2>Seu trabalho flui melhor<br>quando está conectado.</h2><p>Escreva um documento. Transforme em apresentação.<br>Conecte os dados. Tire suas ideias do papel.</p><button id="hero-new">Começar algo novo ↗</button></div><div class="hero-art" aria-hidden="true">▤ ◇<br>▥ ▱</div></section><div class="row between section-head"><h2>Suas ferramentas</h2><span class="muted">Um espaço, dez maneiras de criar</span></div><div class="tools">${Object.entries(
            TYPES,
          )
            .map(
              ([k, t]) =>
                `<button class="tool" data-create="${k}">${icon(k)}<strong>${t.name}</strong><small>${t.desc}</small></button>`,
            )
            .join("")}</div>`
        : ""
    }<div class="row between section-head"><h2>${home ? "Arquivos recentes" : "Biblioteca"}</h2><span class="muted">${filtered().length} arquivos</span></div><section class="files" id="file-list">${fileList(home ? filtered().slice(0, 8) : filtered())}</section>`,
  );
  bind("new", () => createDialog());
  bind("hero-new", () => createDialog());
  document
    .querySelectorAll("[data-create]")
    .forEach((n) => (n.onclick = () => createDialog(n.dataset.create)));
  wireFiles();
}
function showDialog(html, setup) {
  modal.innerHTML = html;
  modal.showModal();
  colors();
  setup?.();
}
function closeDialog() {
  modal.close();
  modal.innerHTML = "";
}
function askConfirm(title, text) {
  return new Promise((resolve) => {
    showDialog(
      `<h2>${esc(title)}</h2><p class="muted">${esc(text)}</p><div class="row"><button id="yes" class="danger">Confirmar</button><button id="no">Cancelar</button></div>`,
      () => {
        bind("yes", () => {
          closeDialog();
          resolve(true);
        });
        bind("no", () => {
          closeDialog();
          resolve(false);
        });
        modal.addEventListener("cancel", () => resolve(false), { once: true });
      },
    );
  });
}
function createDialog(kind = "document") {
  showDialog(
    `<h2>Um novo começo</h2><form id="create-form"><label class="field">Ferramenta<select name="kind">${Object.entries(
      TYPES,
    )
      .map(
        ([k, t]) =>
          `<option value="${k}" ${k === kind ? "selected" : ""}>${t.name}</option>`,
      )
      .join(
        "",
      )}</select></label><label class="field">Nome do arquivo<input name="title" placeholder="Minha próxima grande ideia" maxlength="200" required autofocus></label><p id="create-error" class="error" role="alert"></p><div class="row"><button class="primary">Criar arquivo</button><button id="cancel" type="button">Cancelar</button></div></form>`,
    () => {
      bind("cancel", closeDialog);
      bind(
        "create-form",
        async (e) => {
          e.preventDefault();
          const data = Object.fromEntries(new FormData(e.target));
          try {
            const item = await api("/api/items", {
              ...data,
              content: defaults(data.kind),
            });
            closeDialog();
            await refresh();
            await openItem(item.id);
          } catch (err) {
            document.querySelector("#create-error").textContent = err.message;
          }
        },
        "submit",
      );
    },
  );
}
async function openItem(id) {
  if (!(await leave())) return;
  try {
    current = await api("/api/items/" + id);
    dirty = false;
    if (current.role !== 'read') {
      let draft;
      try { draft=JSON.parse(localStorage.getItem(draftKey()) || 'null'); } catch {}
      if (draft && await askConfirm('Recuperar rascunho?', 'Há alterações não salvas deste arquivo neste navegador. Confirmar recupera o rascunho; Cancelar mantém a versão do servidor.')) {
        const remoteVersion=current.version;
        current.title=draft.title;current.content=draft.content;current.deleted=draft.deleted;
        current.version=draft.version;dirty=true;
        if (remoteVersion!==draft.version) notify('O servidor tem outra versão. Exporte o rascunho antes de resolver o conflito.');
      }
    }
    selectedSlide = 0;
    editor();
  } catch (e) {
    notify(e.message);
  }
}
async function save() {
  if (busy) return;
  busy = true;
  app.inert = true;
  try {
    await spreadsheet?.flush();
    const saved = await api("/api/items/" + current.id, {
      title: current.title,
      content: current.content,
      version: current.version,
      deleted: current.deleted,
    });
    // Saving must not remount Univer: that clears selection, the active ribbon
    // tab and undo history. Keep the content object held by the mounted editor.
    const keepSheet = spreadsheet && !saved.deleted && saved.role !== 'read';
    if (keepSheet) {
      const content = current.content;
      for (const key of Object.keys(content)) delete content[key];
      Object.assign(content, saved.content);
      current = {...saved, content};
    } else current = saved;
    dirty = false;
    clearTimeout(stashDraft.timer);
    try { localStorage.removeItem(draftKey()); } catch {}
    notify("Arquivo salvo. Seu trabalho está em dia.");
    await refresh();
    if (keepSheet) document.querySelector('#save-state').textContent = `Versão ${current.version} · ${date(current.updated)}`;
    else editor();
  } catch (e) {
    if (e.offline) {
      // Keep the edit in this browser so it survives a reload while offline.
      clearTimeout(stashDraft.timer);
      stashDraft();
      e.message = "Sem conexão: as alterações ficaram como rascunho neste navegador. Salve de novo quando a internet voltar.";
    }
    notify(e.message);
    const status = document.querySelector("#save-state");
    if (status) status.textContent = e.message;
  } finally {
    busy = false;
    app.inert = false;
  }
}
function markdown(text,images=[]) {
  const inline=s=>esc(s).replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\*(.*?)\*/g,'<em>$1</em>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const lines=String(text).split('\n'),out=[];
  for(let i=0;i<lines.length;i++) {
    const line=lines[i];
    const picture=/^!\[([^\]]*)\]\(drap-image:([a-zA-Z0-9_-]+)\)$/.exec(line.trim());
    if(picture){const im=images.find(im=>im.id===picture[2]);out.push(im?`<figure><img src="${esc(im.src)}" alt="${esc(im.alt||picture[1])}" style="width:${im.width||80}%;max-width:100%;height:auto;max-height:900px;object-fit:contain"></figure>`:'<p>Imagem indisponível: '+esc(picture[1])+'</p>');continue;}

    if(/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)){out.push('<hr class="page-break" data-label="Quebra de página">');continue;}
    if(line.startsWith('```')) {const block=[];while(++i<lines.length&&!lines[i].startsWith('```'))block.push(lines[i]);out.push('<pre><code>'+esc(block.join('\n'))+'</code></pre>');continue;}
    if(line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[i+1]||'')) {
      const cells=s=>s.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split(/(?<!\\)\|/).map(x=>x.trim().replaceAll('\\|','|'));
      const header=cells(line);i++;const rows=[];
      while(i+1<lines.length && lines[i+1].includes('|'))rows.push(cells(lines[++i]));
      out.push('<table><thead><tr>'+header.map(v=>'<th>'+inline(v)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+inline(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table>');continue;
    }
    const heading=/^(#{1,3})\s(.*)/.exec(line);
    if(heading){out.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`);continue;}
    const bullet=/^\s*([-*]|\d+\.)\s+(.*)/.exec(line);
    if(bullet) {const ordered=/\d/.test(bullet[1]),tag=ordered?'ol':'ul',entries=[bullet[2]];while(i+1<lines.length){const next=/^\s*([-*]|\d+\.)\s+(.*)/.exec(lines[i+1]);if(!next||/\d/.test(next[1])!==ordered)break;entries.push(next[2]);i++;}out.push(`<${tag}>`+entries.map(e=>'<li>'+inline(e).replace(/^\[([ xX])\]/,(_,v)=>v.trim()?'☑':'☐')+'</li>').join('')+`</${tag}>`);continue;}
    if(line.startsWith('> ')){out.push('<blockquote>'+inline(line.slice(2))+'</blockquote>');continue;}
    out.push('<p>'+(inline(line)||'&nbsp;')+'</p>');
  }
  return out.join('');
}
function editor() {
  const t = TYPES[current.kind],
    read = current.role === "read";
  shell(
    `<div class="editor-head"><button id="back">←</button>${icon(current.kind)}<input id="title" class="title-input" aria-label="Nome do arquivo" maxlength="200" value="${esc(current.title)}" ${read ? "disabled" : ""}><span class="badge">${t.single}</span><button id="save" class="primary" ${read ? "disabled" : ""}>Salvar</button></div><div class="toolbar"><span id="save-state" class="muted">${dirty ? "Alterações não salvas" : `Versão ${current.version} · ${date(current.updated)}`}</span><button id="export">Exportar JSON</button>${["document","note","sheet","table","slides","calendar"].includes(current.kind) ? '<button id="export-office">Baixar ' + ({document:"DOCX",note:"DOCX",sheet:"XLSX",table:"XLSX",slides:"PPTX",calendar:"ICS"}[current.kind]) + '</button>' : ""}<button id="print">Imprimir / PDF</button><button id="history">Histórico</button><button id="comments">Comentários</button>${current.role === "owner" ? '<button id="share">Compartilhar</button>' : ""}<button id="trash" class="danger" ${read ? "disabled" : ""}>${current.deleted ? "Restaurar" : "Mover para lixeira"}</button></div><div id="editor-body" class="editor"></div>`,
  );
  bind("back", () => navigate("files"));
  bind(
    "title",
    (e) => {
      current.title = e.target.value;
      setDirty();
    },
    "input",
  );
  bind("save", save);
  bind("export", async () => {
    await spreadsheet?.flush();
    download(
      current.title + ".json",
      JSON.stringify({ format: "drap-office/1", items: [current] }, null, 2),
    );
  });
  bind("export-office", exportOffice);
  bind("print", () => current.kind==="slides"?printSlides(current.content):printPages(current.kind==="document"||current.kind==="note"?current.content:{}));
  bind("history", historyDialog);
  bind("comments", commentsDialog);
  bind("share", shareDialog);
  bind("trash", async () => {
    if (
      !(await askConfirm(
        current.deleted ? "Restaurar arquivo?" : "Mover para lixeira?",
        current.deleted
          ? "O arquivo voltará à biblioteca."
          : "O arquivo ficará recuperável na lixeira. Alterações atuais também serão salvas.",
      ))
    )
      return;
    current.deleted = !current.deleted;
    setDirty();
    await save();
  });
  const c = current.content;
  const root = document.querySelector("#editor-body");
  try {
    switch (current.kind) {
      case "document":
      case "note":
        textEditor(root, c);
        break;
      case "sheet":
        sheetEditor(root, c);
        break;
      case "slides":
        slideEditor(root, c);
        break;
      case "board":
        boardEditor(root, c);
        break;
      case "calendar":
        calendarEditor(root, c);
        break;
      case "form":
        formEditor(root, c);
        break;
      case "table":
        tableEditor(root, c);
        break;
      case "diagram":
        diagramEditor(root, c);
        break;
      case "portal":
        portalEditor(root, c);
        break;
    }
  } catch (e) {
    root.textContent =
      "Formato de conteúdo incompatível com este editor. Exporte o JSON para preservar seus dados.";
  }
  if (read)
    root
      .querySelectorAll("input,textarea,select,button")
      .forEach(n=>{const allowed={slides:'[data-slide],#present',document:'#export-text,#document-mode',note:'#export-text,#document-mode',portal:'[data-link]',diagram:'#diagram-svg',table:'#table-filter,#table-csv',form:'#form-csv'}[current.kind];if(!allowed||!n.matches(allowed))n.disabled=true;});
  colors();
}
// Static table of contents built from the document headings (# and ##, ###).
function tableOfContents(text) {
  const lines=[];let fence=false;
  for(const line of String(text).split('\n')){
    if(/^\s*```/.test(line))fence=!fence;
    const m=!fence&&line.match(/^(#{1,3})\s+(.+?)\s*#*\s*$/);
    if(m&&m[2].trim().toLowerCase()!=='sumário')lines.push('  '.repeat(m[1].length-1)+'- '+m[2].replace(/[*_`]/g,''));
  }
  return lines.length?'## Sumário\n\n'+lines.join('\n'):'';
}
// Print with header, footer and page numbers using CSS page margin boxes.
function printPages(c) {
  const quote=s=>'"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\n\r]/g,' ')+'"';
  const rules=[];
  if(c.header)rules.push(`@top-center{content:${quote(c.header)};font:11px Arial,sans-serif;color:#444}`);
  if(c.footer)rules.push(`@bottom-left{content:${quote(c.footer)};font:11px Arial,sans-serif;color:#444}`);
  if(c.pageNumbers)rules.push('@bottom-right{content:"Página " counter(page) " de " counter(pages);font:11px Arial,sans-serif;color:#444}');
  const style=document.createElement('style');style.id='print-page-setup';
  style.textContent=`@page{margin:20mm 16mm;${rules.join('')}}`;
  document.getElementById('print-page-setup')?.remove();document.head.append(style);
  const cleanup=()=>{style.remove();removeEventListener('afterprint',cleanup);};
  addEventListener('afterprint',cleanup);
  window.print();
}
function textEditor(root, c) {
  documentEditor?.dispose();documentEditor=null;const token={};root.documentToken=token;
  c.text ??= "";
  let visual=true,doc=null;
  try{visual=sessionStorage.getItem('drap-document-mode')!=='markdown';}catch{}
  const readOnly=current.role==='read';
  root.innerHTML = `<div class="toolbar"><button id="document-mode">Editar Markdown</button><button id="document-paragraph">Parágrafo</button><button data-format="# ">Título</button><button data-format="## ">Subtítulo</button><button data-format="**">Negrito</button><button data-format="*">Itálico</button><button data-format="- ">Lista</button><button data-format="- [ ] ">Checklist</button><button id="insert-table">Tabela</button><button id="insert-link">Link</button><button id="document-image">Inserir imagem</button><button id="document-images">Gerenciar imagens</button><button id="document-toc">Sumário</button><button id="document-pagebreak">Quebra de página</button><button id="document-page-setup">Cabeçalho e rodapé</button><button id="find-replace">Localizar e substituir</button><button id="to-slides">Criar apresentação ↗</button><button id="export-text">Baixar texto</button><button id="document-undo">Desfazer</button><button id="document-redo">Refazer</button><span class="muted" id="word-count"></span></div><div class="toolbar" id="document-table-tools"><span id="document-table-hint">Selecione uma célula para editar a tabela.</span><button data-document-command="row">Adicionar linha</button><button data-document-command="column">Adicionar coluna</button><button data-document-command="deleteRow">Excluir linha</button><button data-document-command="deleteColumn">Excluir coluna</button><button data-document-command="deleteTable">Excluir tabela</button></div><div class="document"><textarea id="text" aria-label="Conteúdo do documento" placeholder="Escreva sua próxima ideia… Use # para títulos e **texto** para negrito.">${esc(c.text)}</textarea><article id="preview" class="preview">${markdown(c.text,c.images)}</article></div>`;
  const update = () => {
    if(doc)doc.refresh();else document.querySelector("#preview").innerHTML = markdown(c.text,c.images);
    document.querySelector("#word-count").textContent =
      `${doc?doc.words():(c.text.trim()?c.text.trim().split(/\s+/).length:0)} palavras`;
  };
  update();
  if(c.images?.length)root.querySelector('#export-text').textContent='Baixar HTML com imagens';
  const setMode=()=>{root.querySelector('.document').classList.toggle('visual-mode',visual);root.querySelector('#text').hidden=visual;root.querySelector('#document-mode').textContent=visual?'Editar Markdown':'Editar visualmente';root.querySelector('#document-table-tools').hidden=!visual;for(const id of ['document-paragraph','document-undo','document-redo'])root.querySelector('#'+id).hidden=!visual;};
  setMode();
  bind('document-mode',()=>{visual=!visual;try{sessionStorage.setItem('drap-document-mode',visual?'visual':'markdown');}catch{}setMode();});
  bind('document-paragraph',()=>{if(visual)doc?.format('paragraph');});
  // Page layout helpers: table of contents, page breaks, header/footer for print and DOCX.
  const insertMarkdown=text=>{if(readOnly)return;if(visual&&doc){doc.insert(text);return;}const area=root.querySelector('#text');area.setRangeText('\n'+text+'\n',area.selectionStart,area.selectionEnd,'end');c.text=area.value;update();setDirty();};
  bind('document-toc',()=>{const toc=tableOfContents(c.text);if(!toc){notify('Use Título e Subtítulo no documento para gerar o sumário.');return;}insertMarkdown(toc);notify('Sumário inserido. Se mudar os títulos, insira um novo sumário.');});
  bind('document-pagebreak',()=>{if(visual)doc?.format('pageBreak');else insertMarkdown('---');});
  bind('document-page-setup',()=>showDialog(`<h2>Cabeçalho e rodapé</h2><form id="page-setup-form"><p class="muted">Aparecem em todas as páginas ao imprimir ou salvar em PDF e no arquivo DOCX.</p><label class="field">Cabeçalho<input name="header" maxlength="200" value="${esc(c.header||'')}"></label><label class="field">Rodapé<input name="footer" maxlength="200" value="${esc(c.footer||'')}"></label><label class="checklist"><input type="checkbox" name="pageNumbers" ${c.pageNumbers?'checked':''}>Numerar páginas (Página X de Y)</label><div class="row"><button type="button" id="page-setup-cancel">Cancelar</button><button class="primary" ${readOnly?'disabled':''}>Aplicar</button></div></form>`,()=>{bind('page-setup-cancel',closeDialog);bind('page-setup-form',e=>{e.preventDefault();const f=new FormData(e.target);for(const key of ['header','footer']){const v=String(f.get(key)||'').trim();if(v)c[key]=v;else delete c[key];}if(f.has('pageNumbers'))c.pageNumbers=true;else delete c.pageNumbers;closeDialog();setDirty();notify('Cabeçalho e rodapé atualizados.');},'submit');}));
  for(const command of ['undo','redo'])bind('document-'+command,()=>{if(visual)doc?.format(command);else{root.querySelector('#text').focus();document.execCommand(command);}});
  root.querySelectorAll('[data-document-command]').forEach(el=>el.onclick=()=>doc?.format(el.dataset.documentCommand));
  import('/document.js').then(({mountDocument})=>{if(!root.isConnected||root.documentToken!==token)return;root.querySelector('#preview').textContent='';doc=mountDocument(root.querySelector('#preview'),c,{readOnly,onChange:(text,words)=>{c.text=text;root.querySelector('#text').value=text;root.querySelector('#word-count').textContent=words+' palavras';setDirty();},notify,onState:state=>{root.querySelector('#document-table-hint').textContent=state.table?'Tabela selecionada:':'Selecione uma célula para editar a tabela.';root.querySelectorAll('[data-document-command]').forEach(el=>el.disabled=readOnly||!state.table);root.querySelector('#document-undo').disabled=readOnly||!state.undo;root.querySelector('#document-redo').disabled=readOnly||!state.redo;}});documentEditor=doc;root.querySelectorAll('[data-document-command]').forEach(el=>el.disabled=readOnly||!doc.state().table);root.querySelector('#document-undo').disabled=true;root.querySelector('#document-redo').disabled=true;root.querySelector('#preview').dataset.ready='true';root.querySelector('#word-count').textContent=doc.words()+' palavras';}).catch(e=>{if(!root.isConnected||root.documentToken!==token)return;visual=false;setMode();notify('O editor visual não carregou. A edição Markdown continua disponível.');});

  bind(
    "text",
    (e) => {
      c.text = e.target.value;
      update();
      setDirty();
    },
    "input",
  );
  document.querySelectorAll("[data-format]").forEach(
    (n) =>
      (n.onclick = () => {
        if(visual){doc?.format(n.dataset.format);return;}
        const input = document.querySelector("#text"),
          a = input.selectionStart,
          b = input.selectionEnd,
          f = n.dataset.format;
        input.setRangeText(
          f + input.value.slice(a, b) + (f.includes("*") ? f : ""),
          a,
          b,
          "end",
        );
        c.text = input.value;
        update();
        setDirty();
        input.focus();
      }),
  );
  function insertSnippet(text) {
    if(visual&&doc){doc.insert(text);return;}
    const input=document.querySelector('#text');input.setRangeText(text,input.selectionStart,input.selectionEnd,'end');c.text=input.value;update();setDirty();input.focus();
  }
  bind('document-image',()=>{
    const input=document.createElement('input');input.type='file';input.accept='image/png,image/jpeg,image/webp';
    input.onchange=async()=>{if(!input.files[0])return;try{const {src,ratio}=await raster(input.files[0]);if(!root.isConnected)return;if((c.images||[]).length>=20||JSON.stringify(c).length+src.length>1800000)throw Error('Limite de imagens do documento atingido. Remova imagens não usadas ou crie outro documento.');const im={id:crypto.randomUUID(),src,ratio,alt:input.files[0].name.slice(0,200),width:80};(c.images??=[]).push(im);insertSnippet('\n!['+im.alt.replaceAll(']','')+'](drap-image:'+im.id+')\n');document.querySelector('#export-text').textContent='Baixar HTML com imagens';}catch(e){notify(e.message);}};input.click();
  });
  bind('document-images',()=>showDialog(`<h2>Imagens do documento</h2>${(c.images||[]).map((im,i)=>`<article class="card"><img src="${esc(im.src)}" alt="${esc(im.alt)}" style="max-width:120px;max-height:100px"><label class="field">Descrição<input data-image-alt="${i}" aria-label="Descrição da imagem ${i+1}" maxlength="200" value="${esc(im.alt)}"></label><label class="field">Largura (%)<input type="number" min="10" max="100" data-image-width="${i}" aria-label="Largura da imagem ${i+1}" value="${im.width||80}"></label><button data-image-remove="${i}">Remover imagem ${i+1}</button></article>`).join('')||'<p>Nenhuma imagem inserida.</p>'}<button id="images-close">Concluir</button>`,()=>{
    modal.querySelectorAll('[data-image-alt]').forEach(el=>el.oninput=()=>{c.images[+el.dataset.imageAlt].alt=el.value;update();setDirty();});
    modal.querySelectorAll('[data-image-width]').forEach(el=>el.onchange=()=>{const value=Number(el.value);if(!Number.isFinite(value))return;c.images[+el.dataset.imageWidth].width=Math.max(10,Math.min(100,value));el.value=c.images[+el.dataset.imageWidth].width;update();setDirty();});
    modal.querySelectorAll('[data-image-remove]').forEach(el=>el.onclick=()=>{const im=c.images[+el.dataset.imageRemove];c.text=c.text.split('\n').filter(line=>!line.includes('](drap-image:'+im.id+')')).join('\n');c.images.splice(+el.dataset.imageRemove,1);closeDialog();setDirty();textEditor(root,c);});bind('images-close',closeDialog);
  }));
  bind('insert-table',()=>insertSnippet('\n| Coluna 1 | Coluna 2 |\n| --- | --- |\n| Valor | Valor |\n'));
  bind('insert-link',()=>showDialog('<h2>Inserir link</h2><form id="link-form"><label class="field">Texto do link<input name="label" required></label><label class="field">URL HTTPS<input name="url" type="url" required></label><button class="primary">Inserir</button></form>',()=>bind('link-form',e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));if(!/^https?:\/\//i.test(d.url))return notify('Use um endereço HTTP ou HTTPS.');closeDialog();insertSnippet('['+d.label.replaceAll(']','')+']('+d.url.replaceAll(')','%29')+')');},'submit')));
  bind('find-replace',()=>showDialog('<h2>Localizar e substituir</h2><form id="replace-form"><label class="field">Localizar<input name="search" required></label><label class="field">Substituir por<input name="replacement"></label><button class="primary">Substituir todas</button></form>',()=>bind('replace-form',e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));if(visual&&doc){const count=doc.replace(d.search,d.replacement);closeDialog();notify(count+' ocorrências substituídas.');return;}const count=c.text.split(d.search).length-1;c.text=c.text.replaceAll(d.search,d.replacement);closeDialog();setDirty();textEditor(root,c);notify(count+' ocorrências substituídas.');},'submit')));
  bind("export-text", () =>
    c.images?.length?download(current.title+".html",'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>'+esc(current.title)+'</title><body>'+(doc?doc.html():markdown(c.text,c.images))+'</body></html>',"text/html"):download(current.title + ".md", c.text, "text/markdown"),
  );
  bind("to-slides", () =>
    convert(
      "slides",
      {
        slides: documentSlides(c),
      },
      " — Apresentação",
    ),
  );
}
async function sheetEditor(root, c) {
  root.classList.add('spreadsheet-editor');
  root.innerHTML = `<div class="toolbar sheet-tools"><label>Intervalo <input id="sheet-address" aria-label="Intervalo da planilha" value="A1" size="10"></label><button id="sheet-select">Selecionar</button><label>Valor ou fórmula <input id="sheet-value" aria-label="Valor ou fórmula" placeholder="=SUM(A1:A5)"></label><button id="sheet-apply">Aplicar à célula</button><button id="sheet-insert" class="primary">＋ Inserir</button><button id="csv-import">Importar CSV</button><button id="csv-export">Exportar CSV</button><button id="sheet-report">Criar relatório ↗</button><button id="sheet-chart-add">Criar gráfico</button><button id="sheet-pivot-add">Tabela dinâmica</button></div><div class="toolbar sheet-tools"><button id="sheet-calculate">∑ Inserir cálculo</button><button id="sheet-row">Inserir linha</button><button id="sheet-column">Inserir coluna</button><button id="sheet-clear">Limpar valores</button><button id="sheet-paste">Colar tabela</button><span class="muted">Clique numa célula e digite. Enter confirma; Tab avança. Selecione um intervalo para formatar.</span></div><div id="sheet-link-bar" class="sheet-link-bar" hidden></div><div id="spreadsheet" aria-label="Editor de planilhas"><p>Carregando editor…</p></div><p class="muted sheet-help">Use a barra de ferramentas para formatar, mesclar, filtrar e ordenar. Clique com o botão direito para inserir/excluir linhas e colunas. As células, a barra de fórmulas e o campo acima aceitam SUM/IF/VLOOKUP e os equivalentes SOMA/SE/PROCV; os nomes são armazenados em inglês. Ao digitar números na grade, use vírgula decimal (1234,50). Salve para registrar no banco. XLSX preserva valores, fórmulas, estilos, mesclagens, filtros e validações comuns; regras avançadas ficam no arquivo DRAP e no JSON. Gráficos de colunas, linhas e pizza ficam abaixo da grade e no XLSX. Tabelas dinâmicas agrupam e resumem os dados abaixo da grade. Macros VBA ainda não estão disponíveis.</p><section id="sheet-links" aria-label="Arquivos e links vinculados"></section><section id="sheet-charts" aria-label="Gráficos da planilha"></section><section id="sheet-pivots" aria-label="Tabelas dinâmicas"></section>`;
  const item=current;let pivotUI=null;
  try {
    if (!document.querySelector('#spreadsheet-css')) {
      const link=document.createElement('link');link.id='spreadsheet-css';link.rel='stylesheet';link.href='/spreadsheet.css';document.head.append(link);
      await new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=()=>reject(Error('Falha ao carregar os estilos da planilha.'));});
    }
    const {mountSpreadsheet}=await import('/spreadsheet.js');
    if(!root.isConnected || current!==item)return;
    const host=root.querySelector('#spreadsheet');host.textContent='';
    const mounted=await mountSpreadsheet(host,c,{id:item.id,name:item.title,readOnly:item.role==='read',onChange:setDirty,onError:notify,onSelection:(address,value)=>{if(!root.isConnected)return;showCellLink(address);if(document.activeElement?.closest('.sheet-tools'))return;root.querySelector('#sheet-address').value=address;root.querySelector('#sheet-value').value=value;},onRender:()=>{renderCharts();pivotUI?.render();}});
    if(!root.isConnected||current!==item){mounted.dispose();return;}
    spreadsheet=mounted;
    pivotUI=mountPivots({root,content:c,spreadsheet,readOnly:item.role==='read',dirty:setDirty,dialog:showDialog,closeDialog,notify,download,escapeHtml:esc});
    host.dataset.ready='true';
    renderCharts();
    renderLinks();
    const address=()=>document.querySelector('#sheet-address').value.trim().toUpperCase();
    const action=fn=>async()=>{try{await fn();}catch(e){notify(e.message);}};
    bind('sheet-select',action(()=>{spreadsheet.select(address());showCellLink(address());const value=spreadsheet.read(address());document.querySelector('#sheet-value').value=value.formulas[0]?.[0]||(value.values[0]?.[0]??'');}));
    bind('sheet-apply',action(()=>spreadsheet.set(address(),document.querySelector('#sheet-value').value)));
    for(const kind of ['row','column','clear'])bind('sheet-'+kind,action(()=>spreadsheet.quick(kind,address())));
    bind('sheet-paste',()=>showDialog(`<h2>Colar tabela</h2><form id="sheet-paste-form"><label class="field">Célula inicial<input name="target" value="${esc(address().split(':')[0])}" required pattern="[A-Za-z]{1,3}[1-9][0-9]{0,5}"></label><label class="field">Dados copiados do Excel ou CSV<textarea name="data" rows="8" required></textarea></label><p id="paste-error" role="alert"></p><button class="primary">Colar dados</button></form>`,()=>bind('sheet-paste-form',async e=>{e.preventDefault();try{const f=new FormData(e.target);await spreadsheet.paste(f.get('data'),f.get('target').toUpperCase());closeDialog();notify('Dados inseridos na planilha.');}catch(err){document.querySelector('#paste-error').textContent=err.message;}},'submit')));
    bind('sheet-calculate',()=>showDialog(`<h2>Inserir cálculo</h2><form id="sheet-calc-form"><label class="field">Operação<select name="operation" aria-label="Operação"><option value="SUM">Soma</option><option value="AVERAGE">Média</option><option value="MIN">Mínimo</option><option value="MAX">Máximo</option><option value="COUNT">Contar números</option><option value="COUNTA">Contar preenchidas</option></select></label><label class="field">Intervalo de origem<input name="source" value="${esc(address())}" required pattern="[A-Za-z]{1,3}[1-9][0-9]{0,5}(:[A-Za-z]{1,3}[1-9][0-9]{0,5})?"></label><label class="field">Célula do resultado<input name="target" placeholder="Ex.: D1" required pattern="[A-Za-z]{1,3}[1-9][0-9]{0,5}"></label><p>Escolha uma célula fora do intervalo de origem. O resultado acompanhará as alterações dos dados.</p><p id="calc-error" role="alert"></p><button class="primary">Inserir fórmula</button></form>`,()=>bind('sheet-calc-form',async e=>{e.preventDefault();try{const f=new FormData(e.target),source=f.get('source').toUpperCase(),target=f.get('target').toUpperCase();const parse=a=>{const m=/^([A-Z]+)([0-9]+)$/.exec(a);return {c:[...m[1]].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0),r:+m[2]};};const [a,b]=source.split(':'),start=parse(a),end=parse(b||a),dest=parse(target);if(start.r>end.r||start.c>end.c)throw Error('Use um intervalo em ordem crescente.');if(dest.r>=start.r&&dest.r<=end.r&&dest.c>=start.c&&dest.c<=end.c)throw Error('A célula do resultado precisa ficar fora da origem.');spreadsheet.set(target,'='+f.get('operation')+'('+source+')');await spreadsheet.flush();closeDialog();notify('Fórmula inserida em '+target+'.');}catch(err){document.querySelector('#calc-error').textContent=err.message;}},'submit')));

    bind('csv-import',()=>pickFile('.csv',async text=>{try{await spreadsheet.paste(text,address());}catch(e){notify(e.message);}}));
    bind('sheet-chart-add',()=>showDialog(`<h2>Criar gráfico</h2><form id="chart-form"><label class="field">Título do gráfico<input name="title" value="${esc(current.title)}" maxlength="100" required></label><label class="field">Tipo de gráfico<select name="type">${Object.entries(CHART_TYPES).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label><label class="field">Intervalo de dados<input name="range" value="${esc(address().includes(':')?address():'A1:B5')}" required></label><p>Primeira coluna: rótulos (na dispersão, valores de X). Colunas seguintes: até 6 séries numéricas, cada uma com cabeçalho. Pizza e rosca usam uma série. Até 200 linhas. O gráfico acompanha os valores dessas células.</p><p id="chart-error" role="alert" class="error"></p><button class="primary">Adicionar gráfico</button></form>`,()=>bind('chart-form',async e=>{e.preventDefault();try{await spreadsheet.flush();if((c.charts||[]).length>=10)throw Error('Limite de dez gráficos por arquivo.');const d=Object.fromEntries(new FormData(e.target));d.range=d.range.trim().toUpperCase();if(!/^[A-Z]{1,3}[1-9]\d{0,5}:[A-Z]{1,3}[1-9]\d{0,5}$/.test(d.range))throw Error('Use um intervalo como A1:B5.');d.sheetId=spreadsheet.activeSheetId();d.id=crypto.randomUUID();chartData(spreadsheet.chartRows(d.range,d.sheetId),d.type);(c.charts??=[]).push(d);closeDialog();setDirty();renderCharts();}catch(err){document.querySelector('#chart-error').textContent=err.message;}},'submit')));
    bind('csv-export',action(async()=>{await spreadsheet.flush();download(current.title+'.csv',spreadsheet.csv(),'text/csv');}));
    bind('sheet-insert',()=>insertLinkDialog(address().split(':')[0]));
    bind('sheet-report',action(async()=>{await spreadsheet.flush();await convert('document',{text:'# '+current.title+'\n\n'+spreadsheet.rows().map(r=>r.join(' | ')).join('\n')},' — Relatório');}));
    if(item.role==='read')root.querySelectorAll('.sheet-tools input,.sheet-tools button:not(#csv-export)').forEach(el=>el.disabled=true);
  // Cell links: a cell can point to another DRAP office file or to an external https address.
  function cellLink(cell,sheetId=spreadsheet.activeSheetId()){return (c.links||[]).find(l=>l.sheetId===sheetId&&l.cell===cell);}
  function linkLabel(l){return l.type==='item'?(items.find(i=>i.id===l.item)?.title||l.title):l.url;}
  function openLink(l){if(l.type==='item')openItem(l.item);else window.open(l.url,'_blank','noopener,noreferrer');}
  function showCellLink(address){
    const bar=root.querySelector('#sheet-link-bar');if(!bar||!spreadsheet)return;
    const l=cellLink(String(address).split(':')[0]);
    if(!l){bar.hidden=true;bar.innerHTML='';return;}
    bar.hidden=false;
    bar.innerHTML=`<span>🔗 ${l.type==='item'?'Arquivo':'Link'} em ${esc(l.cell)}: <strong>${esc(linkLabel(l))}</strong></span><button id="cell-link-open" class="primary">Abrir ${l.type==='item'?'arquivo':'link'} ↗</button>${item.role!=='read'?'<button id="cell-link-remove">Remover vínculo</button>':''}`;
    bind('cell-link-open',()=>openLink(l));
    bind('cell-link-remove',()=>{c.links=c.links.filter(x=>x!==l);setDirty();showCellLink(l.cell);renderLinks();});
  }
  function renderLinks(){
    const panel=root.querySelector('#sheet-links');if(!panel||!spreadsheet)return;
    const sheets=new Map(spreadsheet.listSheets().map(s=>[s.id,s.name]));
    const list=(c.links||[]);
    panel.innerHTML=list.length?`<h3>Arquivos e links vinculados</h3><ul class="sheet-link-list">${list.map((l,i)=>`<li><span class="badge">${l.type==='item'?esc(TYPES[l.kind]?.single||'Arquivo'):'Link'}</span> <strong>${esc(linkLabel(l))}</strong> <span class="muted">${esc(sheets.get(l.sheetId)||'Aba removida')} · ${esc(l.cell)}</span> <button data-link-open="${i}">Abrir ↗</button><button data-link-cell="${i}">Ir para a célula</button></li>`).join('')}</ul>`:'';
    panel.querySelectorAll('[data-link-open]').forEach(b=>b.onclick=()=>openLink(list[+b.dataset.linkOpen]));
    panel.querySelectorAll('[data-link-cell]').forEach(b=>b.onclick=()=>{const l=list[+b.dataset.linkCell];try{spreadsheet.activateSheet?.(l.sheetId);spreadsheet.select(l.cell);showCellLink(l.cell);}catch(e){notify(e.message);}});
  }
  function insertLinkDialog(cell){
    const files=items.filter(i=>i.id!==item.id&&!i.deleted);
    showDialog(`<h2>Inserir na planilha</h2><form id="insert-link-form"><fieldset class="field"><legend>O que inserir</legend><label class="checklist"><input type="radio" name="type" value="item" ${files.length?'checked':''} ${files.length?'':'disabled'}>Arquivo do DRAP office</label><label class="checklist"><input type="radio" name="type" value="url" ${files.length?'':'checked'}>Link externo (site)</label></fieldset><label class="field" data-for="item">Arquivo<select name="item" aria-label="Arquivo a vincular">${files.map(f=>`<option value="${esc(f.id)}">${esc(f.title)} — ${esc(TYPES[f.kind]?.single||f.kind)}</option>`).join('')}</select></label><label class="field" data-for="url" hidden>Endereço (https)<input name="url" type="url" placeholder="https://" maxlength="2000"></label><label class="field">Texto exibido na célula<input name="text" maxlength="200" placeholder="Usa o nome do arquivo se ficar vazio"></label><label class="field">Célula<input name="cell" value="${esc(cell)}" required pattern="[A-Za-z]{1,3}[1-9][0-9]{0,5}" aria-label="Célula de destino"></label><p id="insert-link-error" class="error" role="alert"></p><div class="row"><button type="button" id="insert-link-cancel">Cancelar</button><button class="primary">Inserir</button></div></form>`,()=>{
      const form=document.querySelector('#insert-link-form');
      const toggle=()=>{const type=new FormData(form).get('type');form.querySelectorAll('[data-for]').forEach(el=>el.hidden=el.dataset.for!==type);};
      form.querySelectorAll('[name="type"]').forEach(r=>r.onchange=toggle);toggle();
      bind('insert-link-cancel',closeDialog);
      bind('insert-link-form',async e=>{
        e.preventDefault();const d=new FormData(form),error=document.querySelector('#insert-link-error');
        try{
          const type=d.get('type'),target=String(d.get('cell')).toUpperCase(),sheetId=spreadsheet.activeSheetId();
          let link;
          if(type==='item'){const f=files.find(x=>x.id===d.get('item'));if(!f)throw Error('Escolha um arquivo.');link={type:'item',item:f.id,kind:f.kind,title:f.title.slice(0,200)};}
          else{let url;try{url=new URL(d.get('url'));}catch{throw Error('Informe um endereço completo, começando com https://');}if(url.protocol!=='https:')throw Error('Use um endereço https://');link={type:'url',url:url.href};}
          if(!cellLink(target,sheetId)&&(c.links||[]).length>=200)throw Error('Limite de 200 vínculos por planilha.');
          const text=String(d.get('text')||'').trim()||(link.type==='item'?link.title:link.url);
          await spreadsheet.flush();
          spreadsheet.set(target,text.startsWith('=')?"'"+text:text);
          c.links=(c.links||[]).filter(l=>!(l.sheetId===sheetId&&l.cell===target));
          c.links.push({...link,sheetId,cell:target});
          setDirty();closeDialog();renderLinks();showCellLink(target);
          notify(link.type==='item'?'Arquivo vinculado à célula '+target+'.':'Link inserido na célula '+target+'.');
        }catch(err){error.textContent=err.message;}
      },'submit');
    });
  }
  function renderCharts(){
    if(!spreadsheet||!root.isConnected)return;
    const panel=root.querySelector('#sheet-charts');
    panel.innerHTML=(c.charts||[]).map((chart,i)=>{try{const rows=spreadsheet.chartRows(chart.range,chart.sheetId),svg=chartSvg(rows,chart);return `<article class="sheet-chart"><div class="toolbar"><strong>${esc(chart.title)}</strong><span class="muted">${esc(chart.range)}</span><button data-chart-download="${i}">Baixar SVG</button>${item.role!=='read'?`<button data-chart-remove="${i}">Excluir gráfico</button>`:''}</div>${svg}<details><summary>Ver dados do gráfico</summary><table><thead><tr>${rows[0].map(v=>'<th>'+esc(v)+'</th>').join('')}</tr></thead><tbody>${rows.slice(1).map(r=>'<tr>'+r.map(v=>'<td>'+esc(v??'')+'</td>').join('')+'</tr>').join('')}</tbody></table></details></article>`;}catch(e){return `<article class="sheet-chart"><p>${esc(chart.title)}: ${esc(e.message)}</p>${item.role!=='read'?`<button data-chart-remove="${i}">Excluir gráfico</button>`:''}</article>`;}}).join('');
    panel.querySelectorAll('[data-chart-download]').forEach(el=>el.onclick=()=>{const chart=c.charts[+el.dataset.chartDownload];download(chart.title+'.svg',chartSvg(spreadsheet.chartRows(chart.range,chart.sheetId),chart),'image/svg+xml');});
    panel.querySelectorAll('[data-chart-remove]').forEach(el=>el.onclick=()=>{c.charts.splice(+el.dataset.chartRemove,1);setDirty();renderCharts();});
  }
  } catch(e) {root.querySelector('#spreadsheet').textContent='Não foi possível abrir a planilha: '+e.message;}
}
function slideEditor(root,c){mountSlides(root,c,{dirty:setDirty,notify,present,readOnly:current.role==='read',initialIndex:selectedSlide,onSelect:i=>{selectedSlide=i;}});}
function present(slides, theme="light") {
  let i = 0;
  const div = document.createElement("section");
  div.className = "present";
  div.dataset.theme=theme;
  div.setAttribute("role", "dialog");
  div.setAttribute("aria-label", "Apresentação");
  document.body.append(div);
  function close() {
    div.remove();
    document.removeEventListener("keydown", key);
  }
  function render() {
    div.innerHTML = `<small>${esc(current.title)} · ${i + 1} / ${slides.length}</small><div class="slide-stage" data-theme="${esc(theme)}">${slideMarkup(slides[i],{heading:'h1'})}</div><div class="row controls"><button id="previous">← Anterior</button><button id="next-slide">Próximo →</button><button id="close-present">Sair (Esc)</button></div>`;
    div.querySelector("#previous").onclick = () => {
      i = Math.max(0, i - 1);
      render();
    };
    div.querySelector("#next-slide").onclick = () => {
      i = Math.min(slides.length - 1, i + 1);
      render();
    };
    div.querySelector("#close-present").onclick = close;
  }
  function key(e) {
    if (e.key === "Escape") close();
    if (e.key === "ArrowRight") {
      i = Math.min(slides.length - 1, i + 1);
      render();
    }
    if (e.key === "ArrowLeft") {
      i = Math.max(0, i - 1);
      render();
    }
  }
  document.addEventListener("keydown", key);
  render();
  div.querySelector("button").focus();
}
let boardView = "kanban";
function boardEditor(root, c) {
  c.tasks ??= [];
  ensureTaskIds(c.tasks);
  const statuses=['A fazer','Em andamento','Concluído'];
  const priorities=['Baixa','Normal','Alta','Urgente'];
  const byId=new Map(c.tasks.map(t=>[t.id,t]));
  const deps=t=>(t.depends||[]).map(id=>byId.get(id)?.title).filter(Boolean);
  const card=(t,i,status)=>`<article class="card"><h3>${t.milestone?'◆ ':''}${esc(t.title)}</h3><span class="badge">${esc(t.priority || 'Normal')}</span><p class="muted">${t.start?'Início: '+esc(t.start)+'<br>':''}${t.due?(t.milestone?'Marco: ':'Prazo: ')+esc(t.due):'Sem prazo'}${t.assignee?'<br>Responsável: '+esc(t.assignee):''}${deps(t).length?'<br>Depende de: '+deps(t).map(esc).join(', '):''}</p>${(t.subtasks||[]).map((s,j)=>`<label class="checklist"><input type="checkbox" data-subtask="${i}:${j}" ${s.done?'checked':''}>${esc(s.title)}</label>`).join('')}<select data-task="${i}" aria-label="Estado de ${esc(t.title)}">${statuses.map(s=>`<option ${s===status?'selected':''}>${s}</option>`).join('')}</select><div class="row"><button data-edit-task="${i}">Detalhes</button><button data-remove-task="${i}" class="danger">Excluir</button></div></article>`;
  const toolbar=`<form id="add-task" class="toolbar"><input name="title" placeholder="O que precisa ser feito?" aria-label="Nome da tarefa" maxlength="200" required><input name="start" type="date" aria-label="Início"><input name="due" type="date" aria-label="Prazo"><select name="priority" aria-label="Prioridade da tarefa">${priorities.map(p=>`<option ${p==='Normal'?'selected':''}>${p}</option>`).join('')}</select><button class="primary">＋ Adicionar tarefa</button></form><div class="row" role="group" aria-label="Visualização"><button type="button" data-board-view="kanban" aria-pressed="${boardView==='kanban'}" class="${boardView==='kanban'?'primary':''}">Kanban</button><button type="button" data-board-view="timeline" aria-pressed="${boardView==='timeline'}" class="${boardView==='timeline'?'primary':''}">Cronograma</button></div>`;
  root.innerHTML=toolbar+(boardView==='timeline'?timelineMarkup(c.tasks):`<div class="board">${statuses.map(status=>`<section class="column"><h3>${status} <span class="badge">${c.tasks.filter(t=>t.status===status).length}</span></h3>${c.tasks.map((t,i)=>t.status===status?card(t,i,status):'').join('')}</section>`).join('')}</div>`);
  root.querySelectorAll('[data-board-view]').forEach(n=>n.onclick=()=>{boardView=n.dataset.boardView;boardEditor(root,c);});
  bind('add-task',e=>{e.preventDefault();if(c.tasks.length>=1000)return notify('Limite de 1000 tarefas.');const data=Object.fromEntries(new FormData(e.target));if(data.start&&data.due&&data.start>data.due)return notify('O início deve ser antes do prazo.');c.tasks.push({...data,status:'A fazer',assignee:'',subtasks:[],depends:[],milestone:false});ensureTaskIds(c.tasks);setDirty();boardEditor(root,c);},'submit');
  root.querySelectorAll('[data-task]').forEach(n=>n.onchange=()=>{c.tasks[+n.dataset.task].status=n.value;setDirty();boardEditor(root,c);});
  root.querySelectorAll('[data-remove-task]').forEach(n=>n.onclick=()=>{const [removed]=c.tasks.splice(+n.dataset.removeTask,1);for(const t of c.tasks)t.depends=(t.depends||[]).filter(id=>id!==removed.id);setDirty();boardEditor(root,c);});
  root.querySelectorAll('[data-subtask]').forEach(n=>n.onchange=()=>{const [i,j]=n.dataset.subtask.split(':').map(Number);c.tasks[i].subtasks[j].done=n.checked;setDirty();});
  root.querySelectorAll('[data-edit-task]').forEach(n=>n.onclick=()=>{
    const task=c.tasks[+n.dataset.editTask];
    const others=c.tasks.filter(t=>t!==task);
    showDialog(`<h2>Detalhes da tarefa</h2><form id="task-details"><label class="field">Título da tarefa<input name="title" value="${esc(task.title)}" maxlength="200" required></label><label class="field">Responsável<input name="assignee" value="${esc(task.assignee||'')}" maxlength="100"></label><label class="field">Início<input name="start" type="date" value="${esc(task.start||'')}"></label><label class="field">Data limite<input name="due" type="date" value="${esc(task.due)}"></label><label class="checklist"><input type="checkbox" name="milestone" ${task.milestone?'checked':''}>Marco (entrega de um dia, sem duração)</label><label class="field">Prioridade<select name="priority">${priorities.map(p=>`<option ${p===(task.priority||'Normal')?'selected':''}>${p}</option>`).join('')}</select></label><fieldset class="task-deps"><legend>Depende de</legend>${others.length?others.map(o=>`<label class="checklist"><input type="checkbox" name="depends" value="${esc(o.id)}" ${(task.depends||[]).includes(o.id)?'checked':''}>${esc(o.title)}</label>`).join(''):'<p class="muted">Nenhuma outra tarefa.</p>'}</fieldset><label class="field">Subtarefas, uma por linha<textarea name="subtasks" rows="5">${esc((task.subtasks||[]).map(s=>s.title).join('\n'))}</textarea></label><p id="task-error" class="error" role="alert"></p><button class="primary">Aplicar detalhes</button></form>`,()=>bind('task-details',e=>{
      e.preventDefault();const form=new FormData(e.target);const data=Object.fromEntries(form);
      const error=document.querySelector('#task-error');
      const titles=data.subtasks.split('\n').map(t=>t.trim()).filter(Boolean);
      if(titles.length>50 || titles.some(t=>t.length>200)){error.textContent='Até 50 subtarefas, com 200 caracteres cada.';return;}
      data.milestone=form.has('milestone');data.depends=form.getAll('depends');
      if(data.start&&data.due&&data.start>data.due&&!data.milestone){error.textContent='O início deve ser antes da data limite.';return;}
      if(data.milestone&&!data.due){error.textContent='Informe a data do marco.';return;}
      const trial=c.tasks.map(t=>t===task?{...t,depends:data.depends}:t);
      if(findCycle(trial)){error.textContent='Essa dependência cria um ciclo entre tarefas.';return;}
      data.subtasks=titles.map(title=>({title,done:task.subtasks?.find(s=>s.title===title)?.done || false}));
      Object.assign(task,data);closeDialog();setDirty();boardEditor(root,c);
    },'submit'));
  });
}
function timelineMarkup(tasks) {
  const plan=schedule(tasks);
  if(plan.cycle) return `<p class="error" role="alert">As dependências formam um ciclo. Remova uma delas para ver o cronograma.</p>`;
  const undated=tasks.filter(t=>!taskSpan(t));
  if(!plan.tasks.length) return `<p class="muted">Defina início e prazo nas tarefas para montar o cronograma.</p>`;
  const span=Math.max(1,plan.end-plan.start+1);
  const byId=new Map(tasks.map(t=>[t.id,t]));
  const days=plan.end-plan.start+1;
  const path=plan.critical.map(id=>esc(byId.get(id).title)).join(' → ');
  return `<section class="timeline" aria-label="Cronograma"><p><strong>Período:</strong> ${isoDay(plan.start)} a ${isoDay(plan.end)} (${days} dias) · <strong>Caminho crítico:</strong> <span id="critical-path">${path}</span></p>${plan.conflicts.length?`<p class="error" role="alert">Começam antes de as dependências terminarem: ${plan.conflicts.map(id=>esc(byId.get(id).title)).join(', ')}. O cronograma mostra a data mais cedo possível.</p>`:''}<div class="gantt">${plan.tasks.map(r=>{const left=(r.es-plan.start)/span*100,width=r.milestone?0:(r.duration/span*100);const t=byId.get(r.id);return `<div class="gantt-row${r.critical?' critical':''}" data-gantt="${esc(r.id)}"><div class="gantt-label">${r.milestone?'◆ ':''}${esc(t.title)}<small>${isoDay(r.es)}${r.milestone?'':' a '+isoDay(r.ef)} · ${t.status}${r.critical?' · crítica':` · folga ${r.slack} d`}</small></div><div class="gantt-track"><span class="${r.milestone?'gantt-milestone':'gantt-bar'}" style="left:${left.toFixed(3)}%;width:${width.toFixed(3)}%" title="${esc(t.title)}"></span></div></div>`;}).join('')}</div>${undated.length?`<p class="muted">Sem datas: ${undated.map(t=>esc(t.title)).join(', ')}</p>`:''}</section>`;
}
function calendarEditor(root, c) {
  c.events ??= [];
  root.innerHTML = `<form id="add-event" class="toolbar"><input name="title" placeholder="Novo compromisso" aria-label="Título do evento" required maxlength="200"><input name="start" type="datetime-local" aria-label="Data e hora de início" required><input name="end" type="datetime-local" aria-label="Data e hora de fim" required><input name="location" aria-label="Local do evento" placeholder="Local" maxlength="500"><select name="repeat" aria-label="Repetir evento"><option value="none">Não repetir</option><option value="daily">Diariamente</option><option value="weekly">Semanalmente</option><option value="monthly">Mensalmente</option></select><input name="count" type="number" min="1" max="52" value="1" aria-label="Quantidade de ocorrências"><button class="primary">＋ Adicionar</button></form><p class="muted">Horários no fuso do seu navegador: ${esc(Intl.DateTimeFormat().resolvedOptions().timeZone)}. Repetições geram eventos individuais. Use ICS para intercâmbio com outras agendas; convites externos ainda não estão conectados.</p>${
    c.events.length
      ? c.events
          .map((event, index) => ({ ...event, index }))
          .sort((a, b) => a.start.localeCompare(b.start))
          .map(
            (e) =>
              `<article class="card row between"><div><h3>${esc(e.title)}</h3><p class="muted">${date(e.start)} → ${date(e.end)}${e.location ? " · " + esc(e.location) : ""}</p>${e.description?"<p>"+esc(e.description)+"</p>":""}</div><div class="row"><button data-edit-event="${e.index}">Editar compromisso</button><button data-event="${e.index}">Excluir</button></div></article>`,
          )
          .join("")
      : '<div class="empty">Sua agenda está livre. Adicione o primeiro compromisso.</div>'
  }`;
  bind(
    "add-event",
    (e) => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      if (d.end <= d.start)
        return notify("O fim deve ser posterior ao início.");
      const count=d.repeat==='none'?1:Number(d.count);
      if (!Number.isInteger(count) || count<1 || count>52 || c.events.length+count>1000) return notify('Até 52 repetições e 1000 eventos na agenda.');
      const start=new Date(d.start),duration=new Date(d.end)-start;
      for(let i=0;i<count;i++) {
        const occurrence=new Date(start);
        if(d.repeat==='monthly') { occurrence.setDate(1);occurrence.setMonth(start.getMonth()+i);const last=new Date(occurrence.getFullYear(),occurrence.getMonth()+1,0).getDate();occurrence.setDate(Math.min(start.getDate(),last)); }
        else occurrence.setDate(start.getDate()+i*(d.repeat==='weekly'?7:1));
        c.events.push({title:d.title,location:d.location||'',start:occurrence.toISOString(),end:new Date(+occurrence+duration).toISOString()});
      }
      setDirty();
      calendarEditor(root, c);
    },
    "submit",
  );
  root.querySelectorAll('[data-edit-event]').forEach(button=>button.onclick=()=>{
    const event=c.events[+button.dataset.editEvent];
    showDialog(`<h2>Editar compromisso</h2><form id="edit-event"><label class="field">Título do compromisso<input name="title" value="${esc(event.title)}" maxlength="200" required></label><label class="field">Início<input name="start" type="datetime-local" value="${localDateTime(event.start)}" required></label><label class="field">Fim<input name="end" type="datetime-local" value="${localDateTime(event.end)}" required></label><label class="field">Local<input name="location" value="${esc(event.location||'')}" maxlength="500"></label><label class="field">Descrição<textarea name="description" aria-label="Descrição do compromisso" maxlength="4000">${esc(event.description||'')}</textarea></label><p>Esta alteração afeta somente este compromisso.</p><p id="event-error" role="alert"></p><button class="primary">Aplicar compromisso</button></form>`,()=>bind('edit-event',e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));if(new Date(d.end)<=new Date(d.start)){document.querySelector('#event-error').textContent='O fim deve ser posterior ao início.';return;}Object.assign(event,{title:d.title,location:d.location,description:d.description,start:new Date(d.start).toISOString(),end:new Date(d.end).toISOString()});closeDialog();setDirty();calendarEditor(root,c);},'submit'));
  });
  root.querySelectorAll("[data-event]").forEach(
    (n) =>
      (n.onclick = () => {
        c.events.splice(+n.dataset.event, 1);
        setDirty();
        calendarEditor(root, c);
      }),
  );
}
function answerField(question, field, index) {
  const attrs=`name="q${index}" ${field.required?'required':''}`;
  const label=`${esc(question)}${field.required?' *':''}`;
  if(field.type==='multiple') return `<fieldset class="field answer-group" data-answer="${index}"><legend>${label}</legend>${(field.options||[]).map(o=>`<label class="checklist"><input type="checkbox" name="q${index}" value="${esc(o)}">${esc(o)}</label>`).join('')}</fieldset>`;
  if(field.type==='scale') return `<fieldset class="field answer-group scale" data-answer="${index}"><legend>${label}</legend>${Array.from({length:field.max||5},(_,n)=>`<label><input type="radio" ${attrs} value="${n+1}">${n+1}</label>`).join('')}</fieldset>`;
  return `<label class="field">${label}${field.type==='choice'?`<select ${attrs}><option value="">Selecione…</option>${(field.options||[]).map(o=>`<option>${esc(o)}</option>`).join('')}</select>`:`<input ${attrs} type="${field.type}" ${field.type==='number'?'step="any"':''} maxlength="4000">`}</label>`;
}
function collectAnswers(form, fields) {
  const values=new FormData(form);
  return fields.map((field,i)=>field.type==='multiple'?values.getAll('q'+i).join(MULTI_SEPARATOR):(values.get('q'+i)||''));
}
function correctAnswerField(field, i) {
  const options=field.type==='scale'?Array.from({length:field.max||5},(_,n)=>String(n+1)):(field.options||[]);
  let input;
  if(field.type==='multiple') input=`<div class="row">${options.map(o=>`<label class="checklist"><input type="checkbox" data-correct-multi="${i}" value="${esc(o)}" ${(field.correct||[]).includes(o)?'checked':''}>${esc(o)}</label>`).join('')}</div>`;
  else if(field.type==='choice'||field.type==='scale') input=`<select data-correct="${i}" aria-label="Resposta correta da pergunta ${i+1}"><option value="">Sem resposta correta</option>${options.map(o=>`<option ${o===field.correct?'selected':''}>${esc(o)}</option>`).join('')}</select>`;
  else input=`<input data-correct="${i}" type="${field.type==='number'?'number':'text'}" step="any" value="${esc(field.correct||'')}" aria-label="Resposta correta da pergunta ${i+1}" maxlength="4000">`;
  return `<div class="quiz-key"><span>Resposta correta</span>${input}<label>Pontos <input data-points="${i}" type="number" min="0" max="100" step="1" value="${field.points??1}" aria-label="Pontos da pergunta ${i+1}"></label></div>`;
}
function formEditor(root,c) {
  c.questions ??=[];c.responses ??=[];
  c.fields ??=c.questions.map(()=>({type:'text',required:true,options:[]}));
  const fieldTypes={text:'Texto',email:'E-mail',number:'Número',date:'Data',choice:'Escolha única',multiple:'Múltipla seleção',scale:'Escala'};
  const grade=r=>typeof r.total==='number'&&r.total>0?`<p><strong>Nota: ${r.score} de ${r.total}</strong></p>`:'';
  root.innerHTML=`<div class="toolbar"><button id="add-question">＋ Pergunta de texto</button><button id="form-table">Respostas → Tabela</button><button id="form-sheet">Respostas → Planilha</button><button id="form-csv">Baixar respostas CSV</button>${current.role==='owner'?'<button id="form-publish">Link de coleta</button>':''}<label class="checklist"><input type="checkbox" id="form-quiz" ${c.quiz?'checked':''}>Modo quiz (nota automática)</label><span>${c.responses.length} respostas</span></div><h3>Perguntas</h3>${c.questions.map((q,i)=>`<article class="card"><div class="row"><input data-question="${i}" value="${esc(q)}" aria-label="Pergunta ${i+1}" maxlength="300"><select data-field-type="${i}" aria-label="Tipo da pergunta ${i+1}">${Object.entries(fieldTypes).map(([type,label])=>`<option value="${type}" ${c.fields[i].type===type?'selected':''}>${label}</option>`).join('')}</select><button data-remove-question="${i}">Excluir</button></div><label class="checklist"><input type="checkbox" data-field-required="${i}" ${c.fields[i].required?'checked':''}>Obrigatória</label>${['choice','multiple'].includes(c.fields[i].type)?`<label class="field">Opções, uma por linha<textarea data-field-options="${i}" aria-label="Opções da pergunta ${i+1}">${esc(c.fields[i].options.join('\n'))}</textarea></label>`:''}${c.fields[i].type==='scale'?`<label class="field">Escala de 1 até<select data-field-max="${i}" aria-label="Máximo da escala da pergunta ${i+1}">${[2,3,4,5,6,7,8,9,10].map(n=>`<option ${n===(c.fields[i].max||5)?'selected':''}>${n}</option>`).join('')}</select></label>`:''}${c.quiz?correctAnswerField(c.fields[i],i):''}</article>`).join('')}<hr><h3>Responder neste espaço</h3><form id="respond-form">${c.questions.map((q,i)=>answerField(q,c.fields[i],i)).join('')}<button class="primary" ${c.questions.length?'':'disabled'}>Registrar resposta</button></form><h3 class="section-head">Respostas registradas</h3>${c.responses.map(r=>`<div class="card"><small>${date(r.at)}</small>${grade(r)}${r.answers.map((a,i)=>`<p>${esc(r.questions?.[i]||'Pergunta '+(i+1))}: ${esc(a)}</p>`).join('')}</div>`).join('')}`;
  root.querySelectorAll('[data-question]').forEach(n=>n.oninput=()=>{const i=+n.dataset.question;c.questions[i]=n.value;const group=root.querySelector(`[data-answer="${i}"] legend`);if(group)group.textContent=n.value+(c.fields[i].required?' *':'');else{const label=root.querySelector(`[name="q${i}"]`).closest('label');label.firstChild.textContent=n.value+(c.fields[i].required?' *':'');}setDirty();});
  root.querySelectorAll('[data-remove-question]').forEach(n=>n.onclick=()=>{c.questions.splice(+n.dataset.removeQuestion,1);c.fields.splice(+n.dataset.removeQuestion,1);setDirty();formEditor(root,c);});
  root.querySelectorAll('[data-field-type]').forEach(n=>n.onchange=()=>{const f=c.fields[+n.dataset.fieldType];f.type=n.value;delete f.correct;if(n.value==='multiple')f.options=f.options.filter(o=>!o.includes(';'));setDirty();formEditor(root,c);});
  root.querySelectorAll('[data-field-required]').forEach(n=>n.onchange=()=>{c.fields[+n.dataset.fieldRequired].required=n.checked;setDirty();formEditor(root,c);});
  root.querySelectorAll('[data-field-options]').forEach(n=>n.onchange=()=>{const f=c.fields[+n.dataset.fieldOptions];const options=[...new Set(n.value.split('\n').map(s=>s.trim()).filter(Boolean))];if(options.length>50)return notify('Até 50 opções.');if(f.type==='multiple'&&options.some(o=>o.includes(';')))return notify('Em múltipla seleção, as opções não podem conter ponto e vírgula.');f.options=options;if(Array.isArray(f.correct))f.correct=f.correct.filter(o=>options.includes(o));else if(f.correct&&!options.includes(f.correct))delete f.correct;setDirty();formEditor(root,c);});
  root.querySelectorAll('[data-field-max]').forEach(n=>n.onchange=()=>{const f=c.fields[+n.dataset.fieldMax];f.max=+n.value;if(f.correct&&+f.correct>f.max)delete f.correct;setDirty();formEditor(root,c);});
  root.querySelectorAll('[data-correct]').forEach(n=>n.onchange=()=>{const f=c.fields[+n.dataset.correct];if(n.value)f.correct=n.value;else delete f.correct;setDirty();});
  root.querySelectorAll('[data-correct-multi]').forEach(n=>n.onchange=()=>{const i=+n.dataset.correctMulti;c.fields[i].correct=[...root.querySelectorAll(`[data-correct-multi="${i}"]:checked`)].map(x=>x.value);setDirty();});
  root.querySelectorAll('[data-points]').forEach(n=>n.onchange=()=>{const v=Math.round(Number(n.value));if(!(v>=0&&v<=100)){n.value=c.fields[+n.dataset.points].points??1;return notify('Use de 0 a 100 pontos.');}c.fields[+n.dataset.points].points=v;setDirty();});
  bind('form-quiz',e=>{c.quiz=e.target.checked;setDirty();formEditor(root,c);},'change');
  bind('add-question',()=>{if(c.questions.length>=100)return notify('Limite de 100 perguntas.');c.questions.push('Nova pergunta');c.fields.push({type:'text',required:true,options:[]});setDirty();formEditor(root,c);});
  bind('respond-form',e=>{e.preventDefault();if(c.responses.length>=1000)return notify('Limite de 1000 respostas.');const answers=collectAnswers(e.target,c.fields);for(let i=0;i<answers.length;i++){const error=answerError(answers[i],c.fields[i]);if(error){notify('Pergunta '+(i+1)+': '+error);return;}}const response={at:Date.now(),questions:[...c.questions],answers};if(c.quiz){const g=scoreResponse(c.fields,answers);if(g.total){Object.assign(response,g);notify(`Nota: ${g.score} de ${g.total}.`);}}c.responses.push(response);setDirty();formEditor(root,c);},'submit');
  const responseRows=()=>responseTable(c,date);
  bind('form-csv',()=>{const data=responseRows();download(current.title+'-respostas.csv',toCSV(safeCsv([data.columns,...data.rows])),'text/csv');});
  bind('form-table',()=>{if(!c.responses.length)return notify('Registre uma resposta primeiro.');const data=responseRows();if(data.columns.length>26||data.rows.length>200)return notify('A tabela aceita 26 campos e 200 registros. Use Respostas → Planilha ou Baixar respostas CSV para levar todos os dados.');convert('table',data,' — Respostas');});
  bind('form-sheet',()=>{try{if(!c.responses.length)return notify('Registre uma resposta primeiro.');const data=responseRows();convert('sheet',{workbook:recordsWorkbook(data.columns,data.rows)},' — Respostas');}catch(e){notify(e.message);}});
  bind('form-publish',publicationDialog);
}
async function publicationDialog() {
  if(dirty){await save();if(dirty)return;}
  try {
    const state=await api('/api/items/'+current.id+'/publication');
    const url=state.token?location.origin+'/?form='+state.token:'';
    showDialog(`<h2>Coleta de respostas</h2><p>Quem receber o link poderá ver as perguntas e responder sem criar conta. As respostas ficam disponíveis apenas a quem tem acesso ao arquivo.</p>${url?`<label class="field">Link público<input id="public-link" value="${esc(url)}" readonly></label><button id="copy-form-link">Copiar link</button><button id="toggle-publication" class="danger">Desativar link</button>`:'<p>O formulário está fechado para respostas públicas.</p><button id="toggle-publication" class="primary">Ativar link público</button>'}<p id="publication-error" class="error" role="alert"></p><button id="close-publication">Fechar</button>`,()=>{
      bind('close-publication',closeDialog);
      bind('copy-form-link',async()=>{try{await navigator.clipboard.writeText(url);notify('Link copiado.');}catch{document.querySelector('#public-link').select();notify('Selecione e copie o link.');}});
      bind('toggle-publication',async()=>{try{await api('/api/items/'+current.id+'/publication',{enabled:!state.token});closeDialog();await publicationDialog();}catch(e){document.querySelector('#publication-error').textContent=e.message;}});
    });
  } catch(e){notify(e.message);}
}
async function publicForm(token) {
  const data=await api('/api/forms/'+encodeURIComponent(token));
  app.innerHTML=`<main class="public-form"><div class="brand"><span class="brand-name">DRAP <span>office</span></span></div><h1>${esc(data.title)}</h1><form id="public-response">${data.questions.map((q,i)=>answerField(q,data.fields[i],i)).join('')}<p id="public-response-error" class="error" role="alert"></p><button class="primary">Enviar resposta</button></form></main>`;
  bind('public-response',async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;const answers=collectAnswers(e.target,data.fields);const invalid=answers.map((a,i)=>answerError(a,data.fields[i])).findIndex(Boolean);if(invalid>=0){document.querySelector('#public-response-error').textContent='Pergunta '+(invalid+1)+': '+answerError(answers[invalid],data.fields[invalid]);button.disabled=false;return;}try{const result=await api('/api/forms/'+encodeURIComponent(token),{answers,schema_id:data.schema_id});e.target.innerHTML='<h2>Resposta enviada</h2><p>Sua resposta foi registrada. Obrigado!</p>'+(result.total?`<p id="quiz-score"><strong>Sua nota: ${result.score} de ${result.total}</strong></p>`:'');}catch(err){document.querySelector('#public-response-error').textContent=err.message;button.disabled=false;}},'submit');
}
const tableStates=new Map();
function tableEditor(root, c) {
  if(!tableStates.has(current.id))tableStates.set(current.id,{filter:"",sort:null,direction:1});
  const state=tableStates.get(current.id);
  c.columns ??= ["Nome", "Descrição"];
  c.rows ??= [];
  c.types ??= c.columns.map(()=>"text");
  root.innerHTML = `<div class="toolbar"><button id="table-row">＋ Registro</button><button id="table-column">＋ Campo</button><button id="table-deduplicate">Remover duplicatas</button><button id="table-import">Importar CSV</button><button id="table-csv">Exportar CSV</button><button id="table-sheet">Abrir como planilha ↗</button><input id="table-filter" placeholder="Filtrar registros…" aria-label="Filtrar registros" value="${esc(state.filter)}"></div><div class="grid-wrap"><table class="sheet"><thead><tr>${c.columns.map((v, i) => `<th><input data-column="${i}" aria-label="Nome do campo ${i + 1}" value="${esc(v)}"><select data-column-type="${i}" aria-label="Tipo do campo ${i+1}">${Object.entries({text:"Texto",number:"Número",date:"Data",email:"E-mail"}).map(([type,label])=>`<option value="${type}" ${c.types[i]===type?"selected":""}>${label}</option>`).join("")}</select><button data-sort-column="${i}" aria-label="Ordenar por ${esc(v)}">${state.sort===i&&state.direction===-1?"Z → A":"A → Z"}</button><button data-drop-column="${i}" aria-label="Excluir campo ${esc(v)}" ${c.columns.length===1?"disabled":""}>×</button></th>`).join("")}<th>Ações</th></tr></thead><tbody>${c.rows.map((row, r) => `<tr data-table-row="${r}">${c.columns.map((_, col) => `<td><input type="${c.types[col]}" ${c.types[col]==="number"?'step="any"':""} data-table-r="${r}" data-table-c="${col}" aria-label="Registro ${r + 1}, ${esc(c.columns[col])}" value="${esc(row[col] || "")}"></td>`).join("")}<td><button data-delete-row="${r}" class="danger">×</button></td></tr>`).join("")}</tbody></table></div>`;
  const validValue=(value,type)=>!value || type==='text' || (type==='number' && Number.isFinite(Number(value))) || (type==='date' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value))) || (type==='email' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
  root.querySelectorAll('[data-column-type]').forEach(n=>n.onchange=()=>{const index=+n.dataset.columnType;if(c.rows.some(r=>!validValue(r[index],n.value))){n.value=c.types[index];return notify('Existem valores incompatíveis com esse tipo. Corrija os registros primeiro.');}c.types[index]=n.value;setDirty();tableEditor(root,c);});
  root.querySelectorAll('[data-sort-column]').forEach(n=>n.onclick=()=>{const index=+n.dataset.sortColumn;state.direction=state.sort===index?-state.direction:1;state.sort=index;c.rows.sort((a,b)=>(c.types[index]==='number'?Number(a[index])-Number(b[index]):a[index].localeCompare(b[index],'pt-BR',{numeric:true}))*state.direction);setDirty();tableEditor(root,c);});
  root.querySelectorAll('[data-drop-column]').forEach(n=>n.onclick=async()=>{if(c.columns.length<2||!(await askConfirm('Excluir campo?', 'O campo e seus valores serão removidos.')))return;const index=+n.dataset.dropColumn;c.columns.splice(index,1);c.types.splice(index,1);c.rows.forEach(r=>r.splice(index,1));setDirty();tableEditor(root,c);});
  bind('table-deduplicate',()=>{const seen=new Set();c.rows=c.rows.filter(r=>{const key=JSON.stringify(r);if(seen.has(key))return false;seen.add(key);return true;});setDirty();tableEditor(root,c);});
  root.querySelectorAll("[data-column]").forEach(
    (n) =>
      (n.oninput = () => {
        c.columns[+n.dataset.column] = n.value;
        setDirty();
      }),
  );
  root.querySelectorAll("[data-table-r]").forEach(
    (n) =>
      (n.oninput = () => {
        c.rows[+n.dataset.tableR][+n.dataset.tableC] = n.value;
        setDirty();
      }),
  );
  root.querySelectorAll("[data-delete-row]").forEach(
    (n) =>
      (n.onclick = () => {
        c.rows.splice(+n.dataset.deleteRow, 1);
        setDirty();
        tableEditor(root, c);
      }),
  );
  bind("table-row", () => {
    if (c.rows.length >= 200)
      return notify("Limite de 200 registros nesta versão.");
    c.rows.push(Array(c.columns.length).fill(""));
    setDirty();
    tableEditor(root, c);
  });
  bind("table-column", () => {
    if (c.columns.length >= 26) return notify("Limite de 26 campos.");
    c.columns.push("Novo campo");
    c.types.push("text");
    c.rows.forEach((r) => r.push(""));
    setDirty();
    tableEditor(root, c);
  });
  bind("table-csv", () =>
    download(current.title + ".csv", toCSV(safeCsv([c.columns, ...c.rows.map(row=>row.map((v,i)=>c.types[i]==="number"&&v!==""?Number(v):v))])), "text/csv"),
  );
  const filter=()=>root.querySelectorAll('[data-table-row]').forEach(n=>n.hidden=!c.rows[+n.dataset.tableRow].join(' ').toLowerCase().includes(state.filter.toLowerCase()));
  bind('table-filter',e=>{state.filter=e.target.value;filter();},'input');filter();
  bind('table-import',()=>pickFile('.csv',text=>{try{const parsed=parseCSV(text,{maxRows:201,maxCols:26,minCols:1});const columns=parsed[0],rows=parsed.slice(1);if(!columns?.length||!rows.length)throw Error('Use uma linha de cabeçalhos e pelo menos um registro.');if(c.rows.length+rows.length>200)throw Error('A tabela aceita até 200 registros.');if(c.rows.length&&JSON.stringify(columns)!==JSON.stringify(c.columns))throw Error('Os cabeçalhos do CSV precisam corresponder aos campos da tabela.');const types=c.rows.length?c.types:columns.map(()=> 'text');if(rows.some(r=>r.length!==columns.length||r.some((value,i)=>!validValue(value,types[i]))))throw Error('O CSV contém linhas ou tipos incompatíveis.');c.columns=columns;c.types=types;c.rows.push(...rows);setDirty();tableEditor(root,c);notify(rows.length+' registros importados.');}catch(e){notify(e.message);}}));
  bind("table-sheet", () =>
    convert("sheet", { workbook: recordsWorkbook(c.columns,c.rows,c.types) }, " — Planilha"),
  );
}
function diagramEditor(root,c) {
  c.nodes ??=[];
  c.positions ??=c.nodes.map((_,i)=>({x:35+(i%5)*190,y:35+Math.floor(i/5)*90}));
  c.edges ??=c.nodes.slice(1).map((_,i)=>({from:i,to:i+1}));
  const svgContent=()=>`<defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#4b5320"/></marker></defs>${c.edges.map((e,i)=>{const a=c.positions[e.from],b=c.positions[e.to];return `<line data-edge-line="${i}" x1="${a.x+80}" y1="${a.y+30}" x2="${b.x+80}" y2="${b.y+30}" stroke="#4b5320" stroke-width="2" marker-end="url(#flow-arrow)"/>`;}).join('')}${c.nodes.map((n,i)=>`<g class="node" data-drag-node="${i}" transform="translate(${c.positions[i].x},${c.positions[i].y})" tabindex="0" role="button" aria-label="Mover etapa ${esc(n)}"><rect width="160" height="60" rx="10" fill="#f2f4e9" stroke="#4b5320" stroke-width="2"/><text x="80" y="35" text-anchor="middle" fill="#283215" font-size="14">${esc(n.slice(0,20))}</text></g>`).join('')}`;
  root.innerHTML=`<div class="toolbar"><button id="diagram-svg">Baixar SVG</button><button id="diagram-layout">Organizar etapas</button></div><p class="muted">Arraste as etapas ou use as setas do teclado para posicioná-las. Crie conexões entre quaisquer etapas.</p><div class="diagram-canvas"><svg id="flow-canvas" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 ${Math.max(600,...c.positions.map(p=>p.y+100))}" role="img" aria-label="Diagrama de processos">${svgContent()}</svg></div><form id="connect-nodes" class="toolbar"><label>Origem<select name="from">${c.nodes.map((n,i)=>`<option value="${i}">${esc(n)}</option>`).join('')}</select></label><label>Destino<select name="to">${c.nodes.map((n,i)=>`<option value="${i}" ${i===1?'selected':''}>${esc(n)}</option>`).join('')}</select></label><button ${c.nodes.length<2?'disabled':''}>Conectar etapas</button></form><details><summary>Conexões (${c.edges.length})</summary>${c.edges.map((e,i)=>`<div class="row"><span>${esc(c.nodes[e.from])} → ${esc(c.nodes[e.to])}</span><button data-remove-edge="${i}">Remover conexão</button></div>`).join('')}</details><div class="stack">${c.nodes.map((n,i)=>`<div class="row"><input data-node="${i}" value="${esc(n)}" aria-label="Etapa ${i+1}"><button data-delete-node="${i}">Excluir</button></div>`).join('')}<button id="add-node">＋ Etapa</button></div>`;
  root.querySelectorAll('[data-node]').forEach(n=>n.onchange=()=>{c.nodes[+n.dataset.node]=n.value;setDirty();diagramEditor(root,c);});
  root.querySelectorAll('[data-delete-node]').forEach(n=>n.onclick=()=>{const i=+n.dataset.deleteNode;c.nodes.splice(i,1);c.positions.splice(i,1);c.edges=c.edges.filter(e=>e.from!==i&&e.to!==i).map(e=>({from:e.from>i?e.from-1:e.from,to:e.to>i?e.to-1:e.to}));setDirty();diagramEditor(root,c);});
  root.querySelectorAll('[data-remove-edge]').forEach(n=>n.onclick=()=>{c.edges.splice(+n.dataset.removeEdge,1);setDirty();diagramEditor(root,c);});
  bind('add-node',()=>{if(c.nodes.length>=100)return notify('Limite de 100 etapas.');const i=c.nodes.length;c.nodes.push('Nova etapa');c.positions.push({x:35+(i%5)*190,y:Math.min(1900,35+Math.floor(i/5)*90)});setDirty();diagramEditor(root,c);});
  bind('connect-nodes',e=>{e.preventDefault();const data=new FormData(e.target),from=Number(data.get('from')),to=Number(data.get('to'));if(from===to||c.edges.some(e=>e.from===from&&e.to===to))return notify('Escolha etapas diferentes e uma conexão nova.');if(c.edges.length>=300)return notify('Limite de 300 conexões.');c.edges.push({from,to});setDirty();diagramEditor(root,c);},'submit');
  bind('diagram-layout',()=>{c.positions=c.nodes.map((_,i)=>({x:35+(i%5)*190,y:Math.min(1900,35+Math.floor(i/5)*90)}));setDirty();diagramEditor(root,c);});
  bind('diagram-svg',()=>download(current.title+'.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 '+Math.max(600,...c.positions.map(p=>p.y+100))+'">'+svgContent()+'</svg>','image/svg+xml'));
  const canvas=root.querySelector('#flow-canvas');
  const redrawPositions=()=>{
    root.querySelectorAll('[data-drag-node]').forEach(n=>{const p=c.positions[+n.dataset.dragNode];n.setAttribute('transform',`translate(${p.x},${p.y})`);});
    root.querySelectorAll('[data-edge-line]').forEach(n=>{const e=c.edges[+n.dataset.edgeLine],a=c.positions[e.from],b=c.positions[e.to];for(const[k,v]of Object.entries({x1:a.x+80,y1:a.y+30,x2:b.x+80,y2:b.y+30}))n.setAttribute(k,v);});
  };
  root.querySelectorAll('[data-drag-node]').forEach(n=>{
    n.onkeydown=e=>{if(current.role==='read'||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const p=c.positions[+n.dataset.dragNode],step=e.shiftKey?50:10;p.x=Math.max(0,Math.min(840,p.x+(e.key==='ArrowLeft'?-step:e.key==='ArrowRight'?step:0)));p.y=Math.max(0,Math.min(1900,p.y+(e.key==='ArrowUp'?-step:e.key==='ArrowDown'?step:0)));setDirty();redrawPositions();canvas.setAttribute("viewBox","0 0 1000 "+Math.max(600,...c.positions.map(p=>p.y+100)));};
    n.onpointerdown=e=>{if(current.role==='read')return;e.preventDefault();n.setPointerCapture(e.pointerId);const point=canvas.createSVGPoint();const move=ev=>{point.x=ev.clientX;point.y=ev.clientY;const local=point.matrixTransform(canvas.getScreenCTM().inverse());c.positions[+n.dataset.dragNode]={x:Math.max(0,Math.min(840,local.x-80)),y:Math.max(0,Math.min(1900,local.y-30))};redrawPositions();setDirty();};n.onpointermove=move;n.onpointerup=()=>{n.onpointermove=null;n.releasePointerCapture(e.pointerId);canvas.setAttribute("viewBox","0 0 1000 "+Math.max(600,...c.positions.map(p=>p.y+100)));};n.onpointercancel=()=>{n.onpointermove=null;};};
  });
}
function portalEditor(root, c) {
  c.links ??= [];
  c.text ??= "";
  const available = items.filter((i) => i.id !== current.id && !i.deleted);
  root.innerHTML = `<label class="field">Boas-vindas<textarea id="portal-text" rows="4">${esc(c.text)}</textarea></label><div class="preview">${markdown(c.text)}</div><form id="add-link" class="toolbar"><select name="id" aria-label="Arquivo para vincular">${available.map((i) => `<option value="${i.id}">${esc(i.title)}</option>`).join("")}</select><button ${available.length ? "" : "disabled"}>Vincular arquivo</button></form><p class="muted">Os links respeitam as permissões de cada arquivo. Compartilhar o portal não compartilha automaticamente os arquivos.</p>${c.links
    .map((id, index) => {
      const i = items.find((i) => i.id === id && !i.deleted);
      return `<div class="row"><button class="link-card" data-link="${id}" ${i?"":"disabled"}>${esc(i?.title || "Arquivo indisponível ou sem acesso")} ↗</button><button data-remove-link="${index}">Remover</button></div>`;
    })
    .join("")}`;
  bind(
    "portal-text",
    (e) => {
      c.text = e.target.value;
      root.querySelector(".preview").innerHTML = markdown(c.text);
      setDirty();
    },
    "input",
  );
  bind(
    "add-link",
    (e) => {
      e.preventDefault();
      const id = new FormData(e.target).get("id");
      if(c.links.length>=100)return notify("Limite de 100 links por portal.");
      if (id && !c.links.includes(id)) c.links.push(id);
      setDirty();
      portalEditor(root, c);
    },
    "submit",
  );
  root
    .querySelectorAll("[data-link]")
    .forEach((n) => (n.onclick = () => openItem(n.dataset.link)));
  root.querySelectorAll("[data-remove-link]").forEach(
    (n) =>
      (n.onclick = () => {
        c.links.splice(+n.dataset.removeLink, 1);
        setDirty();
        portalEditor(root, c);
      }),
  );
}
async function convert(kind, content, suffix) {
  if (dirty) {
    await save();
    if (dirty) return;
  }
  try {
    if (kind === "slides" && !content.slides.length)
      return notify("Escreva o conteúdo antes de criar os slides.");
    const i = await api("/api/items", {
      kind,
      title: (current.title + suffix).slice(0, 200),
      content,
    });
    dirty = false;
    await refresh();
    await openItem(i.id);
    notify("Novo arquivo criado. O original foi preservado.");
  } catch (e) {
    notify(e.message);
  }
}
async function historyDialog() {
  try {
    const versions = await allPages("/api/items/" + current.id + "/history");
    showDialog(
      `<h2>Histórico de versões</h2><p class="muted">Restaurar cria uma nova versão; o histórico anterior é preservado.</p><div class="stack">${versions.map((v) => `<div class="row between history-row"><span>v${v.version} · ${esc(v.title)}<br><small>${date(v.updated)}</small></span><button data-version="${v.version}" ${current.role === "read" ? "disabled" : ""}>Restaurar</button></div>`).join("")}</div><button id="close-history">Fechar</button>`,
      () => {
        bind("close-history", closeDialog);
        modal.querySelectorAll("[data-version]").forEach(
          (n) =>
            (n.onclick = () => {
              const v = versions.find((v) => v.version === +n.dataset.version);
              current.content = structuredClone(v.content);
              current.title = v.title;
              setDirty();
              closeDialog();
              editor();
              notify(
                "Versão carregada como rascunho. Clique em Salvar para confirmar.",
              );
            }),
        );
      },
    );
  } catch (e) {
    notify(e.message);
  }
}
async function shareDialog() {
  let shares=[];
  try { shares=(await api('/api/items/'+current.id+'/shares')).items; }
  catch(e) { return notify(e.message); }
  showDialog(
    `<h2>Compartilhar arquivo</h2><div class="stack">${shares.map(s => `<div class="card"><strong>${esc(s.name)}</strong> · ${esc(s.email)}<br><span class="muted">${s.role === "edit" ? "Pode editar" : "Somente leitura"}</span></div>`).join("") || "<p>Nenhum acesso compartilhado.</p>"}</div><p class="muted">A pessoa precisa ter uma conta nesta plataforma. Compartilhamento por arquivo, com controle de acesso.</p><form id="share-form"><label class="field">E-mail<input name="email" type="email" required></label><label class="field">Permissão<select name="role"><option value="read">Somente leitura</option><option value="edit">Pode editar</option><option value="remove">Revogar acesso</option></select></label><p id="share-error" class="error" role="alert"></p><div class="row"><button class="primary">Aplicar</button><button id="cancel-share" type="button">Cancelar</button></div></form>`,
    () => {
      bind("cancel-share", closeDialog);
      bind(
        "share-form",
        async (e) => {
          e.preventDefault();
          try {
            await api(
              "/api/items/" + current.id + "/share",
              Object.fromEntries(new FormData(e.target)),
            );
            closeDialog();
            notify("Permissão atualizada.");
          } catch (err) {
            document.querySelector("#share-error").textContent = err.message;
          }
        },
        "submit",
      );
    },
  );
}
function pickFile(accept, callback, maxBytes=5_000_000) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = accept;
  input.onchange = async () => {
    try {
      if (input.files[0].size > maxBytes)
        throw Error(`Limite de importação: ${maxBytes/1_000_000} MB.`);
      await callback(await input.files[0].text());
    } catch (e) {
      notify(e.message);
    }
  };
  input.click();
}
function validImport(item) {
  const c = item.content;
  if (!TYPES[item.kind] || !c || typeof c !== "object" || Array.isArray(c))
    return false;
  const str = (v) => typeof v === "string";
  const matrix = (v) =>
    Array.isArray(v) &&
    v.length <= 200 &&
    v.every((r) => Array.isArray(r) && r.length <= 26 && r.every(str));
  switch (item.kind) {
    case "document":
    case "note":
      return str(c.text);
    case "sheet":
      if(c.workbook) {
        const w=c.workbook;
        return typeof w==='object' && !Array.isArray(w) && str(w.id)
          && Array.isArray(w.sheetOrder) && w.sheetOrder.length>0 && w.sheetOrder.length<=20
          && w.sheets && typeof w.sheets==='object' && w.sheetOrder.every(id=>str(id)&&w.sheets[id]);
      }
      return (
        matrix(c.cells) &&
        c.cells.length > 0 &&
        c.cells[0].length > 0 &&
        c.cells.every((r) => r.length === c.cells[0].length)
      );
    case "slides":
      return (
        Array.isArray(c.slides) &&
        c.slides.length > 0 &&
        c.slides.length <= 100 &&
        c.slides.every((s) => s && str(s.title) && str(s.body) && str(s.notes))
      );
    case "board":
      return (
        Array.isArray(c.tasks) &&
        c.tasks.every(
          (t) =>
            t &&
            str(t.title) &&
            ["A fazer", "Em andamento", "Concluído"].includes(t.status) &&
            str(t.due),
        )
      );
    case "calendar":
      return (
        Array.isArray(c.events) &&
        c.events.every(
          (e) =>
            e &&
            str(e.title) &&
            Number.isFinite(Date.parse(e.start)) &&
            Number.isFinite(Date.parse(e.end)),
        )
      );
    case "form":
      return (
        Array.isArray(c.questions) &&
        c.questions.every(str) &&
        Array.isArray(c.responses) &&
        c.responses.every(
          (r) =>
            r &&
            Number.isFinite(r.at) &&
            Array.isArray(r.answers) &&
            r.answers.every(str) &&
            (!r.questions ||
              (Array.isArray(r.questions) && r.questions.every(str))),
        )
      );
    case "table":
      return (
        Array.isArray(c.columns) &&
        c.columns.length > 0 &&
        c.columns.length <= 26 &&
        c.columns.every(str) &&
        matrix(c.rows)
      );
    case "diagram":
      return Array.isArray(c.nodes) && c.nodes.every(str);
    case "portal":
      return str(c.text) && Array.isArray(c.links) && c.links.every(str);
  }
}
function importBackup() {
  if (dirty) return notify("Salve ou exporte o rascunho antes de importar arquivos.");
  pickFile(".json", async (text) => {
    const backup = JSON.parse(text);
    if (
      !["nexo/1", "drap-office/1"].includes(backup.format) ||
      !Array.isArray(backup.items) ||
      backup.items.length > 100
    )
      throw Error(
        "Arquivo DRAP office inválido. Limite de 100 arquivos por importação.",
      );
    if (
      backup.items.some(
        (i) => !i || !validImport(i) || typeof i.title !== "string",
      )
    )
      throw Error("Conteúdo incompatível. Nenhum arquivo foi importado.");
    let count = 0;
    try {
      for (const i of backup.items) {
        await api("/api/items", {
          title: i.title,
          kind: i.kind,
          content: i.content,
        });
        count++;
      }
    } finally {
      await refresh();
      render();
      notify(
        `${count} arquivos importados como novas cópias privadas. Links de portais precisam ser refeitos.`,
      );
    }
  },64_000_000);
}
function analytics() {
  const active = items.filter((i) => !i.deleted),
    tasks = active
      .filter((i) => i.kind === "board")
      .flatMap((i) => i.content.tasks || []),
    done = tasks.filter((t) => t.status === "Concluído").length,
    responses = active
      .filter((i) => i.kind === "form")
      .reduce((s, i) => s + (i.content.responses || []).length, 0);
  shell(
    `<p class="eyebrow">DADOS DO SEU ESPAÇO</p><h1>Uma visão do que acontece.</h1><p class="muted">Indicadores calculados a partir dos arquivos aos quais você tem acesso.</p><div class="metrics">${[
      ["Arquivos ativos", active.length],
      ["Tarefas concluídas", `${done}/${tasks.length}`],
      [
        "Conclusão de tarefas",
        `${tasks.length ? Math.round((done / tasks.length) * 100) : 0}%`,
      ],
      ["Respostas coletadas", responses],
    ]
      .map(
        ([n, v]) =>
          `<div class="metric"><small>${n}</small><strong>${v}</strong></div>`,
      )
      .join(
        "",
      )}</div><section class="editor"><h2>Arquivos por ferramenta</h2><div class="stack">${Object.entries(
      TYPES,
    )
      .map(
        ([k, t]) =>
          `<div class="row between"><span>${t.name}</span><strong>${active.filter((i) => i.kind === k).length}</strong></div>`,
      )
      .join("")}</div></section>`,
  );
}
function automation() {
  shell(
    `<p class="eyebrow">CONECTE SEU TRABALHO</p><h1>As ideias continuam em outra ferramenta.</h1><p class="muted">Conversões locais executadas sob demanda nos editores. Arquivos de origem são preservados.</p><div class="coverage">${[
      [
        "Documentos → Apresentações",
        "Separe o texto por títulos e crie slides para apresentar.",
      ],
      [
        "Planilhas → Documentos",
        "Transforme os dados da planilha em um relatório de texto.",
      ],
      [
        "Formulários → Banco de dados",
        "Organize as respostas em uma tabela de registros.",
      ],
      [
        "Banco de dados → Planilhas",
        "Leve os registros para calcular e visualizar.",
      ],
    ]
      .map(
        ([t, d]) =>
          `<article class="card"><span class="badge">Disponível no editor</span><h3 class="section-head">${t}</h3><p>${d}</p></article>`,
      )
      .join(
        "",
      )}</div><h2 class="section-head">Serviços externos</h2><div class="card"><h3>E-mail, reuniões, armazenamento remoto e IA</h3><p class="muted">Não conectados. Nenhuma mensagem ou arquivo é enviado para terceiros. As próximas etapas exigem seleção dos provedores, OAuth, contratos de integração e testes. Não são simulados como serviços ativos.</p></div>`,
  );
}
function coverage() {
  shell(
    `<p class="eyebrow">ESCOPO TRANSPARENTE</p><h1>Uma plataforma em evolução.</h1><p class="muted">A lista enviada define a direção da suíte. Esta versão implementa um núcleo próprio, sem equivalência completa com Microsoft 365.</p><div class="coverage">${[
      [
        "Documentos e notas",
        "Disponível",
        "Edição visual, títulos, negrito/itálico, listas, tabelas editáveis, links, imagens, checklist, desfazer/refazer, busca/substituição, Markdown, DOCX e impressão.",
        "Pendentes: paginação profissional, bibliografia, mala direta e revisão com alterações rastreadas.",
      ],
      [
        "Planilhas",
        "Disponível",
        "Editor Univer: múltiplas abas, intervalos, fórmulas, desfazer/refazer, formatação, mesclagem, ordenação, filtros, validação, formatação condicional, gráficos de colunas/linhas/pizza, tabelas dinâmicas, CSV e XLSX.",
        "Pendentes: gráficos avançados, pivôs nativos no XLSX, múltiplos níveis de agrupamento, Solver, DAX, Power Query, macros e equivalência de todas as funções Excel.",
      ],
      [
        "Apresentações",
        "Disponível",
        "Slides, imagens, caixas de texto, formas, arrastar/redimensionar, camadas, desfazer/refazer, temas, reordenação, notas, apresentação por teclado e PPTX com imagens e objetos editáveis.",
        "Pendentes: áudio/vídeo, mestre, animações, transições, recorte avançado e exportação de vídeo.",
      ],
      [
        "Projetos e agenda",
        "Disponível",
        "Kanban, cronograma (Gantt), dependências, marcos, caminho crítico e folga, responsáveis, prioridades, subtarefas, agenda, geração de repetições e arquivos ICS.",
        "Pendentes: recursos e custos, linhas de base, notificações e convites externos.",
      ],
      [
        "Formulários e tabelas",
        "Disponível",
        "Formulários tipados com múltipla seleção, escala e quizzes com nota automática (gabarito privado), coleta pública revogável, respostas persistentes; tabelas com tipos, ordenação, filtro e deduplicação.",
        "Pendentes: anexos, ramificação condicional, relacionamentos e consultas entre tabelas.",
      ],
      [
        "Diagramas e portais",
        "Disponível",
        "Canvas de etapas com arraste, teclado, conexões e SVG; portais com texto estruturado e links autorizados.",
        "Pendentes: bibliotecas BPMN, formas especializadas e publicação de intranet.",
      ],
      [
        "Arquivos e colaboração",
        "Disponível",
        "Histórico, lixeira, rascunhos locais recuperáveis, comentários, acessos listáveis e conflitos de versões.",
        "Pendentes: armazenamento binário geral, leitura e sincronização de arquivos sem internet, coautoria em tempo real e criptografia de arquivos.",
      ],
      [
        "BI e automação",
        "Parcial",
        "Indicadores reais de tarefas e arquivos; conversões manuais entre editores.",
        "Pendentes: modelagem analítica, conectores, agendamento e designer de fluxos.",
      ],
      [
        "Correio, reuniões e IA",
        "Planejado",
        "Requisitos identificados; nenhum provedor conectado.",
        "SMTP/IMAP ou APIs, OAuth, WebRTC, telefonia, OCR e IA exigem implementações dedicadas.",
      ],
      [
        "Segurança e operação",
        "Parcial",
        "Senhas scrypt, verificação em duas etapas (app autenticador e códigos de backup), recuperação por pergunta secreta, registro de atividade da conta, sessões HttpOnly, rate limit no banco, autorização por arquivo, Vercel e Neon.",
        "Pendentes: auditoria administrativa da organização, alertas e testes de carga.",
      ],
    ]
      .map(
        ([t, status, yes, no]) =>
          `<article class="card"><span class="badge">${status}</span><h3 class="section-head">${t}</h3><p>${yes}</p><p>${no}</p></article>`,
      )
      .join("")}</div>`,
  );
}
window.addEventListener("beforeunload", (e) => {
  if (dirty) {
    stashDraft();
    e.preventDefault();
    e.returnValue = "";
  }
});
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s" && current) {
    e.preventDefault();
    if (current.role !== "read") save();
  }
});
try {
  const formToken=new URLSearchParams(location.search).get('form');
  if (formToken) await publicForm(formToken);
  else { user = await api("/api/me"); await refresh(); render(); askRecoverySetup(); }
} catch (e) {
  if (e.status === 401) auth();
  else if (e.offline) {
    app.textContent =
      "Você está sem conexão. O DRAP office vai abrir automaticamente quando a internet voltar.";
    addEventListener("online", () => location.reload(), { once: true });
  } else
    app.textContent =
      "Não foi possível conectar à plataforma. Recarregue a página para tentar novamente.";
}
function connectionNotice() {
  document.body.classList.toggle("offline", !navigator.onLine);
  notify(navigator.onLine
    ? "Conexão restabelecida. Salve as alterações pendentes."
    : "Sem conexão. Você pode continuar editando; salve quando a internet voltar.");
}
addEventListener("online", connectionNotice);
addEventListener("offline", connectionNotice);
if (!navigator.onLine) document.body.classList.add("offline");
// isSecureContext covers HTTPS and localhost; the worker only caches the app shell.
if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

async function importOffice() {
  if (!(await leave())) return;
  const input = document.createElement('input');
  input.type = 'file'; input.accept = '.docx,.xlsx,.pptx,.ics';
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    if (file.size > 2500000) return notify('Limite de 2,5 MB por arquivo Office.');
    try {
      notify('Importando arquivo…');
      const data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = () => reject(Error('Não foi possível ler o arquivo.'));
        reader.readAsDataURL(file);
      });
      const result = await api('/api/import', {name: file.name, data});
      await refresh();
      await openItem(result.item.id);
      showDialog('<h2>Arquivo importado</h2>' + result.warnings.map(w => '<p>' + esc(w) + '</p>').join('') + '<button id="import-done" class="primary">Continuar edição</button>', () => bind('import-done', closeDialog));
    } catch (e) { notify(e.message); }
  };
  input.click();
}
async function exportOffice() {
  await spreadsheet?.flush();
  if (dirty) {
    await save();
    if (dirty) return;
  }
  const extension = {document:'docx',note:'docx',sheet:'xlsx',table:'xlsx',slides:'pptx',calendar:'ics'}[current.kind];
  try {
    const response = await fetch('/api/items/' + current.id + '/export?format=' + extension);
    if (!response.ok) {
      const error = await response.json();
      throw Error(error.error || 'Falha na exportação.');
    }
    download(current.title + '.' + extension, await response.blob(), response.headers.get('Content-Type'));
  } catch (e) { notify(e.message); }
}

function draftKey() { return 'drap:draft:'+user.id+':'+current.id; }
function stashDraft() {
  if (!user || !current || !dirty || current.role==='read') return;
  try { localStorage.setItem(draftKey(),JSON.stringify({title:current.title,content:current.content,version:current.version,deleted:current.deleted})); }
  catch { if(!stashDraft.warned) { notify('Não foi possível guardar o rascunho neste navegador. Salve ou exporte seu arquivo.'); stashDraft.warned=true; } }
}
async function commentsDialog() {
  const itemId=current.id;
  try {
    const comments=await allPages('/api/items/'+itemId+'/comments');
    showDialog(`<h2>Comentários</h2><div class="stack">${comments.map(c=>`<article class="card"><strong>${esc(c.author)}</strong><small> · ${date(c.created)}</small><p class="comment-text">${esc(c.body)}</p></article>`).join('') || '<p>Nenhum comentário ainda.</p>'}</div>${current.role!=='read'?'<form id="comment-form"><label class="field">Seu comentário<textarea name="body" maxlength="4000" required></textarea></label><p id="comment-error" class="error" role="alert"></p><button class="primary">Enviar comentário</button></form>':''}<button id="close-comments">Fechar</button>`,()=>{
      bind('close-comments',closeDialog);
      bind('comment-form',async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{await api('/api/items/'+itemId+'/comments',{body:new FormData(e.target).get('body')});closeDialog();await commentsDialog();}catch(err){document.querySelector('#comment-error').textContent=err.message;button.disabled=false;}},'submit');
    });
  } catch(e) {notify(e.message);}
}
