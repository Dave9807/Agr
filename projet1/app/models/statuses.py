"""Statuts métier d'une transaction 3DPAY et machine à statuts.

Un statut métier n'est PAS un code HTTP :

- `201 Created` accompagne une transaction encore au statut `CREATED` ;
- `200 OK` accompagne une transaction `PROCESSING`, donc non définitive.

La liste des statuts est **figée** (phase 5) et la table `ALLOWED_TRANSITIONS`
décrit les seuls passages autorisés : toute transition absente de cette table
est **interdite** et rejetée (`409`) par `app/services/payments.py`.

Règles d'or encodées dans la table :

- un état terminal (`SUCCEEDED`, `DECLINED_BY_CUSTOMER`, `REJECTED_BY_OPERATOR`,
  `EXPIRED`, `FAILED`) n'a **aucune** sortie : rien ne revient en arrière ;
- refus du client (`DECLINED_BY_CUSTOMER`) et rejet de l'opérateur
  (`REJECTED_BY_OPERATOR`) sont deux états distincts, jamais l'un ni l'autre
  ne se transforme en l'autre ;
- `PROCESSING` (un statut d'attente) ne revient jamais en arrière et n'est
  **jamais** présenté comme un succès : `is_final(PROCESSING)` vaut `False`.

`PROCESSING` est le nom API de ce que les documents de conception appellent
`PENDING` : un seul statut d'attente, pour ne pas en avoir deux qui veulent
dire la même chose.

Équivalence FedaPay : `AUTH_ET_BENCHMARK.md` §8.4.
"""

CREATED = "CREATED"
AWAITING_CUSTOMER_ACTION = "AWAITING_CUSTOMER_ACTION"
PROCESSING = "PROCESSING"
SUCCEEDED = "SUCCEEDED"
DECLINED_BY_CUSTOMER = "DECLINED_BY_CUSTOMER"
REJECTED_BY_OPERATOR = "REJECTED_BY_OPERATOR"
EXPIRED = "EXPIRED"
FAILED = "FAILED"

ALL_STATUSES: tuple[str, ...] = (
    CREATED,
    AWAITING_CUSTOMER_ACTION,
    PROCESSING,
    SUCCEEDED,
    DECLINED_BY_CUSTOMER,
    REJECTED_BY_OPERATOR,
    EXPIRED,
    FAILED,
)

# --- Machine à statuts --------------------------------------------------------
#
# Toute transition absente de ce tableau est INTERDITE et rejetée (HTTP 409).

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    # Demande créée : le client peut encore décider, ou l'opérateur être
    # interrogé directement (la décision lui-même peut être immédiate).
    CREATED: frozenset(
        {
            AWAITING_CUSTOMER_ACTION,
            DECLINED_BY_CUSTOMER,
            REJECTED_BY_OPERATOR,
            SUCCEEDED,
            PROCESSING,
            EXPIRED,
            FAILED,
        }
    ),
    # Le client ouvre/confirme son widget : même destinées, sauf `AWAITING`
    # déjà consommée.
    AWAITING_CUSTOMER_ACTION: frozenset(
        {
            DECLINED_BY_CUSTOMER,
            REJECTED_BY_OPERATOR,
            SUCCEEDED,
            PROCESSING,
            EXPIRED,
            FAILED,
        }
    ),
    # Opérateur en cours : le résultat n'est pas encore définitif. Jamais de
    # retour en arrière vers l'attente du client.
    PROCESSING: frozenset({SUCCEEDED, REJECTED_BY_OPERATOR, EXPIRED, FAILED}),
    # États terminaux : aucune sortie.
    SUCCEEDED: frozenset(),
    DECLINED_BY_CUSTOMER: frozenset(),
    REJECTED_BY_OPERATOR: frozenset(),
    EXPIRED: frozenset(),
    FAILED: frozenset(),
}

# États définitifs : aucune évolution ultérieure n'est attendue.
# (Équivalents : les clés du tableau dont l'ensemble de sortie est vide.)
TERMINAL_STATUSES: frozenset[str] = frozenset(
    status for status, targets in ALLOWED_TRANSITIONS.items() if not targets
)
FINAL_STATUSES: frozenset[str] = TERMINAL_STATUSES

# Statuts à partir desquels le client peut encore décider.
ACTIONABLE_STATUSES: frozenset[str] = frozenset({CREATED, AWAITING_CUSTOMER_ACTION})


def can_transition(current: str, target: str) -> bool:
    """Vrai si le passage `current -> target` est autorisé par la table.

    Lève `ValueError` pour un statut inconnu : une faute de frappe dans un
    statut ne doit jamais passer pour une transition interdite.
    """
    if current not in ALLOWED_TRANSITIONS or target not in ALL_STATUSES:
        raise ValueError(f"Statut inconnu : {current!r} -> {target!r}.")
    return target in ALLOWED_TRANSITIONS[current]


def is_final(status: str) -> bool:
    """Vrai si le statut est définitif (un statut d'attente ne l'est jamais)."""
    return status in FINAL_STATUSES
