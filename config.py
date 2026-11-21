"""Réglages de l'application.

Les informations secrètes (clés, mots de passe) ne sont JAMAIS écrites ici :
elles sont lues dans les « Secrets » de Streamlit (ou dans les variables d'environnement).
"""
import os

NOM_APPLI = "MH2O · Comptes rendus"

# Modèle d'IA utilisé pour la reformulation (API Claude d'Anthropic)
MODELE_IA = os.environ.get("CR_MODELE_IA", "claude-sonnet-5-5")

# Couleur des nouveaux points insérés dans le CR (pour les repérer). Mettre None pour ne pas colorer.
COULEUR_NOUVEAUX_POINTS = "1F3864"

# Nom du compartiment (bucket) Supabase où sont rangés les fichiers Word
BUCKET_SUPABASE = "comptes-rendus"

# Mode local (sans Supabase) : dossier où sont stockées la base et les fichiers
DOSSIER_DONNEES = os.environ.get("CR_DOSSIER_DONNEES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees"))


def secret(nom):
    """Lit un secret : d'abord les variables d'environnement, puis les Secrets de Streamlit."""
    valeur = os.environ.get(nom)
    if valeur:
        return valeur.strip()
    try:
        import streamlit as st

        valeur = st.secrets.get(nom)
        return str(valeur).strip() if valeur else None
    except Exception:
        return None


def mode_supabase():
    """True si les 3 secrets Supabase sont renseignés ; sinon l'appli fonctionne en local."""
    return bool(secret("SUPABASE_DB_URL") and secret("SUPABASE_URL") and secret("SUPABASE_SECRET_KEY"))
