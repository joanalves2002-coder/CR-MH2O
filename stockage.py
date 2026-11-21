"""Stockage des fichiers Word : un dossier par chantier."""
import os
import shutil

from config import DOSSIER_DONNEES

DOSSIER_FICHIERS = os.path.join(DOSSIER_DONNEES, "fichiers")


def dossier_chantier(chantier_id):
    chemin = os.path.join(DOSSIER_FICHIERS, f"chantier_{chantier_id}")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def chemin_cr(chantier_id, numero, suffixe=""):
    return os.path.join(dossier_chantier(chantier_id), f"CR_{numero:03d}{suffixe}.docx")


def enregistrer_televersement(chantier_id, numero, contenu: bytes):
    chemin = chemin_cr(chantier_id, numero)
    with open(chemin, "wb") as f:
        f.write(contenu)
    return chemin


def lire(chemin):
    with open(chemin, "rb") as f:
        return f.read()


def supprimer(chemin):
    if chemin and os.path.exists(chemin):
        os.remove(chemin)


def sauvegarder_tout(destination):
    """Copie complète des données (base + fichiers) dans un zip. Renvoie le chemin du zip."""
    return shutil.make_archive(destination, "zip", DOSSIER_DONNEES)
