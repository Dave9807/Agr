"""Catalogue statique des opérateurs Mobile Money simulés.

En phase 4, chaque opérateur gagnera son propre module (mtn.py, moov.py,
celtiis.py) chargé de simuler les résultats de paiement.
"""

OPERATORS: list[dict[str, str]] = [
    {"id": "mtn", "name": "MTN Mobile Money", "country": "Bénin"},
    {"id": "moov", "name": "Moov Money", "country": "Bénin"},
    {"id": "celtiis", "name": "Celtiis Cash", "country": "Bénin"},
]
