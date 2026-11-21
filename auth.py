"""Mots de passe : jamais stockés en clair, seulement une empreinte (hash) salée."""
import hashlib
import hmac
import os

ITERATIONS = 200_000


def hacher(mot_de_passe: str) -> str:
    sel = os.urandom(16)
    empreinte = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, ITERATIONS)
    return f"{sel.hex()}${empreinte.hex()}"


def verifier(mot_de_passe: str, stocke: str) -> bool:
    try:
        sel_hex, empreinte_hex = stocke.split("$")
    except ValueError:
        return False
    calcul = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), bytes.fromhex(sel_hex), ITERATIONS)
    return hmac.compare_digest(calcul.hex(), empreinte_hex)
