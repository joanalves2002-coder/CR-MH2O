"""Stockage des fichiers Word : un dossier par chantier.

- Avec Supabase : fichiers rangés dans Supabase Storage (compartiment privé), conservés durablement.
- Sans Supabase : fichiers rangés dans le dossier local « donnees/fichiers ».
La « clé » d'un fichier ressemble à : chantier_3/CR_113.docx
"""
import io
import json
import os
import zipfile

import requests

import config

TYPE_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def cle_cr(chantier_id, numero):
    return f"chantier_{chantier_id}/CR_{int(numero):03d}.docx"


# ---------------------------------------------------------------------
# Supabase Storage (API web)
# ---------------------------------------------------------------------
def _entetes():
    cle = config.secret("SUPABASE_SECRET_KEY")
    entetes = {"apikey": cle}
    if not cle.startswith("sb_"):
        # ancienne clé « service_role » (format JWT) : on l'envoie aussi en Authorization
        entetes["Authorization"] = f"Bearer {cle}"
    return entetes


def _url(chemin):
    return config.secret("SUPABASE_URL").rstrip("/") + "/storage/v1/" + chemin


def _supabase():
    return bool(config.secret("SUPABASE_URL") and config.secret("SUPABASE_SECRET_KEY"))


def initialiser():
    """Crée le compartiment privé s'il n'existe pas encore (sans effet s'il existe)."""
    if not _supabase():
        os.makedirs(os.path.join(config.DOSSIER_DONNEES, "fichiers"), exist_ok=True)
        return
    r = requests.get(_url(f"bucket/{config.BUCKET_SUPABASE}"), headers=_entetes(), timeout=20)
    if r.status_code == 200:
        return
    r = requests.post(
        _url("bucket"),
        headers=_entetes(),
        json={"id": config.BUCKET_SUPABASE, "name": config.BUCKET_SUPABASE, "public": False},
        timeout=20,
    )
    if r.status_code not in (200, 201) and "already exists" not in r.text.lower():
        raise RuntimeError(f"Impossible de créer le compartiment Supabase : {r.status_code} {r.text}")


def enregistrer(chantier_id, numero, contenu: bytes):
    cle = cle_cr(chantier_id, numero)
    if _supabase():
        r = requests.post(
            _url(f"object/{config.BUCKET_SUPABASE}/{cle}"),
            headers={**_entetes(), "Content-Type": TYPE_DOCX, "x-upsert": "true"},
            data=contenu,
            timeout=60,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Envoi du fichier vers Supabase impossible : {r.status_code} {r.text}")
    else:
        chemin = os.path.join(config.DOSSIER_DONNEES, "fichiers", cle)
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "wb") as f:
            f.write(contenu)
    return cle


def lire(cle) -> bytes:
    if _supabase():
        r = requests.get(_url(f"object/{config.BUCKET_SUPABASE}/{cle}"), headers=_entetes(), timeout=60)
        if r.status_code != 200:
            raise FileNotFoundError(f"Fichier introuvable dans Supabase : {cle}")
        return r.content
    with open(os.path.join(config.DOSSIER_DONNEES, "fichiers", cle), "rb") as f:
        return f.read()


def supprimer(cle):
    if not cle:
        return
    if _supabase():
        requests.delete(_url(f"object/{config.BUCKET_SUPABASE}/{cle}"), headers=_entetes(), timeout=30)
    else:
        chemin = os.path.join(config.DOSSIER_DONNEES, "fichiers", cle)
        if os.path.exists(chemin):
            os.remove(chemin)


def sauvegarde_zip(donnees: dict) -> bytes:
    """Zip contenant donnees.json (tables) + tous les fichiers Word, rangés par chantier."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("donnees.json", json.dumps(donnees, ensure_ascii=False, indent=2, default=str))
        for cr in donnees.get("comptes_rendus", []):
            try:
                z.writestr("fichiers/" + cr["fichier"], lire(cr["fichier"]))
            except Exception:
                z.writestr("fichiers/" + cr["fichier"] + ".MANQUANT.txt", "Fichier introuvable au moment de la sauvegarde.")
    return tampon.getvalue()
