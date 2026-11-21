"""Réglages de l'application. Modifiez ici si besoin."""
import os

# Dossier où sont stockées la base de données et les fichiers Word des CR
DOSSIER_DONNEES = os.environ.get("CR_DOSSIER_DONNEES", os.path.join(os.path.dirname(__file__), "donnees"))

# Modèle d'IA utilisé pour la reformulation (API Claude d'Anthropic)
MODELE_IA = os.environ.get("CR_MODELE_IA", "claude-sonnet-5-5")

# Couleur des nouveaux points insérés dans le CR (pour les repérer). Mettre None pour ne pas colorer.
COULEUR_NOUVEAUX_POINTS = "1F3864"

NOM_APPLI = "MH2O · Comptes rendus"
