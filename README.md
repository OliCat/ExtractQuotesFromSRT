# Extracteur de Citations pour Podcasts

Application permettant d'extraire automatiquement les moments forts d'un podcast à partir d'un fichier de sous-titres SRT. Elle identifie les passages importants, permet de les éditer, et génère des scripts pour découper la vidéo avec sous-titres incrustés.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-yellow.svg)

## 🌟 Fonctionnalités

- **Interface web intuitive** pour télécharger et traiter les fichiers SRT
- **Extraction intelligente** des moments forts basée sur plusieurs critères :
  - Longueur des passages
  - Mots-clés spécifiques
  - Analyse de sentiment
  - Détection de changements de sujet
- **Regroupement des sous-titres** en passages cohérents et plus longs
- **Édition manuelle** des citations extraites
- **Génération automatique** de scripts de découpage vidéo
- **Incrustation de sous-titres** dans les segments vidéo
- **Exportation multi-formats** : texte, JSON, SRT, scripts FFmpeg

## 📋 Prérequis

- Python 3.6+
- Flask et ses dépendances
- Module `srt` pour le traitement des sous-titres
- Module `textblob` pour l'analyse de sentiment (optionnel)
- FFmpeg (optionnel, pour le découpage vidéo)

## 🚀 Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-utilisateur/extracteur-citations-podcasts.git
cd extracteur-citations-podcasts
```

2. Créer et activer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
# Créer un fichier .env avec les variables suivantes
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=votre_cle_secrete
```

## 💻 Utilisation

L'application peut être utilisée de deux façons différentes :

### 1. Interface Web (Recommandé)

L'interface web offre une expérience complète avec prévisualisation vidéo et édition des extraits.

1. Démarrer l'application :
```bash
flask run
```

2. Ouvrir un navigateur et accéder à `http://localhost:5000`

3. Télécharger un fichier SRT et configurer les paramètres d'extraction

4. Consulter les résultats et éditer les extraits dans l'interface

5. Télécharger votre vidéo complète dans l'éditeur pour prévisualiser les extraits

6. Générer tous les extraits directement depuis l'interface web

### 2. Ligne de commande (Pour utilisateurs avancés)

Cette méthode génère uniquement les scripts FFmpeg que vous devrez exécuter manuellement.

```bash
python extract_srt_quotes.py votre_fichier.srt [options]
```

Options disponibles :
- `-o`, `--output` : Fichier de sortie (par défaut: quotes_output.txt)
- `-n`, `--number` : Nombre de citations à extraire (par défaut: 10)
- `-l`, `--min-length` : Longueur minimale des citations (par défaut: 120)
- `-k`, `--keywords` : Mots-clés à rechercher dans les sous-titres
- `-f`, `--ffmpeg` : Générer un fichier de découpage pour FFmpeg
- `-p`, `--padding` : Padding en secondes pour les segments vidéo (par défaut: 1)
- `-j`, `--json` : Exporter les données au format JSON
- `-s`, `--sentiment` : Utiliser l'analyse de sentiment
- `-t`, `--topic-detection` : Détecter les changements de sujet
- `-g`, `--group-subtitles` : Regrouper les sous-titres en passages cohérents
- `-m`, `--max-gap` : Écart maximal entre sous-titres pour le regroupement (par défaut: 3.0)
- `--no-subtitles` : Ne pas incruster les sous-titres dans les segments vidéo

## 📊 Workflows typiques

### Workflow avec l'interface web

1. Télécharger les sous-titres SRT depuis YouTube ou autre service
2. Importer le fichier SRT dans l'application web
3. Configurer les options d'extraction selon vos besoins
4. Analyser le contenu et visualiser les citations extraites
5. Éditer manuellement les citations pour améliorer leur qualité
6. Télécharger votre vidéo complète dans l'éditeur
7. Prévisualiser et ajuster les extraits avec le lecteur vidéo intégré
8. Personnaliser les options de sous-titres (police, taille, couleur)
9. Générer tous les extraits en un clic directement depuis l'interface

### Workflow avec la ligne de commande

1. Télécharger les sous-titres SRT depuis YouTube ou autre service
2. Exécuter le script Python avec les options souhaitées
3. Éditer manuellement le fichier de sortie si nécessaire
4. Exécuter le script FFmpeg généré pour découper votre vidéo
5. Utiliser les segments vidéo pour créer des capsules pour les réseaux sociaux

## 🔍 Comment ça marche

### Critères de sélection des moments forts

L'application utilise plusieurs critères pour identifier les moments forts :

1. **Longueur du passage** : Les passages plus longs sont souvent plus substantiels
2. **Mots-clés** : Passages contenant des mots-clés spécifiés par l'utilisateur
3. **Analyse de sentiment** : Passages avec une forte charge émotionnelle (positive ou négative)
4. **Changement de sujet** : Points où la conversation change de direction

### Regroupement des sous-titres

Pour créer des passages plus cohérents et plus longs, l'application peut regrouper les sous-titres consécutifs en fonction de :

- L'écart temporel entre les sous-titres (configurable)
- La longueur maximale du passage (pour éviter des extraits trop longs)

### Édition manuelle

L'interface d'édition permet de :

- Corriger les erreurs de transcription
- Améliorer la lisibilité du texte
- Supprimer les hésitations et répétitions
- Générer un fichier SRT propre des citations sélectionnées

### Incrustation de sous-titres

Le script FFmpeg généré peut automatiquement incruster les sous-titres dans les segments vidéo extraits, ce qui les rend immédiatement utilisables pour les réseaux sociaux.

## 🛠️ Développement

Pour contribuer au développement de cette application :

1. Forker le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b nouvelle-fonctionnalite`)
3. Committer vos changements (`git commit -am 'Ajout d'une nouvelle fonctionnalité'`)
4. Pousser vers la branche (`git push origin nouvelle-fonctionnalite`)
5. Créer une Pull Request

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- Développé pour les radios associatives et les créateurs de podcasts
- Utilise Flask, Bootstrap et d'autres bibliothèques open source 