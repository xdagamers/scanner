# NIFTY Breakout Scanner + Audit Collection

## Runtime
- `app.py` — Streamlit UI
- `scanner.py` — existing NIFTY LargeMidcap 250 scanner engine; audit fields are exposed without changing scoring/ranking/filter logic
- `google_sheets_audit.py` — append/read Google Sheets storage
- `audit_logger.py` — builds complete audit signal snapshots
- `audit_analysis.py` — later combination analysis / validation

## Buttons
- **SCAN MARKET**: runs the scanner and writes nothing to Google Sheets.
- **COLLECT AUDIT DATA**: runs the same scanner, asks for confirmation, then appends the full signal batch.

## Secrets
Configure Streamlit Secrets using `secrets.toml.example`. Never commit a real service-account key or `.streamlit/secrets.toml`.

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud
Set the app entrypoint to `app.py` and paste the secrets into the app's Secrets settings.
