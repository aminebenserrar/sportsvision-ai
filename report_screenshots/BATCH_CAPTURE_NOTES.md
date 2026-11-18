# Automatic Sports Image Organization — capture and test results

Captured on 18 November 2026 from the existing application running at http://127.0.0.1:8001. Browser automation used Playwright with Microsoft Edge. The integrated browser connection failed to initialize, so standalone Playwright was used. Application source and the trained model were not changed for these captures.

## Screenshots

- `09_batch_upload.png`: three real sports photographs selected, before classification. The existing interface shows the selected count and total size; it does not show thumbnails until classification completes.
- `10_organized_gallery.png`: actual model results, with one image in each category, thumbnails, confidence values, and counts.
- `11_zip_download.png`: a real browser screenshot of a separate, explicitly labeled report evidence viewer. Its left pane embeds the live application after clicking Download Organized ZIP. Its right pane lists paths and sizes read directly from the downloaded ZIP. This viewer is not a feature of the application, and no prediction values were injected or simulated.
- `12_batch_mobile.png`: the complete organizer section at a 390 x 844 mobile viewport, after real classification and ZIP download.

Desktop application captures use a 1440 x 1000 viewport and capture the organizer element at its natural size; output dimensions therefore vary. The ZIP evidence screenshot captures the entire 1440 x 1000 viewport. The mobile image captures the full organizer section, so it is taller than the viewport. No screenshot pixels were edited or composited.

## Real predictions

| Photograph | Predicted class | Displayed confidence | Count |
| --- | --- | --- | --- |
| basketball.jpg | Basketball | 99% | 1 |
| football.jpg | Football | 91.2% | 1 |
| tennis.jpg | Tennis | 91.8% | 1 |

The original photos are in `report_assets/`. Their authors, source pages, and licenses are documented in [CAPTURE_NOTES.md](CAPTURE_NOTES.md). Preserve those credits when using the figures. These are illustrative examples, not a measurement of test-set accuracy.

`batch_prediction_results.json` contains the actual API response. `batch_zip_verification.json` contains the downloaded archive's SHA-256 and real entry sizes. The ZIP integrity check passed, and every archived photo was compared byte for byte with its original input. The archive contains:

```text
basketball/
  001_basketball.jpg
football/
  002_football.jpg
tennis/
  003_tennis.jpg
```

Downloaded evidence archives are retained locally in ignored `test_artifacts/`. No uploaded image was permanently saved by the application server.

## Test run

Command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

All 5 backend integration tests passed in 12.134 seconds:

1. `test_dimensions_animation_and_single_error_regression` — passed.
2. `test_limits_and_all_invalid_batch` — passed.
3. `test_partial_failures_and_original_bytes_in_zip` — passed.
4. `test_png_webp_and_all_category_zip` — passed.
5. `test_single_and_batch_agree_and_group_correctly` — passed.

Command: `.\.venv\Scripts\python.exe tests/browser_organization.py`

Browser suite passed: single-image classification, real batch classification, partial failure, category counts, actual ZIP download and original-byte verification, mobile overflow check, clearing results, and all-invalid batches. No JavaScript errors were observed.

**Failed tests: none.** Both suites use the real trained model.

## Reproduction

With the app running on port 8001 and Playwright plus Microsoft Edge available:

```powershell
.\.venv\Scripts\python.exe report_assets/capture_batch_screenshots.py
```

The script performs real UI uploads and inference, downloads and verifies the archive, builds the temporary evidence viewer from actual ZIP metadata, and captures all four screenshots.
