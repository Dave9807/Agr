"""Pages HTML de démonstration (aucune dépendance externe).

- `/`                     : accueil et liens utiles ;
- `/demo/inscription`     : création de compte marchand et récupération de la clé ;
- `/demo/connexion`       : ouverture d'une session marchand ;
- `/demo/espace`          : activité et réglages du compte connecté ;
- `/demo/boutique`        : boutique fictive qui crée une demande de paiement ;
- `/demo/widget`          : widget simulé (confirmation / refus du client) ;
- résultat du paiement    : état final ou en attente après décision ;
- `/demo/numeros-de-test` : tableau public des numéros de test.

Le parcours reproduit celui d'un vrai agrégateur : la boutique (serveur
marchand) crée le paiement avec sa clé secrète, puis le client agit dans le
widget avec le `decision_token` à usage unique.

Design : thème sombre « fintech » (dégradés indigo/cyan, cartes, badges),
sans aucune dépendance externe (tout est du HTML/CSS inline).
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.operators.base import INVALID_TEST_NUMBER_RESULT, TEST_SCENARIOS
from app.services import payments

router = APIRouter(tags=["Pages de démonstration"])

_STYLE = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body {
  margin: 0; padding: 0 1rem 3rem;
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.6;
  background:
    radial-gradient(1100px 520px at 85% -10%, rgba(99, 102, 241, 0.20), transparent 60%),
    radial-gradient(800px 480px at -10% -5%, rgba(34, 211, 238, 0.14), transparent 55%),
    #050b14;
  background-attachment: fixed;
  color: #e2e8f0;
}
header {
  display: flex; flex-wrap: wrap; gap: 1rem; align-items: center;
  padding: 1.1rem 0; border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  margin-bottom: 2rem;
}
header .brand { display: flex; align-items: center; gap: 0.6rem; font-size: 1.3rem; font-weight: 800; letter-spacing: -0.02em; }
header .logo {
  width: 36px; height: 36px; border-radius: 11px;
  background: linear-gradient(135deg, #6366f1, #22d3ee);
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 900; color: #fff; font-size: 1rem;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.45);
}
header .badge {
  background: #f59e0b; color: #1e293b; font-weight: 700; padding: 0.2rem 0.65rem;
  border-radius: 999px; font-size: 0.72rem; letter-spacing: 0.05em;
}
nav { display: flex; gap: 0.5rem; margin-left: auto; flex-wrap: wrap; }
nav a {
  color: #a5b4fc; text-decoration: none; font-size: 0.9rem; font-weight: 600;
  padding: 0.35rem 0.85rem; border-radius: 999px;
  border: 1px solid rgba(99, 102, 241, 0.35); background: rgba(99, 102, 241, 0.08);
}
nav a:hover { background: rgba(99, 102, 241, 0.18); text-decoration: none; }
main { max-width: 860px; margin: 0 auto; }
.card {
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.55), rgba(15, 23, 42, 0.85));
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 20px;
  padding: 1.75rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.55);
}
h1 { font-size: 1.6rem; margin: 0 0 1rem; letter-spacing: -0.02em; }
h2 { font-size: 1.25rem; margin: 0 0 0.75rem; letter-spacing: -0.01em; }
p { margin: 0 0 0.75rem; }
a { color: #818cf8; }
label { display: block; font-size: 0.85rem; margin: 0.9rem 0 0.35rem; color: #cbd5e1; font-weight: 600; }
input, select, button { font: inherit; padding: 0.7rem 0.85rem; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.28); background: #0b1220; color: #e2e8f0; width: 100%; }
input:focus, select:focus { outline: none; border-color: #818cf8; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25); }
button { background: linear-gradient(135deg, #6366f1, #22d3ee); border: none; border-radius: 12px; font-weight: 700; font-size: 0.95rem; cursor: pointer; width: auto; padding: 0.75rem 1.4rem; color: #fff; box-shadow: 0 8px 22px rgba(56, 189, 248, 0.35); transition: transform 0.12s ease, box-shadow 0.12s ease, opacity 0.12s; }
button:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(56, 189, 248, 0.45); }
button.danger { background: linear-gradient(135deg, #f43f5e, #fb7185); box-shadow: 0 8px 22px rgba(244, 63, 94, 0.35); }
button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }
.row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 1rem; }
.row button { width: auto; }
.muted { color: #94a3b8; font-size: 0.85rem; }
.status { margin-top: 1rem; font-weight: 600; }
pre { background: #0b1220; padding: 0.85rem; border-radius: 12px; overflow: auto; font-size: 0.8rem; border: 1px solid rgba(148, 163, 184, 0.12); }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.65rem 0.5rem; border-bottom: 1px solid rgba(148, 163, 184, 0.14); }
th { color: #94a3b8; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
code { background: rgba(99, 102, 241, 0.14); padding: 0.1rem 0.35rem; border-radius: 6px; font-size: 0.85em; }

/* --- Hero (accueil) --- */
.hero { text-align: center; padding: 2.5rem 0 1.75rem; }
.hero h1 { font-size: 2.4rem; letter-spacing: -0.03em; line-height: 1.15; margin: 1rem 0 0.75rem; }
.hero h1 .grad { background: linear-gradient(90deg, #818cf8, #22d3ee); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero p { color: #94a3b8; max-width: 580px; margin: 0 auto 1.75rem; font-size: 1.05rem; }
.hero-actions { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.btn { display: inline-block; text-align: center; background: linear-gradient(135deg, #6366f1, #22d3ee); color: #fff; font-weight: 700; padding: 0.8rem 1.5rem; border-radius: 12px; border: none; width: auto; cursor: pointer; box-shadow: 0 10px 26px rgba(56, 189, 248, 0.35); font-size: 0.95rem; text-decoration: none; }
.btn.secondary { background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.4); color: #c7d2fe; box-shadow: none; }
.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.feature { background: linear-gradient(180deg, rgba(30, 41, 59, 0.55), rgba(15, 23, 42, 0.85)); border: 1px solid rgba(148, 163, 184, 0.16); border-radius: 16px; padding: 1.1rem; }
.feature .icon { font-size: 1.5rem; }
.feature h3 { font-size: 0.98rem; margin: 0.5rem 0 0.25rem; }
.feature p { margin: 0; color: #94a3b8; font-size: 0.85rem; }

/* --- Widget de paiement --- */
.amount { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; background: linear-gradient(90deg, #818cf8, #22d3ee); -webkit-background-clip: text; background-clip: text; color: transparent; margin: 1rem 0 0.5rem; }
.amount-row { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
.meta { display: flex; justify-content: space-between; gap: 1rem; padding: 0.6rem 0; border-bottom: 1px dashed rgba(148, 163, 184, 0.2); font-size: 0.9rem; }
.meta:last-of-type { border-bottom: none; }
.meta .k { color: #94a3b8; }
.meta .v { font-weight: 600; text-align: right; }

/* --- Badges de statut --- */
.pill { display: inline-block; padding: 0.15rem 0.65rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.pill.ok { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }
.pill.warn { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); }
.pill.info { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.35); }
.pill.bad { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); }

footer { max-width: 820px; margin: 2rem auto 0; color: #64748b; font-size: 0.8rem; text-align: center; }

/* --- Refonte responsive : identité claire et rassurante --- */
:root {
  color-scheme: light;
  --ink: #14251f;
  --muted: #62736c;
  --line: #e4ebe6;
  --green: #087c5a;
  --green-dark: #075b43;
  --lime: #d7f36a;
  --surface: #fff;
}
body {
  padding: 0 1.25rem 3.5rem;
  color: var(--ink);
  background:
    radial-gradient(800px 460px at 90% 0%, rgba(215, 243, 106, .2), transparent 65%),
    radial-gradient(720px 460px at 0% 8%, rgba(8, 124, 90, .08), transparent 65%),
    #f6f8f5;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
header {
  position: sticky; top: 0; z-index: 5;
  max-width: 1180px; margin: 0 auto 2.25rem; padding: 1rem 0;
  background: rgba(246, 248, 245, .88);
  border-bottom-color: var(--line);
  backdrop-filter: blur(16px);
}
header .brand { color: var(--ink); letter-spacing: -.04em; }
header .logo {
  color: var(--ink);
  background: var(--lime);
  box-shadow: 0 6px 18px rgba(8, 124, 90, .12);
}
header .badge {
  color: var(--green-dark); background: #e8f4d0;
  border: 1px solid #d5e8b3;
}
nav { gap: .35rem; }
nav a {
  color: #52665d; border: 1px solid transparent; background: transparent;
  padding: .48rem .8rem; transition: background .16s ease, color .16s ease;
}
nav a:hover { color: var(--green-dark); background: #eaf2eb; }
main { max-width: 1080px; min-height: 65vh; }
.card, .feature {
  color: var(--ink); background: var(--surface); border: 1px solid var(--line);
  border-radius: 22px; box-shadow: 0 16px 42px rgba(20, 37, 31, .055);
}
.card { padding: clamp(1.25rem, 3vw, 2rem); margin-bottom: 1.25rem; }
h1, h2, h3 { color: var(--ink); }
h1 { font-size: clamp(1.65rem, 4vw, 2.2rem); letter-spacing: -.045em; }
h2 { letter-spacing: -.035em; }
a { color: var(--green); }
label { color: #334940; }
input, select {
  color: var(--ink); background: #fbfcfa; border-color: #dce5de;
  border-radius: 12px; transition: border-color .16s ease, box-shadow .16s ease;
}
input::placeholder { color: #9aa8a0; }
input:focus, select:focus {
  border-color: var(--green); box-shadow: 0 0 0 4px rgba(8, 124, 90, .1);
}
button, .btn {
  color: #fff; background: var(--green); border-radius: 12px;
  box-shadow: 0 8px 18px rgba(8, 124, 90, .16);
}
button:hover, .btn:hover {
  background: var(--green-dark); box-shadow: 0 10px 22px rgba(8, 124, 90, .2);
}
button.danger { background: #b8444b; box-shadow: 0 8px 18px rgba(184, 68, 75, .14); }
button.danger:hover { background: #96363c; }
.btn.secondary {
  color: var(--green-dark); background: #fff; border: 1px solid #cfe0d4;
  box-shadow: none;
}
.btn.secondary:hover { background: #edf5ef; }
.muted, .hero p, .feature p { color: var(--muted); }
code { color: var(--green-dark); background: #edf5ed; }
pre { color: #e7f0e9; background: #14251f; border: 0; }
th { color: #697970; }
td { border-bottom-color: var(--line); }
.hero { text-align: left; padding: 0; }
.hero h1 {
  max-width: 620px; margin: .7rem 0 1rem;
  font-size: clamp(2.25rem, 4.5vw, 3.55rem);
  line-height: 1.08; letter-spacing: -.055em;
}
.hero h1 .grad {
  background: none; color: var(--green);
  -webkit-text-fill-color: currentColor;
}
.hero p { max-width: 560px; margin: 0 0 1.4rem; font-size: 1rem; }
.hero .pill { margin-bottom: .4rem; }
.pill.warn { color: #73540a; background: #fff6d8; border-color: #f0df9e; }
.hero-actions { justify-content: flex-start; }
.hero-actions .btn { padding-inline: 1.1rem; }
.home-grid {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, .75fr);
  align-items: center; gap: clamp(2rem, 6vw, 5rem);
  min-height: 450px; padding: 1rem 0 2.5rem;
}
.home-preview {
  padding: 1.25rem; border: 1px solid #dfe7df; border-radius: 14px;
  background: #fff; box-shadow: 0 20px 55px rgba(20,37,31,.09);
}
.home-preview-head {
  display: flex; justify-content: space-between; align-items: center;
  gap: .75rem; padding-bottom: .85rem; border-bottom: 1px solid var(--line);
  color: var(--muted); font-size: .74rem;
}
.home-preview-brand { display: flex; align-items: center; gap: .55rem; color: var(--ink); font-weight: 750; }
.home-preview-mark {
  display: grid; place-items: center; width: 30px; height: 30px;
  border-radius: 7px; color: var(--ink); background: var(--lime); font-size: .72rem;
}
.home-preview-total { padding: 1.15rem 0 .85rem; }
.home-preview-total small { display: block; color: var(--muted); font-size: .74rem; }
.home-preview-total strong { display: block; margin-top: .18rem; font-size: 1.9rem; letter-spacing: -.045em; }
.home-preview-method {
  display: flex; align-items: center; gap: .65rem; margin-top: .45rem;
  padding: .65rem .7rem; border: 1px solid var(--line); border-radius: 8px;
  color: #344a3f; font-size: .82rem;
}
.home-preview-method.selected { border-color: #86b69b; background: #f2f8f2; }
.home-preview-radio { width: 14px; height: 14px; border: 1px solid #9cad9f; border-radius: 50%; }
.selected .home-preview-radio { border: 4px solid var(--green); }
.home-preview-submit {
  margin-top: .75rem; padding: .7rem; border-radius: 8px;
  color: white; background: var(--green); text-align: center;
  font-size: .82rem; font-weight: 700;
}
.home-preview-foot {
  display: flex; justify-content: space-between; gap: .75rem;
  margin-top: .75rem; color: var(--muted); font-size: .69rem;
}
.home-network-line {
  display: flex; flex-wrap: wrap; align-items: center; gap: .45rem;
  margin-top: 1.75rem; color: var(--muted); font-size: .76rem;
}
.home-network-line strong { margin-right: .25rem; color: #31443a; font-weight: 700; }
.network-name { padding: .25rem .5rem; border: 1px solid var(--line); border-radius: 5px; background: rgba(255,255,255,.55); }
.flow-section { padding: 1.1rem 0 1.5rem; border-top: 1px solid var(--line); }
.flow-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin-bottom: .5rem; }
.flow-heading h2 { margin: 0; font-size: 1rem; }
.flow-heading a { font-size: .82rem; }
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; padding: 0; list-style: none; counter-reset: steps; }
.steps li {
  position: relative; min-height: 78px; counter-increment: steps;
  padding: .65rem .9rem .65rem 0; color: #334940; font-size: .84rem;
}
.steps li::before {
  content: "0" counter(steps); position: relative; z-index: 1;
  display: grid; width: 25px; height: 25px; place-items: center;
  margin: 0 0 .5rem; border: 1px solid #cddbd0; border-radius: 50%;
  color: var(--green); background: #f6f8f5; font-size: .68rem; font-weight: 800;
}
.steps li:not(:last-child)::after {
  content: ""; position: absolute; top: .9rem; left: 2rem; right: .6rem;
  height: 1px; background: #dce5de;
}
.eyebrow {
  display: inline-flex; align-items: center; gap: .5rem; margin-bottom: .75rem;
  color: var(--green); font-size: .75rem; font-weight: 800;
  letter-spacing: .1em; text-transform: uppercase;
}
.eyebrow::before { content: ""; width: 18px; height: 2px; background: var(--lime); }
.page-intro { max-width: 680px; margin: 0 auto 1.5rem; text-align: center; }
.page-intro p { color: var(--muted); }
.journey {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: .5rem;
  margin: 0 auto 1.5rem; max-width: 920px;
}
.journey-step {
  display: flex; align-items: center; gap: .55rem; min-width: 0;
  padding: .65rem .75rem; color: #84928a; font-size: .78rem;
  border-bottom: 2px solid #dfe7df;
}
.journey-step .step-number {
  display: grid; flex: 0 0 26px; width: 26px; height: 26px;
  place-items: center; border-radius: 50%; background: #e9eee9;
  color: #68786e; font-size: .72rem; font-weight: 800;
}
.journey-step.active { color: var(--green-dark); border-bottom-color: var(--green); font-weight: 750; }
.journey-step.active .step-number { color: #fff; background: var(--green); }
.journey-step.complete { color: var(--green); border-bottom-color: #b7d9c2; }
.journey-step.complete .step-number { color: var(--green-dark); background: #e2f1e4; }
.register-layout, .auth-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(250px, .7fr); gap: 1.25rem; align-items: start; }
.auth-layout { max-width: 900px; margin: 0 auto; }
.auth-aside { padding: 1.5rem; border: 1px solid var(--line); border-radius: 18px; background: #eef4ed; }
.auth-aside h2 { font-size: 1.1rem; }
.auth-switch { padding-top: .9rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .87rem; }
.auth-switch a { font-weight: 700; }
.workspace { max-width: 1080px; margin: 0 auto; }
.workspace-heading { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
.workspace-heading h1 { margin-bottom: .2rem; }
.workspace-heading p { color: var(--muted); }
.workspace-actions { display: flex; flex-wrap: wrap; gap: .6rem; }
.workspace-actions .btn { padding: .65rem 1rem; }
.workspace-actions .btn.secondary { color: var(--green-dark); background: #f1f5ef; border-color: var(--line); }
.workspace-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; margin-bottom: 1rem; }
.summary-item { min-width: 0; padding: 1rem 1.1rem; border: 1px solid var(--line); border-radius: 15px; background: var(--surface); }
.summary-item small, .summary-item strong { display: block; }
.summary-item small { color: var(--muted); font-size: .78rem; }
.summary-item strong { margin-top: .25rem; font-size: 1.25rem; }
.summary-item .key-value { overflow-wrap: anywhere; font-size: .78rem; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(260px, .75fr); gap: 1rem; align-items: start; }
.workspace-grid .card { box-shadow: none; }
.workspace-table { min-width: 520px; }
.workspace-table td { color: var(--ink); }
.workspace-list-item { display: flex; justify-content: space-between; gap: .75rem; padding: .7rem 0; border-bottom: 1px solid var(--line); font-size: .84rem; }
.workspace-list-item:last-child { border-bottom: 0; }
.workspace-list-item span:last-child { color: var(--muted); text-align: right; }
.workspace-empty, .workspace-error, .workspace-notice { color: var(--muted); font-size: .88rem; }
.workspace-error { margin-bottom: .8rem; color: #a63d44; font-weight: 650; }
.workspace-notice:empty { display: none; }
.nav-button { width: auto; padding: .35rem .85rem; border: 1px solid var(--line); border-radius: 999px; color: var(--green-dark); background: #f1f5ef; box-shadow: none; font-size: .85rem; }
.nav-button:hover { transform: none; box-shadow: none; background: #e8f0e7; }
.nav-feedback { flex-basis: 100%; color: #a63d44; font-size: .8rem; }
.workspace[hidden] { display: none; }
.register-aside { padding: 1.5rem; border-radius: 20px; color: #eaf5ee; background: #14251f; }
.register-aside h2 { color: #fff; }
.register-aside p { color: #b8c9bf; }
.register-aside .check-list { padding-left: 1.2rem; color: #d7e5dc; }
.register-aside .check-list li { margin: .55rem 0; }
.key-result {
  margin-top: 1rem; padding: 1.1rem; border: 1px solid #d8e7d9;
  border-radius: 14px; background: #f3f8f1;
}
.key-result code { display: block; margin: .65rem 0; padding: .8rem; overflow-wrap: anywhere; }
.key-actions { display: flex; flex-wrap: wrap; gap: .65rem; margin-top: .75rem; }
.key-actions button, .key-actions .btn { flex: 1; min-width: 170px; }
.result-panel { margin-top: 1.25rem; padding: 1.25rem; border-radius: 16px; background: #f3f8f1; }
.result-panel h2 { margin-top: .5rem; }
.result-panel[data-state="bad"] { background: #fff4f2; }
.result-panel[data-state="waiting"] { background: #fff8e8; }
.result-symbol {
  display: grid; width: 44px; height: 44px; place-items: center;
  margin-bottom: .75rem; border: 1px solid #c6ead6; border-radius: 50%;
  color: var(--green); background: #e8f6ef; font-size: 1.2rem; font-weight: 750;
}
.result-panel[data-state="bad"] .result-symbol { color: #a63d44; background: #fff0ef; border-color: #f3d0ce; }
.result-panel[data-state="waiting"] .result-symbol { color: #82610a; background: #fff6d8; border-color: #f0df9e; }
.api-details { margin-top: 1rem; color: var(--muted); font-size: .83rem; }
.api-details summary { cursor: pointer; color: var(--green-dark); font-weight: 650; }
.result-symbol {
  display: grid; width: 44px; height: 44px; place-items: center;
  border: 1px solid #c6ead6; border-radius: 50%; color: var(--green);
  background: #e8f6ef; font-size: 1.2rem; font-weight: 750;
}
.result-panel[data-state="bad"] .result-symbol { color: #a63d44; background: #fff0ef; border-color: #f3d0ce; }
.result-panel[data-state="waiting"] .result-symbol { color: #82610a; background: #fff6d8; border-color: #f0df9e; }
.api-details { margin-top: 1rem; color: var(--muted); font-size: .83rem; }
.api-details summary { cursor: pointer; color: var(--green-dark); font-weight: 650; }
.result-actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1rem; }
.result-actions .btn { min-width: 190px; }
.result-actions[hidden], .key-result[hidden] { display: none; }
.shop-layout { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(240px, .65fr); gap: 1.25rem; align-items: start; }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1rem; }
.field-full { grid-column: 1 / -1; }
.shop-aside { padding: 1.25rem; border-radius: 18px; background: #eff5ec; }
.shop-aside h2 { font-size: 1rem; }
.scenario {
  display: flex; justify-content: space-between; gap: .75rem;
  padding: .75rem 0; border-bottom: 1px solid #dce8d9; font-size: .86rem;
}
.scenario:last-child { border-bottom: 0; }
.scenario code { white-space: nowrap; }
.status { min-height: 1.5rem; color: var(--green-dark); }
.widget-wrap { max-width: 600px; margin: 0 auto; }
.widget-card { overflow: hidden; }
.widget-top {
  display: flex; justify-content: space-between; align-items: center;
  gap: 1rem; padding-bottom: 1.1rem; border-bottom: 1px solid var(--line);
}
.amount { color: var(--green); background: none; -webkit-text-fill-color: currentColor; }
.meta { border-bottom-color: var(--line); }
.meta .k { color: var(--muted); }
.meta .v { color: var(--ink); }
.pill.ok { color: #087c5a; background: #e8f6ef; border-color: #c6ead6; }
.pill.warn { color: #82610a; background: #fff6d8; border-color: #f0df9e; }
.pill.info { color: #426955; background: #edf5e6; border-color: #dbe8ce; }
.pill.bad { color: #a63d44; background: #fff0ef; border-color: #f3d0ce; }
.decision-actions { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }
.decision-actions button { width: 100%; }
.table-wrap { overflow-x: auto; margin: 1.25rem 0; border: 1px solid var(--line); border-radius: 14px; }
.table-wrap table { margin: 0; }
.table-wrap th, .table-wrap td { padding: .85rem 1rem; }
.table-wrap th { background: #f6f8f5; }
.table-wrap tr:last-child td { border-bottom: 0; }
footer {
  max-width: 1080px; padding-top: 1.25rem; color: #78877f;
  border-top: 1px solid var(--line);
}
@media (max-width: 720px) {
  header { position: static; align-items: flex-start; }
  nav { width: 100%; margin-left: 0; }
  nav a { padding-inline: .55rem; font-size: .82rem; }
  .shop-layout, .register-layout, .auth-layout { grid-template-columns: 1fr; }
  .workspace-grid { grid-template-columns: 1fr; }
  .workspace-heading { align-items: flex-start; flex-direction: column; }
  .home-grid { grid-template-columns: 1fr; gap: 1.5rem; min-height: 0; padding: 1rem 0 2rem; }
  .home-preview { max-width: 520px; }
  .steps { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 480px) {
  body { padding-inline: .85rem; }
  header { gap: .65rem; margin-bottom: 1rem; }
  header .brand { font-size: 1.12rem; }
  .hero { padding-top: 1.5rem; }
  .hero h1 { font-size: 2.55rem; }
  .field-grid, .steps, .decision-actions { grid-template-columns: 1fr; }
  .workspace-summary { grid-template-columns: 1fr; }
  .steps li { min-height: 0; }
  .steps li:not(:last-child)::after { top: 1.2rem; bottom: -.2rem; left: 12px; right: auto; width: 1px; height: auto; }
  .journey { gap: .2rem; }
  .journey-step { flex-direction: column; align-items: flex-start; gap: .3rem; padding: .5rem .3rem; font-size: .67rem; }
  .field-full { grid-column: auto; }
  .row button, .hero-actions .btn { width: 100%; }
  .meta { align-items: flex-start; }
  .meta .v { overflow-wrap: anywhere; }
}
"""

_SHELL = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__ · 3Dpay</title>
  <style>__STYLE__</style>
</head>
<body>
  <header>
    <span class="brand"><span class="logo">3D</span> 3Dpay</span><span class="badge">SIMULATION</span>
    <nav>
      <a href="/">Accueil</a>
      <a data-auth="guest" href="/demo/inscription">Créer un compte</a>
      <a data-auth="guest" href="/demo/connexion">Se connecter</a>
      <a data-auth="signed-in" href="/demo/espace" hidden>Espace marchand</a>
      <button data-auth="signed-in" data-action="logout" type="button" class="nav-button" hidden>Se déconnecter</button>
      <a href="/demo/boutique">Boutique</a>
      <a href="/demo/numeros-de-test">Numéros de test</a>
      <a href="/docs">API</a>
      <span id="auth-feedback" class="nav-feedback" role="status" aria-live="polite" hidden></span>
    </nav>
  </header>
  <main>__CONTENT__</main>
  <footer>Plateforme de paiement mobile money <strong>simulée</strong> — aucun argent réel, aucune donnée bancaire.</footer>
  <script>
  (() => {
    const guestItems = document.querySelectorAll('[data-auth="guest"]');
    const signedInItems = document.querySelectorAll('[data-auth="signed-in"]');
    const feedback = document.getElementById('auth-feedback');
    const token = sessionStorage.getItem('3dp_session');

    function setAuthenticated(authenticated) {
      guestItems.forEach((item) => { item.hidden = authenticated; });
      signedInItems.forEach((item) => { item.hidden = !authenticated; });
    }

    function showFeedback(message) {
      feedback.textContent = message;
      feedback.hidden = false;
    }

    window.addEventListener('3dp-session-ended', () => setAuthenticated(false));
    setAuthenticated(Boolean(token));
    if (token) {
      fetch('/api/v1/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      }).then((response) => {
        if (response.status === 401) {
          sessionStorage.removeItem('3dp_session');
          setAuthenticated(false);
          window.dispatchEvent(new Event('3dp-session-ended'));
          return;
        }
        if (!response.ok) {
          showFeedback('Vérification de la session impossible (' + response.status + ').');
          return;
        }
        if (['/demo/connexion', '/demo/inscription'].includes(window.location.pathname)) {
          window.location.replace('/demo/espace');
        }
      }).catch(() => {
        showFeedback('Impossible de vérifier la session. Vérifiez votre connexion.');
      });
    }

    document.querySelectorAll('[data-action="logout"]').forEach((button) => {
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          const response = await fetch('/api/v1/auth/logout', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
          });
          const data = await response.json();
          if (!response.ok) {
            if (response.status === 401) {
              sessionStorage.removeItem('3dp_session');
              setAuthenticated(false);
              showFeedback('Votre session a expiré. Vous pouvez vous reconnecter.');
              window.location.assign('/');
              return;
            }
            throw new Error(typeof data.detail === 'string' ? data.detail : 'Le serveur a refusé la déconnexion.');
          }
          sessionStorage.removeItem('3dp_session');
          window.location.assign('/');
        } catch (error) {
          showFeedback('Déconnexion impossible : ' + error.message + '. Réessayez.');
          button.disabled = false;
        }
      });
    });
  })();
  </script>
</body>
</html>"""


def _render(title: str, content: str) -> HTMLResponse:
    page = (
        _SHELL.replace("__STYLE__", _STYLE)
        .replace("__TITLE__", title)
        .replace("__CONTENT__", content)
    )
    return HTMLResponse(page)


_INDEX = """
<section class="home-grid">
<div class="hero">
  <span class="eyebrow">3DPAY</span>
  <h1>Votre intégration Mobile Money, testée de bout en bout.</h1>
  <p>Créez un compte marchand, envoyez une demande de paiement et suivez le résultat.
  Les opérateurs et numéros proposés sont réservés aux essais.</p>
  <div class="hero-actions">
    <a class="btn" data-auth="guest" href="/demo/inscription">Créer un compte</a>
    <a class="btn secondary" data-auth="guest" href="/demo/connexion">Se connecter</a>
    <a class="btn" data-auth="signed-in" href="/demo/espace" hidden>Ouvrir mon espace</a>
  </div>
  <div class="home-network-line">
    <strong>Réseaux disponibles</strong>
    <span class="network-name">MTN Mobile Money</span>
    <span class="network-name">Moov Money</span>
    <span class="network-name">Celtiis Cash</span>
  </div>
</div>
<aside class="home-preview" aria-label="Aperçu du paiement">
  <div class="home-preview-head">
    <span class="home-preview-brand"><span class="home-preview-mark">3D</span> Paiement marchand</span>
    <span>APERÇU</span>
  </div>
  <div class="home-preview-total"><small>Montant de la commande</small><strong>2 500 <small>FCFA</small></strong></div>
  <div class="home-preview-method selected"><span class="home-preview-radio"></span><strong>MTN</strong><span>Mobile Money</span></div>
  <div class="home-preview-method"><span class="home-preview-radio"></span><strong>MOOV</strong><span>Moov Money</span></div>
  <div class="home-preview-method"><span class="home-preview-radio"></span><strong>CELTIIS</strong><span>Celtiis Cash</span></div>
  <div class="home-preview-submit">Confirmer le paiement</div>
  <div class="home-preview-foot"><span>Transaction de test</span><span>Simulation uniquement</span></div>
</aside>
</section>
<section class="flow-section">
  <div class="flow-heading">
    <h2>Parcours d’intégration</h2>
    <a href="/demo/numeros-de-test">Voir les numéros de test</a>
  </div>
  <ol class="steps">
    <li>Créer un compte et récupérer la clé secrète.</li>
    <li>Créer une transaction avec un scénario de test.</li>
    <li>Confirmer ou refuser dans le widget.</li>
    <li>Consulter le statut et les notifications.</li>
  </ol>
</section>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    return _render("Accueil", _INDEX)


def _journey(active: int) -> str:
    labels = ("Compte", "Paiement", "Confirmation", "Résultat")
    steps = []
    for index, label in enumerate(labels, start=1):
        state = "active" if index == active else "complete" if index < active else ""
        number = "✓" if index < active else str(index)
        steps.append(
            f'<div class="journey-step {state}" aria-current="{"step" if index == active else "false"}">'
            f'<span class="step-number">{number}</span><span>{label}</span></div>'
        )
    return f'<nav id="demo-journey" class="journey" aria-label="Étapes de la démonstration">{"".join(steps)}</nav>'


_REGISTER = """
<div class="page-intro">
  <span class="eyebrow">Étape 1 · Votre espace marchand</span>
  <h1>Créer votre compte</h1>
  <p>Un compte de démonstration vous donne une clé API pour lancer votre premier paiement fictif.</p>
</div>
<section id="register-stage" data-auth="guest">
  <div class="register-layout">
    <div class="card">
      <h2>Informations du compte</h2>
      <p class="muted">Utilisez une adresse de démonstration. Ne réutilisez pas un mot de passe personnel.</p>
      <form id="register-form">
        <label for="merchant-name">Nom de la boutique</label>
        <input id="merchant-name" name="name" minlength="2" maxlength="80" autocomplete="organization" placeholder="Ex. Boutique Ébène" required>
        <label for="merchant-email">Adresse e-mail</label>
        <input id="merchant-email" name="email" type="email" maxlength="120" autocomplete="email" placeholder="vous@exemple.bj" required>
        <label for="merchant-password">Mot de passe</label>
        <input id="merchant-password" name="password" type="password" minlength="8" maxlength="128" autocomplete="new-password" required>
            <div class="row"><button id="register-submit" type="submit">Créer mon compte</button></div>
      </form>
      <p class="status" id="register-status" role="status" aria-live="polite"></p>
      <p class="auth-switch">Déjà inscrit ? <a href="/demo/connexion">Se connecter</a></p>
      <div id="key-result" class="key-result" hidden>
        <span class="pill ok">Compte créé</span>
        <h2>Votre clé secrète</h2>
        <p class="muted">Elle ne sera affichée qu’une seule fois. Copiez-la maintenant et gardez-la privée.</p>
        <code id="secret-key"></code>
        <div class="key-actions">
          <button id="copy-key" type="button" class="btn secondary">Copier la clé</button>
          <a class="btn" href="/demo/boutique">Continuer vers le paiement</a>
        </div>
        <p class="auth-switch">Pour consulter votre espace, <a href="/demo/connexion">connectez-vous avec ces identifiants</a>.</p>
        <p id="copy-status" class="muted" role="status" aria-live="polite"></p>
      </div>
    </div>
    <aside class="register-aside">
      <span class="eyebrow">Mode simulation</span>
      <h2>Un parcours sans argent réel</h2>
      <p>Explorez l’intégration comme un marchand, du compte jusqu’au résultat de transaction.</p>
      <ul class="check-list">
        <li>Clé secrète affichée une seule fois</li>
        <li>Transactions et numéros entièrement fictifs</li>
        <li>Aucune donnée bancaire demandée</li>
      </ul>
    </aside>
  </div>
</section>
<script>
const registerForm = document.getElementById('register-form');
const registerStatus = document.getElementById('register-status');
const registerSubmit = document.getElementById('register-submit');
const keyResult = document.getElementById('key-result');
const secretKey = document.getElementById('secret-key');

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  registerSubmit.disabled = true;
  registerStatus.textContent = 'Création du compte…';
  const payload = {
    name: document.getElementById('merchant-name').value.trim(),
    email: document.getElementById('merchant-email').value.trim(),
    password: document.getElementById('merchant-password').value
  };
  try {
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) {
      registerStatus.textContent = 'Erreur ' + response.status + ' : '
        + (typeof data.detail === 'string' ? data.detail : 'Vérifiez les champs saisis.');
      return;
    }
    secretKey.textContent = data.secret_key;
    keyResult.hidden = false;
    registerForm.querySelectorAll('input, button[type="submit"]').forEach((field) => field.disabled = true);
    registerStatus.textContent = 'Compte prêt. Copiez votre clé avant de continuer.';
    keyResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } catch (error) {
    registerStatus.textContent = 'Erreur réseau : ' + error;
  } finally {
    registerSubmit.disabled = keyResult.hidden ? false : true;
  }
});

document.getElementById('copy-key').addEventListener('click', async () => {
  const copyStatus = document.getElementById('copy-status');
  try {
    await navigator.clipboard.writeText(secretKey.textContent);
    copyStatus.textContent = 'Clé copiée. Collez-la dans le formulaire de paiement.';
  } catch (error) {
    copyStatus.textContent = 'Copie impossible dans ce navigateur. Sélectionnez la clé et copiez-la manuellement.';
  }
});
</script>
"""


@router.get("/demo/inscription", response_class=HTMLResponse, include_in_schema=False)
def demo_register() -> HTMLResponse:
    return _render("Créer un compte", _journey(1) + _REGISTER)


_LOGIN = """
<div class="page-intro">
  <span class="eyebrow">Espace marchand</span>
  <h1>Se connecter</h1>
  <p>Retrouvez vos transactions, vos notifications et les réglages de votre compte.</p>
</div>
<div class="auth-layout" data-auth="guest">
  <section class="card">
    <h2>Accéder à votre espace</h2>
    <form id="login-form">
      <label for="login-email">Adresse e-mail</label>
      <input id="login-email" type="email" autocomplete="username" required>
      <label for="login-password">Mot de passe</label>
      <input id="login-password" type="password" autocomplete="current-password" required>
      <div class="row"><button id="login-submit" type="submit">Se connecter</button></div>
    </form>
    <p id="login-status" class="status" role="status" aria-live="polite"></p>
    <p class="auth-switch">Pas encore de compte ? <a href="/demo/inscription">Créer un compte marchand</a></p>
  </section>
  <aside class="auth-aside">
    <span class="eyebrow">Votre espace</span>
    <h2>Les opérations de votre compte, réunies au même endroit.</h2>
    <p>Connectez-vous pour consulter l’activité et les réglages du compte marchand.</p>
    <p class="muted">La session reste dans cet onglet et expire selon la durée configurée par le service.</p>
  </aside>
</div>
<script>
const loginForm = document.getElementById('login-form');
const loginStatus = document.getElementById('login-status');
const loginSubmit = document.getElementById('login-submit');

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginSubmit.disabled = true;
  loginStatus.textContent = 'Vérification des identifiants…';
  try {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('login-email').value.trim(),
        password: document.getElementById('login-password').value
      })
    });
    const data = await response.json();
    if (!response.ok) {
      loginStatus.textContent = 'Connexion impossible : '
        + (typeof data.detail === 'string' ? data.detail : 'Vérifiez les identifiants saisis.');
      return;
    }
    sessionStorage.setItem('3dp_session', data.access_token);
    window.location.assign('/demo/espace');
  } catch (error) {
    loginStatus.textContent = 'Erreur réseau : ' + error;
  } finally {
    loginSubmit.disabled = false;
  }
});
</script>
"""


@router.get("/demo/connexion", response_class=HTMLResponse, include_in_schema=False)
def demo_login() -> HTMLResponse:
    return _render("Se connecter", _LOGIN)


_WORKSPACE = """
<section id="workspace-loading" class="card">
  <p class="status" role="status">Chargement de votre espace marchand…</p>
</section>
<section id="workspace-content" class="workspace" hidden>
  <div class="workspace-heading">
    <div>
      <span class="eyebrow">Espace marchand</span>
      <h1>Bonjour, <span id="merchant-name">marchand</span></h1>
      <p id="merchant-email"></p>
    </div>
    <div class="workspace-actions">
      <a class="btn" href="/demo/boutique">Nouveau paiement</a>
      <button id="logout" data-action="logout" type="button" class="btn secondary">Se déconnecter</button>
    </div>
  </div>
  <div class="workspace-summary">
    <div class="summary-item"><small>Transactions</small><strong id="transaction-count">0</strong></div>
    <div class="summary-item"><small>Paiements acceptés</small><strong id="success-count">0</strong></div>
    <div class="summary-item"><small>Clé publique</small><code id="public-key" class="key-value"></code></div>
  </div>
  <div class="workspace-grid">
    <section class="card">
      <span class="eyebrow">Activité récente</span>
      <h2>Transactions</h2>
      <div class="table-wrap">
        <table class="workspace-table">
          <thead><tr><th>Référence</th><th>Opérateur</th><th>Montant</th><th>Statut</th></tr></thead>
          <tbody id="transactions-body"></tbody>
        </table>
      </div>
      <p id="transactions-empty" class="workspace-empty" hidden>Aucune transaction pour le moment.</p>
    </section>
    <div>
      <section class="card">
        <span class="eyebrow">Notifications</span>
        <h2>Derniers webhooks</h2>
        <div id="webhook-list" class="workspace-list"></div>
        <p id="webhooks-empty" class="workspace-empty" hidden>Aucune notification envoyée.</p>
      </section>
      <section class="card">
        <span class="eyebrow">Configuration</span>
        <h2>URL de webhook</h2>
        <p id="webhook-url" class="muted"></p>
        <p><a href="/demo/boutique">Créer un paiement</a> · <a href="/docs">Documentation API</a></p>
      </section>
    </div>
  </div>
</section>
<script>
const sessionToken = sessionStorage.getItem('3dp_session');
const loadingPanel = document.getElementById('workspace-loading');
const workspace = document.getElementById('workspace-content');
function showWorkspaceError(message) {
  loadingPanel.replaceChildren();
  const paragraph = document.createElement('p');
  paragraph.className = 'workspace-error';
  paragraph.textContent = message;
  const link = document.createElement('a');
  link.href = '/demo/connexion';
  link.textContent = 'Se connecter';
  loadingPanel.append(paragraph, link);
}

async function api(path) {
  const response = await fetch(path, {
    headers: { 'Authorization': 'Bearer ' + sessionToken }
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Erreur de chargement.';
    throw new Error(response.status + ' — ' + detail);
  }
  return data;
}

function appendCell(row, value) {
  const cell = document.createElement('td');
  cell.textContent = value;
  row.appendChild(cell);
}

async function loadWorkspace() {
  if (!sessionToken) {
    showWorkspaceError('Votre session n’est pas ouverte.');
    return;
  }
  try {
    const [account, transactions, webhooks, keys, settings] = await Promise.all([
      api('/api/v1/auth/me'),
      api('/api/v1/dashboard/transactions'),
      api('/api/v1/dashboard/webhooks'),
      api('/api/v1/dashboard/keys'),
      api('/api/v1/dashboard/settings')
    ]);
    document.getElementById('merchant-name').textContent = account.name;
    document.getElementById('merchant-email').textContent = account.email;
    document.getElementById('transaction-count').textContent = transactions.length;
    document.getElementById('success-count').textContent =
      transactions.filter((item) => item.status === 'SUCCEEDED').length;
    document.getElementById('public-key').textContent = keys.public_key;
    document.getElementById('webhook-url').textContent =
      settings.webhook_url || 'Aucune URL configurée';

    const transactionBody = document.getElementById('transactions-body');
    transactions.slice(0, 8).forEach((item) => {
      const row = document.createElement('tr');
      appendCell(row, item.reference);
      appendCell(row, item.operator.toUpperCase());
      appendCell(row, Number(item.amount).toLocaleString('fr-FR') + ' ' + item.currency);
      const statusCell = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = item.status === 'SUCCEEDED' ? 'pill ok'
        : item.is_final ? 'pill bad' : 'pill warn';
      badge.textContent = item.status;
      statusCell.appendChild(badge);
      row.appendChild(statusCell);
      transactionBody.appendChild(row);
    });
    document.getElementById('transactions-empty').hidden = transactions.length > 0;

    const webhookList = document.getElementById('webhook-list');
    webhooks.slice(0, 5).forEach((item) => {
      const row = document.createElement('div');
      row.className = 'workspace-list-item';
      const event = document.createElement('span');
      const state = document.createElement('span');
      event.textContent = item.event;
      state.textContent = item.state + ' · ' + item.attempts + ' essai(s)';
      row.append(event, state);
      webhookList.appendChild(row);
    });
    document.getElementById('webhooks-empty').hidden = webhooks.length > 0;
    loadingPanel.hidden = true;
    workspace.hidden = false;
  } catch (error) {
    if (String(error.message).startsWith('401')) {
      sessionStorage.removeItem('3dp_session');
      window.dispatchEvent(new Event('3dp-session-ended'));
      showWorkspaceError('Votre session a expiré. Connectez-vous à nouveau.');
      return;
    }
    showWorkspaceError('Impossible de charger votre espace : ' + error.message);
  }
}

loadWorkspace();
</script>
"""


@router.get("/demo/espace", response_class=HTMLResponse, include_in_schema=False)
def demo_workspace() -> HTMLResponse:
    return _render("Espace marchand", _WORKSPACE)


_BOUTIQUE = """
<div class="page-intro">
  <span class="eyebrow">Démonstration guidée</span>
  <h1>Créer un paiement</h1>
  <p>Configurez une transaction fictive, puis choisissez la décision du client dans le widget.</p>
</div>
<div class="shop-layout">
<section class="card">
  <h2>Détails de la transaction</h2>
  <p class="muted">Votre clé sert uniquement à cet appel. Elle n’est pas mémorisée par la page.</p>
  <form id="pay">
    <label for="secret">Clé secrète (3dp_sec_…)</label>
    <input id="secret" type="password" autocomplete="new-password" placeholder="3dp_sec_…" required>
    <div class="field-grid">
    <div>
    <label for="amount">Montant (FCFA)</label>
    <input id="amount" type="number" min="1" max="10000000" value="2500" required>
    </div>
    <div>
    <label for="operator">Opérateur</label>
    <select id="operator">
      <option value="mtn">MTN Mobile Money</option>
      <option value="moov">Moov Money</option>
      <option value="celtiis">Celtiis Cash</option>
    </select>
    </div>
    <div class="field-full">
    <label for="order">Référence commande (facultatif)</label>
    <input id="order" maxlength="80" placeholder="CMD-1042">
    </div>
    <div class="field-full">
    <label for="number">Numéro de test (8 chiffres)</label>
    <input id="number" inputmode="numeric" value="01970000" pattern="[0-9]{8}" required>
    </div>
    </div>
    <div class="row">
      <button id="submit-payment" type="submit">Créer le paiement</button>
    </div>
  </form>
  <p class="status" id="status" role="status" aria-live="polite"></p>
</section>
<aside class="shop-aside">
  <span class="eyebrow">Scénarios disponibles</span>
  <h2>Choisissez un numéro de test</h2>
  <div class="scenario"><span>Paiement accepté</span><code>01970000</code></div>
  <div class="scenario"><span>Refus opérateur</span><code>01970001</code></div>
  <div class="scenario"><span>Solde insuffisant</span><code>01970002</code></div>
  <div class="scenario"><span>En attente</span><code>01970003</code></div>
  <p class="muted">Ces numéros sont fictifs. <a href="/demo/numeros-de-test">Voir tous les détails</a>.</p>
</aside>
</div>
<script>
const form = document.getElementById('pay');
const status = document.getElementById('status');
const submitButton = document.getElementById('submit-payment');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const secret = document.getElementById('secret').value.trim();

  const body = {
    amount: Number(document.getElementById('amount').value),
    currency: 'XOF',
    operator: document.getElementById('operator').value,
    merchant_reference: document.getElementById('order').value || null,
    test_number: document.getElementById('number').value.trim()
  };

  status.textContent = 'Création de la demande…';
  submitButton.disabled = true;
  try {
    const response = await fetch('/api/v1/payments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + secret },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) {
      status.textContent = 'Erreur ' + response.status + ' : ' + JSON.stringify(data.detail);
      return;
    }
    status.textContent = 'Transaction ' + data.reference + ' créée (' + data.status + ').';
    window.location.href = '/demo/widget?reference=' + encodeURIComponent(data.reference)
      + '#decision_token=' + encodeURIComponent(data.decision_token);
  } catch (error) {
    status.textContent = 'Erreur réseau : ' + error;
  } finally {
    submitButton.disabled = false;
  }
});
</script>
"""


@router.get("/demo/boutique", response_class=HTMLResponse, include_in_schema=False)
def demo_shop() -> HTMLResponse:
    return _render("Boutique fictive", _journey(2) + _BOUTIQUE)


_WIDGET = """
<div class="widget-wrap">
<div id="decision-stage">
<div class="card widget-card">
  <div class="widget-top">
    <div><span class="eyebrow">Paiement sécurisé</span><h1>Confirmer le paiement</h1></div>
    <span class="pill info">SIMULATION</span>
  </div>
  <p class="amount" id="amount">—</p>
  <div>
    <div class="meta"><span class="k">Opérateur</span><span class="v" id="op">—</span></div>
    <div class="meta"><span class="k">Référence</span><span class="v"><code id="ref">—</code></span></div>
    <div class="meta"><span class="k">Statut</span><span class="v" id="st">—</span></div>
  </div>
  <p class="muted" id="info">Chargement…</p>
  <div class="decision-actions">
    <button id="confirm">Confirmer</button>
    <button id="decline" class="danger">Refuser</button>
  </div>
  <p class="status" id="status" role="status" aria-live="polite"></p>
</div>
</div>
<section id="result-stage" class="result-panel" hidden aria-live="polite">
  <span id="result-badge" class="pill info">SIMULATION</span>
  <h2 id="result-title">Résultat du paiement</h2>
  <p id="result-message" class="muted"></p>
  <div class="meta"><span class="k">Référence</span><span class="v" id="result-reference"></span></div>
  <div class="meta"><span class="k">Montant</span><span class="v" id="result-amount"></span></div>
  <div class="meta"><span class="k">Statut</span><span class="v" id="result-status"></span></div>
  <pre id="raw"></pre>
  <div class="result-actions">
    <a class="btn" href="/demo/boutique">Créer un autre paiement</a>
    <a class="btn secondary" href="/demo/numeros-de-test">Explorer les scénarios</a>
  </div>
</section>
</div>
<script>
const params = new URLSearchParams(window.location.search);
const reference = params.get('reference') || '';
const token = new URLSearchParams(window.location.hash.slice(1)).get('decision_token')
  || params.get('decision_token') || '';
const info = document.getElementById('info');
const status = document.getElementById('status');
const raw = document.getElementById('raw');
const decisionStage = document.getElementById('decision-stage');
const resultStage = document.getElementById('result-stage');

function pill_for(status) {
  if (status === 'SUCCEEDED') return 'pill ok';
  if (status === 'DECLINED_BY_CUSTOMER' || status === 'REJECTED_BY_OPERATOR' || status === 'FAILED') return 'pill bad';
  if (status === 'EXPIRED') return 'pill warn';
  return 'pill info';
}

function show(data) {
  document.getElementById('amount').textContent = data.amount + ' ' + data.currency;
  document.getElementById('op').textContent = data.operator ? data.operator.toUpperCase() : '—';
  document.getElementById('ref').textContent = data.reference;
  const statusBadge = document.createElement('span');
  statusBadge.className = pill_for(data.status);
  statusBadge.textContent = data.status;
  document.getElementById('st').replaceChildren(statusBadge);
  info.textContent = data.message;
  document.getElementById('result-reference').textContent = data.reference;
  document.getElementById('result-amount').textContent = data.amount + ' ' + data.currency;
  document.getElementById('result-status').textContent = data.status;
  document.getElementById('result-message').textContent = data.message;
  raw.textContent = JSON.stringify(data, null, 2);
  const isWaiting = data.status === 'PROCESSING';
  const resultBadge = document.getElementById('result-badge');
  resultBadge.className = pill_for(data.status);
  resultBadge.textContent = isWaiting ? 'RÉSULTAT EN ATTENTE' : data.status;
  document.getElementById('result-title').textContent = isWaiting
    ? 'Paiement en cours de traitement'
    : data.status === 'SUCCEEDED' ? 'Paiement accepté' : 'Paiement non abouti';
  resultStage.dataset.state = isWaiting ? 'waiting'
    : data.status === 'SUCCEEDED' ? 'ok' : 'bad';
  decisionStage.hidden = true;
  resultStage.hidden = false;
  document.querySelectorAll('#demo-journey .journey-step').forEach((step, index) => {
    step.classList.toggle('complete', index < 3);
    step.classList.toggle('active', index === 3);
    step.setAttribute('aria-current', index === 3 ? 'step' : 'false');
    if (index < 3) step.querySelector('.step-number').textContent = '✓';
  });
}

async function decide(decision) {
  document.getElementById('confirm').disabled = true;
  document.getElementById('decline').disabled = true;
  status.textContent = 'Traitement de votre décision…';
  try {
    const response = await fetch('/api/v1/payments/' + encodeURIComponent(reference) + '/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: decision, decision_token: token })
    });
    const data = await response.json();
    if (!response.ok) {
      status.textContent = 'Erreur ' + response.status + ' : ' + JSON.stringify(data.detail);
      document.getElementById('confirm').disabled = false;
      document.getElementById('decline').disabled = false;
      return;
    }
    status.textContent = 'Décision enregistrée.';
    show(data);
  } catch (error) {
    status.textContent = 'Erreur réseau : ' + error;
    document.getElementById('confirm').disabled = false;
    document.getElementById('decline').disabled = false;
  }
}

document.getElementById('confirm').addEventListener('click', () => decide('CONFIRM'));
document.getElementById('decline').addEventListener('click', () => decide('DECLINE'));

if (!reference || !token) {
  info.textContent = 'Référence ou jeton de décision manquant dans l’URL.';
  document.getElementById('confirm').disabled = true;
  document.getElementById('decline').disabled = true;
} else {
  document.getElementById('ref').textContent = reference;
  info.textContent = 'Le statut est consultable par le marchand via l’API.';
}
</script>
"""


@router.get("/demo/widget", response_class=HTMLResponse, include_in_schema=False)
def demo_widget() -> HTMLResponse:
    return _render("Widget de paiement", _journey(3) + _WIDGET)


_ROW = (
    "<tr><td><code>{number}</code></td>"
    "<td>{scenario}</td>"
    "<td><code>{status}</code></td>"
    "<td>{reason}</td></tr>"
)


@router.get("/demo/numeros-de-test", response_class=HTMLResponse, include_in_schema=False)
def demo_test_numbers() -> HTMLResponse:
    rows = []
    for number, result in TEST_SCENARIOS.items():
        status, reason = payments.STATUS_BY_OUTCOME[result.outcome]
        rows.append(
            _ROW.format(
                number=number,
                scenario=result.message,
                status=status,
                reason=f"<code>{reason}</code>" if reason else "—",
            )
        )

    status, reason = payments.STATUS_BY_OUTCOME[INVALID_TEST_NUMBER_RESULT.outcome]
    rows.append(
        _ROW.format(
            number="tout autre",
            scenario=INVALID_TEST_NUMBER_RESULT.message,
            status=status,
            reason=f"<code>{reason}</code>" if reason else "—",
        )
    )

    content = f"""
<div class="card">
  <span class="eyebrow">Référence de test</span>
  <h1>Scénarios de paiement</h1>
  <p>Le numéro détermine le scénario, <strong>quel que soit l’opérateur</strong>
  (MTN, Moov, Celtiis renvoient le même résultat). Aucun numéro réel n'est utilisé.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Numéro (8 chiffres)</th><th>Scénario simulé</th><th>Statut visé</th><th>reason</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  </div>
  <p class="muted">Pour essayer un cas, copiez son numéro dans la <a href="/demo/boutique">boutique de démonstration</a>.
  Le mode contrôlé (<code>forced_outcome</code>) est réservé aux tests internes :
  aucune route HTTP ne l'expose.</p>
</div>
"""
    return _render("Numéros de test", content)
