"""Lecture et écriture des CR Word (trame MH2O).

Principe : le nouveau CR est une copie du CR précédent, dans laquelle on
1) met à jour le numéro du CR,
2) ajoute les nouveaux points à la fin de la section choisie.
La mise en page, les en-têtes et les tableaux existants sont conservés.
"""
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor
from docx.text.paragraph import Paragraph

LONGUEUR_MAX_TITRE = 120


def _est_titre(paragraphe: Paragraph) -> bool:
    """Un titre = style 'Titre'/'Heading', ou paragraphe court entièrement en gras."""
    texte = paragraphe.text.strip()
    if not texte:
        return False
    nom_style = (paragraphe.style.name or "").lower() if paragraphe.style is not None else ""
    if nom_style.startswith(("heading", "titre", "title")):
        return True
    runs = [r for r in paragraphe.runs if r.text.strip()]
    if runs and len(texte) <= LONGUEUR_MAX_TITRE and all(r.bold for r in runs):
        return True
    return False


def _niveau(paragraphe: Paragraph) -> int:
    nom_style = (paragraphe.style.name or "") if paragraphe.style is not None else ""
    chiffres = re.findall(r"\d+", nom_style)
    return int(chiffres[0]) if chiffres else 9


def _titres(doc):
    """Liste ordonnée des paragraphes titres du corps du document (hors tableaux)."""
    return [p for p in doc.paragraphs if _est_titre(p)]


def lister_sections(chemin):
    """Sections disponibles pour insérer des points : [{'index', 'titre', 'niveau'}]."""
    doc = Document(chemin)
    return [
        {"index": i, "titre": p.text.strip(), "niveau": _niveau(p)}
        for i, p in enumerate(_titres(doc))
    ]


def extraire_texte(chemin):
    """Tout le texte du CR (paragraphes + tableaux), pour la recherche."""
    doc = Document(chemin)
    morceaux = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for ligne in table.rows:
            for cellule in ligne.cells:
                morceaux.append(cellule.text)
    return "\n".join(t for t in morceaux if t.strip())


def _remplacer_dans_paragraphe(paragraphe, motif, remplacement):
    if not motif.search(paragraphe.text):
        return False
    # 1) essai run par run pour garder la mise en forme
    remplace = False
    for run in paragraphe.runs:
        if motif.search(run.text):
            run.text = motif.sub(remplacement, run.text)
            remplace = True
    if remplace:
        return True
    # 2) texte coupé entre plusieurs runs : on regroupe dans le premier run
    nouveau = motif.sub(remplacement, paragraphe.text)
    if paragraphe.runs:
        paragraphe.runs[0].text = nouveau
        for run in paragraphe.runs[1:]:
            run.text = ""
    return True


def _tous_les_paragraphes(doc):
    for p in doc.paragraphs:
        yield p
    for table in doc.tables:
        for ligne in table.rows:
            for cellule in ligne.cells:
                yield from cellule.paragraphs
    for section in doc.sections:
        for partie in (section.header, section.footer, section.first_page_header, section.first_page_footer):
            if partie is None:
                continue
            yield from partie.paragraphs
            for table in partie.tables:
                for ligne in table.rows:
                    for cellule in ligne.cells:
                        yield from cellule.paragraphs


def mettre_a_jour_numero(doc, ancien, nouveau):
    """Remplace 'n°112', 'N° 112', 'CR 112'... par le nouveau numéro. Renvoie le nombre de remplacements."""
    motif = re.compile(rf"((?:n|N)\s*°\s*|(?:CR|cr)\s*(?:n\s*°\s*)?){ancien}\b")
    total = 0
    for p in _tous_les_paragraphes(doc):
        if _remplacer_dans_paragraphe(p, motif, rf"\g<1>{nouveau}"):
            total += 1
    return total


def _dernier_element_de_section(titre: Paragraph, corps):
    """Dernier élément (paragraphe ou tableau) avant le titre suivant."""
    element = titre._p
    dernier = element
    suivant = element.getnext()
    while suivant is not None:
        if suivant.tag == qn("w:sectPr"):
            break
        if suivant.tag == qn("w:p") and _est_titre(Paragraph(suivant, corps)):
            break
        dernier = suivant
        suivant = suivant.getnext()
    return dernier


def _style_paragraphe_section(titre: Paragraph, corps):
    """Style du premier paragraphe 'normal' de la section, pour que les ajouts s'y fondent."""
    suivant = titre._p.getnext()
    while suivant is not None and suivant.tag != qn("w:sectPr"):
        if suivant.tag == qn("w:p"):
            p = Paragraph(suivant, corps)
            if _est_titre(p):
                break
            if p.text.strip():
                return p.style
        suivant = suivant.getnext()
    return None


def generer_cr(chemin_base, chemin_sortie, ajouts, ancien_numero, nouveau_numero, couleur=None):
    """Crée le nouveau CR.

    ajouts : liste de {'section_index': int, 'textes': [str, ...]}
    Renvoie un petit bilan {'numeros_remplaces': int, 'points_ajoutes': int}.
    """
    doc = Document(chemin_base)
    titres = _titres(doc)

    points = 0
    for ajout in ajouts:
        titre = titres[ajout["section_index"]]
        style = _style_paragraphe_section(titre, doc._body)
        ancre = _dernier_element_de_section(titre, doc._body)
        for texte in ajout["textes"]:
            texte = texte.strip()
            if not texte:
                continue
            nouvel_element = OxmlElement("w:p")
            ancre.addnext(nouvel_element)
            paragraphe = Paragraph(nouvel_element, doc._body)
            if style is not None:
                paragraphe.style = style
            run = paragraphe.add_run(texte)
            if couleur:
                run.font.color.rgb = RGBColor.from_string(couleur)
            ancre = nouvel_element
            points += 1

    remplaces = 0
    if ancien_numero is not None:
        remplaces = mettre_a_jour_numero(doc, ancien_numero, nouveau_numero)

    doc.save(chemin_sortie)
    return {"numeros_remplaces": remplaces, "points_ajoutes": points}
