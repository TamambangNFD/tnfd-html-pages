# tnfd-html-pages

Static, self-contained HTML case-study pages:

- `Coleridge_Initiative.html` — dataset discovery / NLP project
- `Fraud_Detection.html` — fraud detection with data augmentation
- `Vivino.html` — Vivino wine market intelligence

## Checks

The pages have no JavaScript, so instead of unit tests the repository validates
page structure, accessibility basics and referenced assets:

```bash
pip install -r requirements-dev.txt
pytest -v
```

Each page is checked for HTML5 validity, an HTML5 doctype, `<html lang>`,
`<title>`, charset and viewport meta tags, exactly one `<h1>`, non-empty `img`
alt text, unique element ids, resolvable in-page anchors, existing local assets
and https-only external references.

`Fraud_Detection.html` references four dashboard images that are not committed
(`model_performance.png`, `operational_impact.png`, `confusion_matrices.png`,
`threshold_tuning.png`); they are listed in `KNOWN_MISSING_ASSETS` in
`tests/test_html_pages.py`. Commit the images and remove the corresponding
entries to make the asset check enforce them.

CI runs the same checks on every push to `main` and every pull request.
