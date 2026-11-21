# MH2O · Comptes rendus — version 1

Application web pour rédiger, ranger et retrouver les comptes rendus (CR) de réunion de chantier.
Chaque MOEX / OPC se connecte avec son compte et ne voit que ses chantiers.

## Ce que fait la version 1

- **Comptes et accès** : connexion par e-mail et mot de passe (mot de passe jamais stocké en clair). L'administrateur crée les comptes et donne à chacun un accès « rédaction » ou « lecture seule » par chantier.
- **Chantiers** : un espace par chantier, avec tous ses CR rangés par numéro.
- **Import** : on importe le dernier CR Word existant, qui sert de base au suivant.
- **Nouveau CR** :
  1. L'appli reprend le CR précédent et liste ses sections (titres).
  2. Vous choisissez une section et tapez ou dictez vos notes brutes.
  3. L'IA les reformule dans le style CR. Vous relisez et corrigez.
  4. L'appli génère le nouveau Word : même trame, numéro mis à jour, nouveaux points ajoutés en fin de section (en bleu pour les repérer).
- **Statuts** : Brouillon → Validé → Diffusé.
- **Recherche** dans le texte de tous les CR de vos chantiers.
- **Sauvegarde** : l'administrateur télécharge une copie complète (base + fichiers) en un clic.

## Installation sur un PC (Windows), une seule fois

1. Installez **Python** (version 3.10 ou plus) depuis python.org. Pendant l'installation, cochez **« Add Python to PATH »**.
2. Dézippez le dossier `app_cr` où vous voulez (par exemple dans Documents).
3. Ouvrez le dossier, cliquez dans la barre d'adresse de l'explorateur, tapez `cmd`, puis appuyez sur Entrée. Une fenêtre noire s'ouvre dans le dossier.
4. Tapez la commande suivante, puis appuyez sur Entrée :
   ```
   pip install -r requirements.txt
   ```

## Lancer l'appli

Double-cliquez sur **Lancer_appli.bat**, ou tapez dans la fenêtre noire ouverte dans le dossier :
```
streamlit run app.py
```
L'appli s'ouvre dans le navigateur (adresse `http://localhost:8501`). Au premier lancement, elle demande de créer le compte administrateur.

Pour l'arrêter, fermez la fenêtre noire.

## Activer l'IA (clé d'API Claude)

Sans clé, l'appli fonctionne en **mode démo** : elle met seulement les notes en forme, sans les reformuler.

1. Créez une clé sur console.anthropic.com. Le service est payant à l'usage, comptez quelques euros par mois pour une équipe.
2. Dans le dossier `app_cr`, créez un dossier `.streamlit`, et dedans un fichier `secrets.toml` contenant :
   ```
   ANTHROPIC_API_KEY = "votre-clé-ici"
   ```
3. Relancez l'appli.

⚠️ Ne partagez jamais cette clé et ne l'envoyez pas par mail.

## Premiers pas

1. Connectez-vous avec le compte administrateur.
2. **Administration › Chantiers** : créez le chantier (ex. L'ECLAT 78).
3. **Administration › Utilisateurs** : créez les comptes de vos collègues.
4. **Administration › Accès** : donnez à chacun l'accès à ses chantiers.
5. Ouvrez le chantier, onglet **Importer un CR existant** : importez le dernier CR Word (ex. le n°112).
6. Cliquez sur **+ Nouveau CR (n°113)**.

## Où sont les données ?

Tout est dans le dossier `donnees`, à côté de `app.py` :
- `appli_cr.db` : la base (comptes, chantiers, liste des CR) ;
- `fichiers/chantier_X/CR_113.docx` : les fichiers Word, un dossier par chantier.

**Faites une sauvegarde régulière** (Administration › Sauvegarde) et gardez-la sur un autre support.

## Utiliser l'appli à plusieurs

Lancée sur votre PC, l'appli n'est accessible que depuis ce PC. Pour que toute l'équipe l'utilise, il faut l'installer sur un serveur. Deux possibilités :
- un **serveur interne MH2O** (à voir avec l'informatique) : les autres y accèdent par le réseau de l'entreprise ;
- un **hébergeur en Europe** (par exemple un petit serveur virtuel à environ 5 à 10 € par mois), avec une adresse en HTTPS.

Cette décision est à valider avec la direction et l'informatique, car elle concerne la sécurité des données.

## Limites connues (pistes pour la version 2)

- **Détection des sections** : l'appli repère les titres qui utilisent un style « Titre » de Word ou qui sont entièrement en gras. Si votre trame est différente, il faudra ajuster `word.py`.
- **Ajouts dans les tableaux** : les nouveaux points s'ajoutent sous forme de paragraphes en fin de section, pas encore dans les lignes des tableaux.
- **Numéro du CR** : l'appli remplace « n°112 » par « n°113 » partout, en-têtes compris. Vérifiez les phrases qui citent volontairement l'ancien numéro (ex. « le CR n°112 est approuvé »).
- **Pas encore inclus** : diffusion automatique par mail, export PDF, dictée intégrée. Pour l'instant, la dictée passe par Windows + H.
- À relire avant chaque diffusion : dates, présents, planning, échéances.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `app.py` | Les écrans de l'appli (Streamlit) |
| `db.py` | La base de données (utilisateurs, chantiers, accès, CR) |
| `word.py` | Lecture du CR précédent et génération du nouveau Word |
| `ia.py` | La reformulation par l'IA (consignes de rédaction incluses) |
| `stockage.py` | Le rangement des fichiers par chantier et la sauvegarde |
| `auth.py` | La sécurité des mots de passe |
| `config.py` | Les réglages (dossier des données, modèle d'IA, couleur des ajouts) |
