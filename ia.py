"""Reformulation des notes brutes en points de CR, avec l'API Claude.

Sans clé d'API, l'appli fonctionne en « mode démo » : elle remet seulement
les notes en forme (majuscule, point final), sans IA.
"""
import os

from config import MODELE_IA

CONSIGNES = """Tu es rédacteur de comptes rendus de réunion de chantier pour MH2O, \
un bureau de maîtrise d'œuvre d'exécution et d'OPC.

On te donne des notes brutes prises en réunion pour une section du CR. \
Transforme-les en points de compte rendu :
- une phrase claire et factuelle par point, au présent ou au futur ;
- style professionnel, neutre, impersonnel, comme dans un CR de chantier ;
- précise qui doit faire quoi et pour quand si les notes le disent ;
- développe les abréviations courantes du BTP (exe → exécution, sem pro → semaine prochaine, pb → problème…) ;
- n'invente AUCUNE information : pas de date, de nom ou de chiffre absents des notes ;
- garde les noms, dates, niveaux et références tels quels.

Réponds uniquement avec la liste des points, un par ligne, sans puces ni numéros, sans commentaire."""


def cle_api():
    cle = os.environ.get("ANTHROPIC_API_KEY")
    if cle:
        return cle
    try:
        import streamlit as st

        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None


def mode_demo():
    return not cle_api()


def _mise_en_forme_simple(notes):
    points = []
    for ligne in notes.splitlines():
        ligne = ligne.strip(" -•*\t")
        if not ligne:
            continue
        ligne = ligne[0].upper() + ligne[1:]
        if ligne[-1] not in ".!?":
            ligne += "."
        points.append(ligne)
    return points


def reformuler(notes, section=""):
    """Renvoie une liste de points rédigés."""
    if not notes.strip():
        return []
    cle = cle_api()
    if not cle:
        return _mise_en_forme_simple(notes)

    import anthropic

    client = anthropic.Anthropic(api_key=cle)
    message = client.messages.create(
        model=MODELE_IA,
        max_tokens=1000,
        system=CONSIGNES,
        messages=[
            {
                "role": "user",
                "content": f"Section du CR : {section or 'non précisée'}\n\nNotes brutes :\n{notes}",
            }
        ],
    )
    texte = "".join(bloc.text for bloc in message.content if getattr(bloc, "type", "") == "text")
    return [ligne.strip(" -•*\t") for ligne in texte.splitlines() if ligne.strip(" -•*\t")]
