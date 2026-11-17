# Rapport SportsVision AI — édition EMSI / 5e année

**Auteur :** Mohamed Amine Bensserrar  
**Formation :** 5e année, Ingénierie Informatique et Réseaux (EMSI)  
**Année universitaire :** 2026–2027

## Livrables

- `rapport_sportsvision.tex` : source LaTeX complète, édition mise en forme selon le rapport SONACOS de référence.
- `rapport_sportsvision.pdf` : PDF généré automatiquement par GitHub Actions après compilation réussie.
- Les captures réelles de SportsVision AI sont référencées depuis `../report_screenshots/`.
- Les logos d'établissement sont préparés dans `report_assets/` par le script `prepare_logos.py` au cours de la compilation.

## Style éditorial

Page de couverture académique avec EMSI / Honoris, 5e année et auteur complet ; titres et bandeaux verts ; en-têtes et pieds de page ; dédicaces ; remerciements ; résumés français et anglais ; liste des figures ; liste des tableaux ; liste des abréviations ; sommaire ; 7 chapitres ; captures de l'application ; annexes et bibliographie.

Le contenu scientifique conserve les nombres d'images d'entraînement, validation et test, les hyperparamètres MobileNetV2, les résultats observés, l'architecture FastAPI et les précautions liées à la taille réduite de l'échantillon de test.

## Compilation locale

Avec une distribution TeX complète, depuis la racine du dépôt :

```bash
python rapport/prepare_logos.py
cd rapport
pdflatex -interaction=nonstopmode -halt-on-error rapport_sportsvision.tex
pdflatex -interaction=nonstopmode -halt-on-error rapport_sportsvision.tex
```

## Compilation automatique sur GitHub

Le workflow `.github/workflows/build-sportsvision-report.yml` prépare les logos, exécute LaTeX, publie le PDF comme artefact et tente de l'enregistrer dans `rapport/` pour le téléchargement direct.

**Sources des logos :** site officiel EMSI et logo Honoris sur Wikimedia Commons. Les photographies sportives visibles dans les captures sont créditées en annexe et dans `report_screenshots/CAPTURE_NOTES.md`.
