"""Appli « MH2O · Comptes rendus » — lancer avec :  streamlit run app.py"""
from datetime import date

import streamlit as st

import config
import db
import ia
import stockage
import word
from config import COULEUR_NOUVEAUX_POINTS, NOM_APPLI

st.set_page_config(page_title=NOM_APPLI, page_icon="📋", layout="wide")


@st.cache_resource
def demarrage():
    """Crée les tables et le compartiment de fichiers au premier lancement (une seule fois)."""
    db.initialiser()
    stockage.initialiser()
    return True


try:
    demarrage()
except Exception as erreur:
    st.error("Connexion au stockage impossible. Vérifiez les Secrets (SUPABASE_DB_URL, SUPABASE_URL, "
             f"SUPABASE_SECRET_KEY).\n\nDétail : {erreur}")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def fichier(cle):
    return stockage.lire(cle)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { background: #1F3864; }
    [data-testid="stSidebar"] * { color: #FFFFFF; }
    [data-testid="stSidebar"] button { background: rgba(255,255,255,0.08); border: none; text-align: left; }
    .stButton button[kind="primary"] { background: #E8A020; color: #14213D; border: none; font-weight: 600; }
    .badge { font-size: 0.8rem; font-weight: 600; padding: 2px 10px; border-radius: 999px; }
    .Diffusé { background: #E3F1E6; color: #1E5E2F; }
    .Validé { background: #DDEBF7; color: #1F3864; }
    .Brouillon { background: #FDF1DC; color: #7A4B00; }
    </style>
    """,
    unsafe_allow_html=True,
)

etat = st.session_state
etat.setdefault("utilisateur", None)
etat.setdefault("page", "chantiers")
etat.setdefault("chantier_id", None)
etat.setdefault("ajouts", [])  # points en attente pour le nouveau CR
etat.setdefault("proposition", None)


def aller(page, chantier_id=None):
    etat.page = page
    if chantier_id is not None:
        etat.chantier_id = chantier_id
    st.rerun()


def badge(statut):
    return f'<span class="badge {statut}">{statut}</span>'


def date_fr(iso):
    try:
        a, m, j = iso.split("-")
        return f"{j}/{m}/{a}"
    except ValueError:
        return iso


# =====================================================================
# Premier lancement : création du compte administrateur
# =====================================================================
if db.nb_utilisateurs() == 0:
    st.title(NOM_APPLI)
    st.subheader("Premier lancement : créez le compte administrateur")
    with st.form("premier_admin"):
        nom = st.text_input("Nom et prénom")
        email = st.text_input("E-mail professionnel")
        mdp = st.text_input("Mot de passe (8 caractères minimum)", type="password")
        mdp2 = st.text_input("Confirmer le mot de passe", type="password")
        if st.form_submit_button("Créer le compte", type="primary"):
            if not (nom and email and mdp):
                st.error("Tous les champs sont obligatoires.")
            elif len(mdp) < 8:
                st.error("Le mot de passe doit faire au moins 8 caractères.")
            elif mdp != mdp2:
                st.error("Les deux mots de passe ne correspondent pas.")
            else:
                db.creer_utilisateur(nom, email, mdp, role="admin")
                st.success("Compte créé. Vous pouvez vous connecter.")
                st.rerun()
    st.stop()

# =====================================================================
# Connexion
# =====================================================================
if etat.utilisateur is None:
    _, centre, _ = st.columns([1, 1.2, 1])
    with centre:
        st.title(NOM_APPLI)
        st.caption("Espace réservé aux équipes MOEX / OPC")
        with st.form("connexion"):
            email = st.text_input("Adresse e-mail professionnelle")
            mdp = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter", type="primary", use_container_width=True):
                u = db.authentifier(email, mdp)
                if u:
                    etat.utilisateur = u
                    st.rerun()
                else:
                    st.error("E-mail ou mot de passe incorrect.")
        st.caption("Chaque utilisateur ne voit que les chantiers qui lui sont attribués. "
                   "Les comptes sont créés par l'administrateur.")
    st.stop()

utilisateur = etat.utilisateur
est_admin = utilisateur["role"] == "admin"

# =====================================================================
# Menu latéral
# =====================================================================
with st.sidebar:
    st.markdown(f"### {NOM_APPLI}")
    st.write("")
    if st.button("🏗️  Mes chantiers", use_container_width=True):
        aller("chantiers")
    if st.button("🔎  Recherche", use_container_width=True):
        aller("recherche")
    if est_admin and st.button("⚙️  Administration", use_container_width=True):
        aller("admin")
    if st.button("🔑  Mon mot de passe", use_container_width=True):
        aller("mot_de_passe")
    st.divider()
    st.write(f"**{utilisateur['nom']}**")
    st.caption("Administrateur" if est_admin else "Utilisateur")
    if st.button("Déconnexion", use_container_width=True):
        for cle in list(etat.keys()):
            del etat[cle]
        st.rerun()
    if config.mode_supabase():
        st.caption("☁️ Données enregistrées sur Supabase.")
    else:
        st.caption("💾 Mode local : données enregistrées sur cet appareil uniquement.")
    if ia.mode_demo():
        st.caption("⚠️ Mode démo : aucune clé d'API IA configurée, la reformulation est simplifiée.")


# =====================================================================
# Pages
# =====================================================================
def page_chantiers():
    haut_g, haut_d = st.columns([3, 1])
    haut_g.title("Mes chantiers")
    haut_g.caption("Tous les comptes rendus, rangés par chantier.")
    chantiers = db.chantiers_visibles(utilisateur)
    if not chantiers:
        st.info("Aucun chantier pour l'instant." + (" Créez-en un dans Administration." if est_admin
                                                     else " Demandez à l'administrateur de vous en attribuer un."))
        return
    colonnes = st.columns(3)
    for i, c in enumerate(chantiers):
        with colonnes[i % 3].container(border=True):
            st.markdown(f"#### {c['nom']}")
            st.caption(f"{c['ville'] or '—'} · {c['statut']}")
            dernier = f"n°{c['dernier_numero']}" if c["dernier_numero"] else "aucun"
            st.write(f"Dernier CR : **{dernier}**")
            st.caption("Rédaction" if c["droit"] == "redaction" else "Lecture seule")
            if st.button("Voir les comptes rendus →", key=f"ouvrir_{c['id']}", use_container_width=True):
                aller("chantier", c["id"])


def page_chantier():
    cid = etat.chantier_id
    c = db.chantier(cid)
    droit = db.droit_sur_chantier(utilisateur, cid)
    if not c or not droit:
        st.error("Chantier introuvable ou accès refusé.")
        return
    if st.button("← Mes chantiers"):
        aller("chantiers")
    crs = db.crs_du_chantier(cid)

    g, d = st.columns([3, 1])
    g.title(c["nom"])
    g.caption(" · ".join(x for x in [c["ville"], f"Maître d'ouvrage : {c['maitre_ouvrage']}" if c["maitre_ouvrage"] else "", c["statut"]] if x))
    if droit == "redaction" and crs:
        if d.button(f"+ Nouveau CR (n°{crs[0]['numero'] + 1})", type="primary", use_container_width=True):
            etat.ajouts = []
            etat.proposition = None
            aller("nouveau_cr", cid)

    onglets = ["Comptes rendus", "Équipe"] + (["Importer un CR existant"] if droit == "redaction" else [])
    tabs = st.tabs(onglets)

    with tabs[0]:
        if not crs:
            st.info("Aucun CR pour ce chantier. Commencez par importer le dernier CR Word existant "
                    "(onglet « Importer un CR existant ») : il servira de base au suivant.")
        for cr in crs:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 2, 2, 3])
                c1.markdown(f"**n°{cr['numero']}**")
                c2.write(date_fr(cr["date_reunion"]))
                c3.markdown(f"{cr['auteur'] or '—'}<br>{badge(cr['statut'])}", unsafe_allow_html=True)
                with c4:
                    try:
                        st.download_button("Télécharger (Word)", fichier(cr["fichier"]),
                                           file_name=f"{c['nom']}_CR_{cr['numero']:03d}.docx",
                                           key=f"dl_{cr['id']}", use_container_width=True)
                    except Exception:
                        st.warning("Fichier introuvable")
                    if droit == "redaction":
                        if cr["statut"] == "Brouillon" and st.button("Valider", key=f"val_{cr['id']}", use_container_width=True):
                            db.changer_statut_cr(cr["id"], "Validé")
                            st.rerun()
                        if cr["statut"] == "Validé" and st.button("Marquer comme diffusé", key=f"dif_{cr['id']}", use_container_width=True):
                            db.changer_statut_cr(cr["id"], "Diffusé")
                            st.rerun()
                        if cr["statut"] == "Brouillon" and cr is crs[0]:
                            if st.button("Supprimer ce brouillon", key=f"sup_{cr['id']}", use_container_width=True):
                                stockage.supprimer(db.supprimer_cr(cr["id"]))
                                st.rerun()

    with tabs[1]:
        equipe = db.equipe_chantier(cid)
        if not equipe:
            st.caption("Aucun membre attribué (l'administrateur voit tous les chantiers).")
        for m in equipe:
            st.write(f"**{m['nom']}** — {m['email']} — {'rédaction' if m['droit'] == 'redaction' else 'lecture'}")

    if droit == "redaction":
        with tabs[2]:
            st.caption("Importez un CR Word déjà rédigé (par exemple le dernier CR envoyé). "
                       "L'appli s'en servira comme base pour le CR suivant.")
            with st.form("import_cr", clear_on_submit=True):
                televerse = st.file_uploader("Fichier Word (.docx)", type=["docx"])
                numero = st.number_input("Numéro du CR", min_value=1, step=1,
                                         value=(crs[0]["numero"] + 1) if crs else 1)
                date_reu = st.date_input("Date de la réunion", value=date.today(), format="DD/MM/YYYY")
                statut = st.selectbox("Statut", ["Diffusé", "Validé", "Brouillon"])
                if st.form_submit_button("Importer", type="primary"):
                    if not televerse:
                        st.error("Choisissez un fichier .docx.")
                    elif any(x["numero"] == numero for x in crs):
                        st.error(f"Le CR n°{numero} existe déjà pour ce chantier.")
                    else:
                        contenu = televerse.getvalue()
                        try:
                            texte = word.extraire_texte(contenu)
                        except Exception:
                            st.error("Ce fichier Word n'a pas pu être lu. Vérifiez qu'il s'agit bien d'un .docx.")
                        else:
                            cle = stockage.enregistrer(cid, int(numero), contenu)
                            db.ajouter_cr(cid, int(numero), date_reu.isoformat(), utilisateur["id"], statut, cle, texte)
                            st.success(f"CR n°{numero} importé.")
                            st.rerun()


def page_nouveau_cr():
    cid = etat.chantier_id
    c = db.chantier(cid)
    if db.droit_sur_chantier(utilisateur, cid) != "redaction":
        st.error("Vous n'avez pas le droit de rédaction sur ce chantier.")
        return
    base = db.dernier_cr(cid)
    if not base:
        st.warning("Importez d'abord un CR existant pour ce chantier.")
        return
    numero = base["numero"] + 1

    if st.button(f"← {c['nom']}"):
        aller("chantier", cid)
    st.title(f"Nouveau CR n°{numero}")
    st.caption(f"Basé sur le CR n°{base['numero']} · trame Word conservée")

    try:
        contenu_base = fichier(base["fichier"])
        sections = word.lister_sections(contenu_base)
    except Exception as e:
        st.error(f"Impossible de lire le CR n°{base['numero']} : {e}")
        return
    if not sections:
        st.error("Aucune section (titre) n'a été détectée dans le CR précédent. "
                 "Les titres doivent utiliser un style « Titre » de Word ou être en gras.")
        return

    date_reu = st.date_input("Date de la réunion", value=date.today(), format="DD/MM/YYYY")
    gauche, droite = st.columns(2)

    with gauche:
        with st.container(border=True):
            st.subheader("1. Notes de réunion")
            libelles = [("— " * (s["niveau"] - 1) if s["niveau"] < 9 else "") + s["titre"] for s in sections]
            idx = st.selectbox("Section du CR", range(len(sections)), format_func=lambda i: libelles[i])
            notes = st.text_area("Notes brutes", height=180,
                                 placeholder="ex. : plans exe pas reçus, relancer, attendu sem pro",
                                 help="Astuce dictée : sous Windows, appuyez sur Windows + H pour dicter vos notes.")
            st.caption("🎤 Pour dicter : Windows + H (Windows) ou touche Fn deux fois (Mac). "
                       "Ne saisissez ni montants ni données personnelles.")
            if st.button("Reformuler avec l'IA", type="primary", use_container_width=True, disabled=not notes.strip()):
                with st.spinner("Reformulation en cours…"):
                    try:
                        points = ia.reformuler(notes, sections[idx]["titre"])
                        etat.proposition = {"section_index": idx, "texte": "\n".join(points)}
                    except Exception as e:
                        st.error(f"L'IA n'a pas répondu : {e}")

    with droite:
        with st.container(border=True):
            st.subheader("2. Relecture")
            prop = etat.proposition
            if not prop:
                st.caption("Saisissez vos notes puis cliquez sur « Reformuler avec l'IA ».")
            else:
                st.caption(f"Section : **{sections[prop['section_index']]['titre']}** — un point par ligne, modifiable.")
                texte = st.text_area("Texte proposé", value=prop["texte"], height=180, key=f"prop_{hash(prop['texte'])}")
                st.warning("Texte proposé par l'IA : relisez-le. Vous restez responsable du contenu.")
                if st.button("Ajouter au CR", type="primary", use_container_width=True):
                    etat.ajouts.append({"section_index": prop["section_index"],
                                        "textes": [l for l in texte.splitlines() if l.strip()]})
                    etat.proposition = None
                    st.rerun()

    st.subheader("3. Points ajoutés au CR")
    if not etat.ajouts:
        st.caption("Aucun point pour l'instant.")
    for i, a in enumerate(etat.ajouts):
        with st.container(border=True):
            st.markdown(f"**{sections[a['section_index']]['titre']}**")
            for t in a["textes"]:
                st.write(f"• {t}")
            if st.button("Retirer", key=f"retirer_{i}"):
                etat.ajouts.pop(i)
                st.rerun()

    if st.button(f"Générer le CR n°{numero}", type="primary", disabled=not etat.ajouts):
        nouveau, bilan = word.generer_cr(contenu_base, etat.ajouts, base["numero"], numero,
                                         couleur=COULEUR_NOUVEAUX_POINTS)
        cle = stockage.enregistrer(cid, numero, nouveau)
        db.ajouter_cr(cid, numero, date_reu.isoformat(), utilisateur["id"], "Brouillon", cle,
                      word.extraire_texte(nouveau))
        etat.ajouts = []
        st.success(f"CR n°{numero} enregistré en brouillon : {bilan['points_ajoutes']} point(s) ajouté(s), "
                   f"numéro mis à jour à {bilan['numeros_remplaces']} endroit(s).")
        if bilan["numeros_remplaces"] == 0:
            st.info("Le numéro du CR n'a pas été trouvé dans le document : pensez à le modifier à la main.")
        st.download_button("Télécharger le CR (Word)", nouveau,
                           file_name=f"{c['nom']}_CR_{numero:03d}.docx")
        st.caption("Relisez-le dans Word (dates, présents, planning), puis validez-le depuis la page du chantier.")


def page_recherche():
    st.title("Recherche")
    terme = st.text_input("Mot à chercher dans les CR (ex. : étanchéité, réservations, plans d'exécution)")
    if terme:
        resultats = db.rechercher(utilisateur, terme)
        st.caption(f"{len(resultats)} résultat(s)")
        for r in resultats:
            texte = r["texte"] or ""
            pos = texte.lower().find(terme.lower())
            extrait = texte[max(0, pos - 80): pos + 120].replace("\n", " ") if pos >= 0 else ""
            with st.container(border=True):
                g, d = st.columns([4, 1])
                g.markdown(f"**{r['chantier']}** — CR n°{r['numero']} du {date_fr(r['date_reunion'])}")
                g.caption(f"…{extrait}…")
                if d.button("Ouvrir le chantier", key=f"rech_{r['id']}"):
                    aller("chantier", r["chantier_id"])


def page_mot_de_passe():
    st.title("Mon mot de passe")
    with st.form("mdp", clear_on_submit=True):
        actuel = st.text_input("Mot de passe actuel", type="password")
        nouveau = st.text_input("Nouveau mot de passe (8 caractères minimum)", type="password")
        nouveau2 = st.text_input("Confirmer", type="password")
        if st.form_submit_button("Changer", type="primary"):
            if not db.authentifier(utilisateur["email"], actuel):
                st.error("Mot de passe actuel incorrect.")
            elif len(nouveau) < 8 or nouveau != nouveau2:
                st.error("Le nouveau mot de passe doit faire 8 caractères minimum et être confirmé.")
            else:
                db.changer_mot_de_passe(utilisateur["id"], nouveau)
                st.success("Mot de passe modifié.")


def page_admin():
    if not est_admin:
        st.error("Réservé à l'administrateur.")
        return
    st.title("Administration")
    t_users, t_chantiers, t_acces, t_sauvegarde = st.tabs(["Utilisateurs", "Chantiers", "Accès", "Sauvegarde"])

    with t_users:
        with st.form("nouvel_utilisateur", clear_on_submit=True):
            st.subheader("Créer un compte")
            nom = st.text_input("Nom et prénom")
            email = st.text_input("E-mail")
            mdp = st.text_input("Mot de passe provisoire (8 caractères minimum)", type="password")
            role = st.selectbox("Rôle", ["utilisateur", "admin"])
            if st.form_submit_button("Créer", type="primary"):
                if not (nom and email and len(mdp) >= 8):
                    st.error("Nom, e-mail et mot de passe (8 caractères min.) obligatoires.")
                else:
                    try:
                        db.creer_utilisateur(nom, email, mdp, role)
                        st.success(f"Compte créé pour {nom}. Communiquez-lui son mot de passe provisoire.")
                    except Exception:
                        st.error("Cet e-mail existe déjà.")
        st.subheader("Comptes existants")
        for u in db.liste_utilisateurs():
            g, d = st.columns([4, 1])
            g.write(f"**{u['nom']}** — {u['email']} — {u['role']}" + ("" if u["actif"] else " — *désactivé*"))
            if u["id"] != utilisateur["id"]:
                libelle = "Désactiver" if u["actif"] else "Réactiver"
                if d.button(libelle, key=f"act_{u['id']}"):
                    db.activer_utilisateur(u["id"], not u["actif"])
                    st.rerun()

    with t_chantiers:
        with st.form("nouveau_chantier", clear_on_submit=True):
            st.subheader("Créer un chantier")
            nom = st.text_input("Nom du chantier")
            ville = st.text_input("Ville")
            moa = st.text_input("Maître d'ouvrage")
            if st.form_submit_button("Créer", type="primary"):
                if not nom:
                    st.error("Le nom est obligatoire.")
                else:
                    db.creer_chantier(nom, ville, moa)
                    st.success(f"Chantier « {nom} » créé.")
        st.subheader("Chantiers existants")
        for ch in db.tous_les_chantiers():
            g, d = st.columns([4, 1])
            g.write(f"**{ch['nom']}** — {ch['ville'] or '—'}")
            statuts = ["En cours", "Réceptionné", "Archivé"]
            nouveau = d.selectbox("Statut", statuts, index=statuts.index(ch["statut"]) if ch["statut"] in statuts else 0,
                                  key=f"st_{ch['id']}", label_visibility="collapsed")
            if nouveau != ch["statut"]:
                db.modifier_statut_chantier(ch["id"], nouveau)
                st.rerun()

    with t_acces:
        users = [u for u in db.liste_utilisateurs() if u["role"] != "admin" and u["actif"]]
        chantiers = db.tous_les_chantiers()
        if not users or not chantiers:
            st.info("Créez d'abord au moins un utilisateur (non admin) et un chantier.")
        else:
            with st.form("acces"):
                u = st.selectbox("Utilisateur", users, format_func=lambda x: x["nom"])
                ch = st.selectbox("Chantier", chantiers, format_func=lambda x: x["nom"])
                droit = st.radio("Droit", ["redaction", "lecture"], horizontal=True,
                                 format_func=lambda x: "Rédaction" if x == "redaction" else "Lecture seule")
                g, d = st.columns(2)
                if g.form_submit_button("Donner l'accès", type="primary"):
                    db.donner_acces(u["id"], ch["id"], droit)
                    st.success(f"{u['nom']} a maintenant accès à {ch['nom']}.")
                if d.form_submit_button("Retirer l'accès"):
                    db.retirer_acces(u["id"], ch["id"])
                    st.success("Accès retiré.")

    with t_sauvegarde:
        st.caption("Téléchargez une copie complète (base + tous les fichiers Word). "
                   "À faire régulièrement et à conserver sur un autre support.")
        if st.button("Préparer la sauvegarde"):
            with st.spinner("Préparation…"):
                contenu_zip = stockage.sauvegarde_zip(db.exporter_tout())
            st.download_button("Télécharger la sauvegarde (.zip)", contenu_zip,
                               file_name=f"sauvegarde_CR_{date.today().isoformat()}.zip")


PAGES = {
    "chantiers": page_chantiers,
    "chantier": page_chantier,
    "nouveau_cr": page_nouveau_cr,
    "recherche": page_recherche,
    "mot_de_passe": page_mot_de_passe,
    "admin": page_admin,
}
PAGES.get(etat.page, page_chantiers)()
