"""Pages HTML de démonstration (aucune dépendance externe).

- `/`                     : accueil et liens utiles ;
- `/demo/boutique`        : boutique fictive qui crée une demande de paiement ;
- `/demo/widget`          : widget simulé (confirmation / refus du client) ;
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
.hero { text-align: left; padding: clamp(1.5rem, 5vw, 4rem) 0 2.75rem; }
.hero h1 {
  max-width: 760px; font-size: clamp(2.4rem, 6vw, 4.65rem);
  line-height: 1.03; letter-spacing: -.065em;
}
.hero h1 .grad {
  background: none; color: var(--green);
  -webkit-text-fill-color: currentColor;
}
.hero p { max-width: 620px; margin: 0 0 1.6rem; font-size: 1.08rem; }
.hero .pill { margin-bottom: .85rem; }
.pill.warn { color: #73540a; background: #fff6d8; border-color: #f0df9e; }
.hero-actions { justify-content: flex-start; }
.features { gap: .9rem; margin-bottom: 1.25rem; }
.feature { padding: 1.25rem; }
.feature .icon {
  display: grid; width: 42px; height: 42px; place-items: center;
  border-radius: 13px; background: #edf5e6;
}
.feature h3 { letter-spacing: -.02em; }
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: .75rem; padding: 0; list-style: none; counter-reset: steps; }
.steps li {
  counter-increment: steps; padding: 1rem; border: 1px solid var(--line);
  border-radius: 14px; background: #fbfcfa; font-size: .92rem;
}
.steps li::before {
  content: "0" counter(steps); display: block; margin-bottom: .7rem;
  color: var(--green); font-size: .75rem; font-weight: 800; letter-spacing: .08em;
}
.eyebrow {
  display: inline-flex; align-items: center; gap: .5rem; margin-bottom: .75rem;
  color: var(--green); font-size: .75rem; font-weight: 800;
  letter-spacing: .1em; text-transform: uppercase;
}
.eyebrow::before { content: ""; width: 18px; height: 2px; background: var(--lime); }
.page-intro { max-width: 680px; margin: 0 auto 1.5rem; text-align: center; }
.page-intro p { color: var(--muted); }
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
  .shop-layout { grid-template-columns: 1fr; }
  .steps { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 480px) {
  body { padding-inline: .85rem; }
  header { gap: .65rem; margin-bottom: 1rem; }
  header .brand { font-size: 1.12rem; }
  .hero { padding-top: 1.5rem; }
  .hero h1 { font-size: 2.55rem; }
  .field-grid, .steps, .decision-actions { grid-template-columns: 1fr; }
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
      <a href="/demo/boutique">Boutique</a>
      <a href="/demo/numeros-de-test">Numéros de test</a>
      <a href="/docs">API</a>
    </nav>
  </header>
  <main>__CONTENT__</main>
  <footer>Plateforme de paiement mobile money <strong>simulée</strong> — aucun argent réel, aucune donnée bancaire.</footer>
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
<div class="hero">
  <span class="eyebrow">Paiements mobiles · Bénin</span><br>
  <span class="pill warn">⚠ Plateforme de démonstration</span>
  <h1>Le paiement Mobile Money, <span class="grad">sans le risque.</span></h1>
  <p>3Dpay reproduit le cycle complet d'un agrégateur de paiement : inscription,
  clés API, demande de paiement, confirmation du client, webhook signé et tableau
  de bord — avec de l'argent fictif.</p>
  <div class="hero-actions">
    <a class="btn" href="/demo/boutique">Essayer la démonstration →</a>
    <a class="btn secondary" href="/demo/numeros-de-test">Explorer les scénarios</a>
  </div>
</div>

<div class="features">
  <div class="feature">
    <div class="icon">💳</div>
    <h3>3 opérateurs simulés</h3>
    <p>MTN Mobile Money, Moov Money et Celtiis Cash sur un même numéro fictif.</p>
  </div>
  <div class="feature">
    <div class="icon">🔐</div>
    <h3>Webhooks signés</h3>
    <p>Signature HMAC, retry, journal des livraisons — comme un vrai agrégateur.</p>
  </div>
  <div class="feature">
    <div class="icon">📊</div>
    <h3>Tableau de bord</h3>
    <p>Transactions, clés, réglages : un compte, ses données, et rien que ça.</p>
  </div>
</div>

<div class="card">
  <span class="eyebrow">Prêt en quelques instants</span>
  <h2>Votre première transaction de test</h2>
  <ol class="steps">
    <li>Créer un compte via <a href="/docs">l’API</a> (<code>POST /api/v1/auth/register</code>).</li>
    <li>Ouvrir la <a href="/demo/boutique">boutique fictive</a> avec votre clé.</li>
    <li>Choisir un scénario de paiement simulé.</li>
    <li>Confirmer ou refuser dans le widget de paiement.</li>
  </ol>
  <p class="muted">Aucun paiement réel n’est effectué. Les identifiants saisis dans la boutique ne sont pas conservés.</p>
</div>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    return _render("Accueil", _INDEX)


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
      <button id="submit-payment" type="submit">Créer le paiement →</button>
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
      + '&decision_token=' + encodeURIComponent(data.decision_token);
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
    return _render("Boutique fictive", _BOUTIQUE)


_WIDGET = """
<div class="widget-wrap">
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
  <pre id="raw"></pre>
</div>
</div>
<script>
const params = new URLSearchParams(window.location.search);
const reference = params.get('reference') || '';
const token = params.get('decision_token') || '';
const info = document.getElementById('info');
const status = document.getElementById('status');
const raw = document.getElementById('raw');

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
  raw.textContent = JSON.stringify(data, null, 2);
  const done = data.is_final;
  document.getElementById('confirm').disabled = done;
  document.getElementById('decline').disabled = done;
}

async function decide(decision) {
  status.textContent = 'Envoi de la décision…';
  document.getElementById('confirm').disabled = true;
  document.getElementById('decline').disabled = true;
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
} else {
  document.getElementById('ref').textContent = reference;
  info.textContent = 'Le statut est consultable par le marchand via l’API.';
}
</script>
"""


@router.get("/demo/widget", response_class=HTMLResponse, include_in_schema=False)
def demo_widget() -> HTMLResponse:
    return _render("Widget de paiement", _WIDGET)


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
