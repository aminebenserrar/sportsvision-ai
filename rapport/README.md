# Rapport LaTeX — SportsVision AI

Ce dossier contient le rapport académique complet en français : `rapport_sportsvision.tex`.

## Compiler avec les images

Le fichier LaTeX utilise directement les images présentes dans `../report_screenshots/`, déjà incluses dans ce dépôt.

### Overleaf

1. Télécharger le dépôt GitHub en ZIP (bouton **Code > Download ZIP**).
2. Sur Overleaf, créer un nouveau projet avec **Upload Project** et sélectionner le ZIP.
3. Ouvrir `rapport/rapport_sportsvision.tex` et le définir comme **Main Document**.
4. Compiler avec **pdfLaTeX**. Si les chemins des images ne sont pas résolus depuis le dossier de compilation, déplacer le fichier .tex à la racine et remplacer `../report_screenshots/` par `report_screenshots/` dans la macro `\photo`.

### Compilation locale (TeX Live ou MiKTeX)

Dans un terminal à la racine du dépôt :

```bash
cd rapport
pdflatex -interaction=nonstopmode rapport_sportsvision.tex
pdflatex -interaction=nonstopmode rapport_sportsvision.tex
```

Le PDF est produit à l'emplacement `rapport/rapport_sportsvision.pdf`.

## Personnalisation

- Compléter l'établissement et le nom de l'encadrant sur la page de garde.
- Les résultats de l'application proviennent du fichier `report_screenshots/prediction_results.json`.
- Les chiffres du test CNN proviennent de la session d'entraînement antérieure (15 images de test). Le rapport explique explicitement que ces 15 images ne suffisent pas à prouver une exactitude générale de 100 %.
- Les photographies tierces employées pour les démonstrations sont créditées en annexe.

Les captures d'écran sont les fichiers réels du dossier `report_screenshots/`. Le document n'invente pas de captures.
