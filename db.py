"""Base de données SQLite : utilisateurs, chantiers, accès et comptes rendus."""
import os
import sqlite3
from datetime import datetime

import auth
from config import DOSSIER_DONNEES

CHEMIN_BASE = os.path.join(DOSSIER_DONNEES, "appli_cr.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    mdp_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'utilisateur')),
    actif INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS chantiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    ville TEXT,
    maitre_ouvrage TEXT,
    statut TEXT NOT NULL DEFAULT 'En cours',
    cree_le TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS acces (
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    chantier_id INTEGER NOT NULL REFERENCES chantiers(id),
    droit TEXT NOT NULL CHECK (droit IN ('redaction', 'lecture')),
    PRIMARY KEY (utilisateur_id, chantier_id)
);
CREATE TABLE IF NOT EXISTS comptes_rendus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chantier_id INTEGER NOT NULL REFERENCES chantiers(id),
    numero INTEGER NOT NULL,
    date_reunion TEXT NOT NULL,
    auteur_id INTEGER REFERENCES utilisateurs(id),
    statut TEXT NOT NULL CHECK (statut IN ('Brouillon', 'Validé', 'Diffusé')),
    fichier TEXT NOT NULL,
    texte TEXT,
    cree_le TEXT NOT NULL,
    UNIQUE (chantier_id, numero)
);
"""


def connexion():
    os.makedirs(DOSSIER_DONNEES, exist_ok=True)
    con = sqlite3.connect(CHEMIN_BASE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def initialiser():
    with connexion() as con:
        con.executescript(SCHEMA)


def maintenant():
    return datetime.now().isoformat(timespec="seconds")


# ---------- Utilisateurs ----------
def nb_utilisateurs():
    with connexion() as con:
        return con.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]


def creer_utilisateur(nom, email, mot_de_passe, role="utilisateur"):
    with connexion() as con:
        con.execute(
            "INSERT INTO utilisateurs (nom, email, mdp_hash, role) VALUES (?, ?, ?, ?)",
            (nom.strip(), email.strip().lower(), auth.hacher(mot_de_passe), role),
        )


def authentifier(email, mot_de_passe):
    with connexion() as con:
        u = con.execute(
            "SELECT * FROM utilisateurs WHERE email = ? AND actif = 1", (email.strip().lower(),)
        ).fetchone()
    if u and auth.verifier(mot_de_passe, u["mdp_hash"]):
        return dict(u)
    return None


def liste_utilisateurs():
    with connexion() as con:
        return [dict(r) for r in con.execute("SELECT id, nom, email, role, actif FROM utilisateurs ORDER BY nom")]


def changer_mot_de_passe(utilisateur_id, nouveau):
    with connexion() as con:
        con.execute("UPDATE utilisateurs SET mdp_hash = ? WHERE id = ?", (auth.hacher(nouveau), utilisateur_id))


def activer_utilisateur(utilisateur_id, actif):
    with connexion() as con:
        con.execute("UPDATE utilisateurs SET actif = ? WHERE id = ?", (1 if actif else 0, utilisateur_id))


# ---------- Chantiers et accès ----------
def creer_chantier(nom, ville="", maitre_ouvrage=""):
    with connexion() as con:
        cur = con.execute(
            "INSERT INTO chantiers (nom, ville, maitre_ouvrage, cree_le) VALUES (?, ?, ?, ?)",
            (nom.strip(), ville.strip(), maitre_ouvrage.strip(), maintenant()),
        )
        return cur.lastrowid


def modifier_statut_chantier(chantier_id, statut):
    with connexion() as con:
        con.execute("UPDATE chantiers SET statut = ? WHERE id = ?", (statut, chantier_id))


def chantier(chantier_id):
    with connexion() as con:
        r = con.execute("SELECT * FROM chantiers WHERE id = ?", (chantier_id,)).fetchone()
        return dict(r) if r else None


def tous_les_chantiers():
    with connexion() as con:
        return [dict(r) for r in con.execute("SELECT * FROM chantiers ORDER BY nom")]


def chantiers_visibles(utilisateur):
    """L'admin voit tout ; les autres ne voient que les chantiers qui leur sont attribués."""
    dernier = "(SELECT MAX(numero) FROM comptes_rendus cr WHERE cr.chantier_id = c.id) AS dernier_numero"
    ordre = "ORDER BY c.statut = 'En cours' DESC, c.nom"
    with connexion() as con:
        if utilisateur["role"] == "admin":
            lignes = con.execute(f"SELECT c.*, 'redaction' AS droit, {dernier} FROM chantiers c {ordre}").fetchall()
        else:
            lignes = con.execute(
                f"SELECT c.*, a.droit, {dernier} FROM chantiers c "
                f"JOIN acces a ON a.chantier_id = c.id AND a.utilisateur_id = ? {ordre}",
                (utilisateur["id"],),
            ).fetchall()
    return [dict(r) for r in lignes]


def droit_sur_chantier(utilisateur, chantier_id):
    """Renvoie 'redaction', 'lecture' ou None."""
    if utilisateur["role"] == "admin":
        return "redaction"
    with connexion() as con:
        r = con.execute(
            "SELECT droit FROM acces WHERE utilisateur_id = ? AND chantier_id = ?",
            (utilisateur["id"], chantier_id),
        ).fetchone()
    return r["droit"] if r else None


def donner_acces(utilisateur_id, chantier_id, droit):
    with connexion() as con:
        con.execute(
            "INSERT INTO acces (utilisateur_id, chantier_id, droit) VALUES (?, ?, ?) "
            "ON CONFLICT (utilisateur_id, chantier_id) DO UPDATE SET droit = excluded.droit",
            (utilisateur_id, chantier_id, droit),
        )


def retirer_acces(utilisateur_id, chantier_id):
    with connexion() as con:
        con.execute("DELETE FROM acces WHERE utilisateur_id = ? AND chantier_id = ?", (utilisateur_id, chantier_id))


def equipe_chantier(chantier_id):
    with connexion() as con:
        return [
            dict(r)
            for r in con.execute(
                "SELECT u.id, u.nom, u.email, a.droit FROM acces a JOIN utilisateurs u ON u.id = a.utilisateur_id "
                "WHERE a.chantier_id = ? ORDER BY u.nom",
                (chantier_id,),
            )
        ]


# ---------- Comptes rendus ----------
def ajouter_cr(chantier_id, numero, date_reunion, auteur_id, statut, fichier, texte):
    with connexion() as con:
        cur = con.execute(
            "INSERT INTO comptes_rendus (chantier_id, numero, date_reunion, auteur_id, statut, fichier, texte, cree_le) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chantier_id, numero, date_reunion, auteur_id, statut, fichier, texte, maintenant()),
        )
        return cur.lastrowid


def crs_du_chantier(chantier_id):
    with connexion() as con:
        return [
            dict(r)
            for r in con.execute(
                "SELECT cr.*, u.nom AS auteur FROM comptes_rendus cr LEFT JOIN utilisateurs u ON u.id = cr.auteur_id "
                "WHERE cr.chantier_id = ? ORDER BY cr.numero DESC",
                (chantier_id,),
            )
        ]


def dernier_cr(chantier_id):
    crs = crs_du_chantier(chantier_id)
    return crs[0] if crs else None


def changer_statut_cr(cr_id, statut):
    with connexion() as con:
        con.execute("UPDATE comptes_rendus SET statut = ? WHERE id = ?", (statut, cr_id))


def supprimer_cr(cr_id):
    with connexion() as con:
        r = con.execute("SELECT fichier FROM comptes_rendus WHERE id = ?", (cr_id,)).fetchone()
        con.execute("DELETE FROM comptes_rendus WHERE id = ?", (cr_id,))
    return r["fichier"] if r else None


def rechercher(utilisateur, terme):
    ids = [c["id"] for c in chantiers_visibles(utilisateur)]
    if not ids or not terme.strip():
        return []
    marques = ",".join("?" * len(ids))
    with connexion() as con:
        return [
            dict(r)
            for r in con.execute(
                f"SELECT cr.id, cr.numero, cr.date_reunion, cr.texte, cr.fichier, cr.statut, c.nom AS chantier, c.id AS chantier_id "
                f"FROM comptes_rendus cr JOIN chantiers c ON c.id = cr.chantier_id "
                f"WHERE cr.chantier_id IN ({marques}) AND cr.texte LIKE ? ORDER BY cr.date_reunion DESC LIMIT 50",
                (*ids, f"%{terme.strip()}%"),
            )
        ]
