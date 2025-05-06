# Guide de contribution

Merci de votre intérêt pour contribuer à l'Extracteur de Citations pour Podcasts ! Ce document vous guidera à travers le processus de contribution.

## Structure des branches

Ce projet suit un modèle de flux Git inspiré de Gitflow :

- `main` : Branche de production stable
- `develop` : Branche principale de développement
- `feature/*` : Branches pour les nouvelles fonctionnalités
- `bugfix/*` : Branches pour les corrections de bugs
- `hotfix/*` : Branches pour les correctifs urgents

## Processus de contribution

### 1. Configuration initiale

1. Forkez le dépôt
2. Clonez votre fork :
   ```bash
   git clone https://github.com/votre-username/extracteur-citations-podcasts.git
   cd extracteur-citations-podcasts
   ```
3. Ajoutez le dépôt d'origine comme remote :
   ```bash
   git remote add upstream https://github.com/username-original/extracteur-citations-podcasts.git
   ```
4. Basculez sur la branche develop :
   ```bash
   git checkout develop
   ```

### 2. Développement

1. Synchronisez votre branche develop avec le dépôt d'origine :
   ```bash
   git pull upstream develop
   ```
2. Créez une branche pour votre fonctionnalité ou correction :
   ```bash
   git checkout -b feature/ma-nouvelle-fonctionnalite
   # ou
   git checkout -b bugfix/correction-bug
   ```
3. Développez et testez votre code
4. Committez vos changements avec des messages clairs :
   ```bash
   git commit -m "Feature: Ajout de la fonctionnalité X qui permet Y"
   ```

### 3. Soumission

1. Poussez votre branche vers votre fork :
   ```bash
   git push origin feature/ma-nouvelle-fonctionnalite
   ```
2. Créez une Pull Request vers la branche `develop` du dépôt d'origine
3. Décrivez clairement vos changements dans la PR

## Conventions de code

### Style de code

- Suivez PEP 8 pour le code Python
- Utilisez des noms de variables et fonctions explicites en français
- Documentez vos fonctions avec des docstrings
- Utilisez des commentaires pour expliquer le "pourquoi", pas le "comment"

### Messages de commit

Format recommandé :
```
Type: Description courte (50 caractères max)

Description détaillée si nécessaire. Limitez les lignes à 72 caractères.
Expliquez le problème résolu et pourquoi cette approche a été choisie.

Issue: #123
```

Types de commit :
- `Feature:` Nouvelle fonctionnalité
- `Fix:` Correction de bug
- `Docs:` Documentation
- `Style:` Formatage, indentation, etc.
- `Refactor:` Restructuration du code sans changement de comportement
- `Test:` Ajout ou modification de tests
- `Chore:` Maintenance générale, dépendances, etc.

## Tests

- Testez vos modifications localement avant de soumettre une PR
- Si vous ajoutez une nouvelle fonctionnalité, incluez des tests appropriés

## Documentation

- Mettez à jour la documentation si votre contribution change le comportement de l'application
- Documentez les nouvelles fonctionnalités dans le README.md

## Rapport de bugs et suggestions

- Utilisez l'onglet Issues pour signaler des bugs ou proposer des améliorations
- Utilisez les templates fournis pour assurer la cohérence des rapports

Merci de contribuer à améliorer cet outil pour les radios associatives et les créateurs de podcasts ! 