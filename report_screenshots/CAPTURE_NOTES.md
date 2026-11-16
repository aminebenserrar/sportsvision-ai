# SportsVision AI report screenshots

Captured from the running, unchanged application at http://127.0.0.1:8000 using Playwright and headless Microsoft Edge. All predictions were obtained by uploading actual photographs through the application's file input and clicking Analyze Image. No API responses, labels, confidence values, or screenshot pixels were fabricated or edited. The model was not modified or retrained.

## Views and resolution

- `01_homepage.png`: complete homepage captured using a 1440 x 900 desktop viewport. The output is taller than 900 pixels because it includes the entire scrolling page.
- `01_homepage_viewport.png`: additional exact 1440 x 900 homepage viewport.
- `02_upload.png`: image upload interface, 1440 x 900.
- `03_image_preview.png`: selected football photograph before prediction, 1440 x 900.
- `04_football_prediction.png`: real football classification, 1440 x 900.
- `05_basketball_prediction.png`: real basketball classification, 1440 x 900.
- `06_tennis_prediction.png`: real tennis classification, 1440 x 900.
- `07_model_information.png`: model explanation in context, 1440 x 900.
- `08_mobile_view.png`: full responsive page, captured at a 390 x 844 mobile viewport.
- `08_mobile_viewport.png`: additional exact 390 x 844 mobile viewport.

All eight requested views were captured. Full-page images preserve the existing layout and natural page height instead of shrinking text to fit a single screen. Desktop section captures include surrounding content because the application has a continuous page layout. Fonts were allowed to load before capture; animations were allowed to finish.

## Actual predictions

| Input photograph | Predicted sport | Confidence displayed |
| --- | --- | --- |
| Football in Bloomington, Indiana, 1995 | Football | 91.2% |
| USA vs. China, Beijing 2008 Olympics | Basketball | 99% |
| Rafael Nadal, China Open 2009 | Tennis | 91.8% |

`prediction_results.json` records the actual HTTP 200 API responses, including probabilities in the model's original class order. These are three illustrative examples, not a measurement of overall model accuracy or a held-out evaluation. Whether the photos overlap with training data is unknown.

## Photograph credits for your report

Keep these credits with the corresponding figures when reusing the photographs in your report. Images were displayed scaled within the application's preview; no creative edits were applied during capture. Football and basketball input copies were taken from the existing Downloads folder. Tennis was downloaded from Wikimedia Commons. These licenses apply to the respective embedded photographs.

### Football (screenshots 03 and 04)

Rick Dikeman (Rdikeman), *Football in Bloomington, Indiana, 1995*.

Source: https://commons.wikimedia.org/wiki/File:Football_in_Bloomington,_Indiana,_1995.jpg

License: Creative Commons Attribution-ShareAlike 3.0 Unported, https://creativecommons.org/licenses/by-sa/3.0/

### Basketball (screenshot 05)

kris krüg, *USA vs. China Mens Basketball - Beijing 2008 Olympic Games*.

Source: https://commons.wikimedia.org/wiki/File:USA_vs._China_Mens_Basketball_-_Beijing_2008_Olympic_Games_(2751923597).jpg

License: Creative Commons Attribution-ShareAlike 2.0 Generic, https://creativecommons.org/licenses/by-sa/2.0/

### Tennis (screenshot 06)

IvanWalsh.com, *Rafael Nadal (4132943958)*, China Tennis Open, 6 October 2009.

Source: https://commons.wikimedia.org/wiki/File:Rafael_Nadal_(4132943958).jpg

License: Creative Commons Attribution 2.0 Generic, https://creativecommons.org/licenses/by/2.0/

## Reproduction

The application was already running with its model ready and was left running. Playwright was installed into the existing `.venv` solely for browser capture; application source, requirements, model, and design were not edited. The integrated browser tool failed to initialize, so standalone Playwright was used.

Input photographs and the capture script are in the project-level `report_assets` folder. To reproduce with the app running and Microsoft Edge installed:

```powershell
.\.venv\Scripts\python.exe report_assets/capture_screenshots.py
```
