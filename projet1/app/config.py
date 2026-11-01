"""Configuration de l'application, lue depuis l'environnement (`.env`).

Règle du projet : **aucune valeur sensible en dur** dans le code.
Tout (URL de base, secret de webhook, seuils) vient d'ici, donc d'un `.env`
ou des variables d'environnement du serveur.

`load_dotenv` ne remplace jamais une variable déjà définie dans
l'environnement : les tests peuvent donc imposer leurs propres valeurs
avant d'importer l'application.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Réglages de l'application.

    Volontairement modifiable (pas de `frozen`) pour que les tests puissent
    ajuster un seuil sans redémarrer l'application.
    """

    def __init__(self) -> None:
        # --- Général ---------------------------------------------------------
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.app_name: str = os.getenv("APP_NAME", "3DPAY")
        self.app_debug: bool = _bool("APP_DEBUG", True)
        self.simulation_label: str = "SIMULATION"

        # --- Persistance -----------------------------------------------------
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./3dpay.db")

        # --- Sessions --------------------------------------------------------
        self.session_ttl_hours: int = _int("SESSION_TTL_HOURS", 24)

        # --- Transactions ----------------------------------------------------
        self.transaction_ttl_minutes: int = _int("TRANSACTION_TTL_MINUTES", 30)

        # --- Webhooks --------------------------------------------------------
        self.webhook_secret: str = os.getenv(
            "WEBHOOK_SECRET", "changez-moi-secret-de-developpement"
        )
        self.webhook_max_attempts: int = _int("WEBHOOK_MAX_ATTEMPTS", 5)
        self.webhook_timeout_seconds: float = _float("WEBHOOK_TIMEOUT_SECONDS", 2.0)
        self.webhook_retry_delay_seconds: float = _float(
            "WEBHOOK_RETRY_DELAY_SECONDS", 0.0
        )
        # Protection SSRF : active par défaut. On ne la désactive que pour les
        # démonstrations locales (recevoir un webhook sur 127.0.0.1).
        self.webhook_block_private: bool = _bool("WEBHOOK_BLOCK_PRIVATE", True)

        # --- Limitation du débit ---------------------------------------------
        self.rate_limit_enabled: bool = _bool("RATE_LIMIT_ENABLED", True)
        self.rate_limit_auth_per_minute: int = _int("RATE_LIMIT_AUTH_PER_MINUTE", 10)
        self.rate_limit_payments_per_minute: int = _int(
            "RATE_LIMIT_PAYMENTS_PER_MINUTE", 60
        )


settings = Settings()
