# NIFTY Breakout Scanner — Audit Collection Deployment

## Architecture
- `SCAN MARKET` runs the scanner and writes **nothing** to Google Sheets.
- `COLLECT AUDIT DATA` runs the exact same scanner, creates an audit snapshot, then asks for explicit confirmation before appending.
- Google Sheets is append-only for audit batches. Previous batches are never overwritten.
- Tabs: `Audit_Signals`, `Audit_Runs`, `Daily_Performance`, `Analysis_Results`.

## One-time Google setup
1. Open Google Cloud Console and create/select a project.
2. Enable Google Sheets API (and Google Drive API if prompted/required by your gspread setup).
3. Create a Service Account.
4. Create/download a JSON key for that service account.
5. Open the target spreadsheet and Share it with the service account's `client_email` as Editor.
6. The spreadsheet ID is already configured from the supplied URL.

## Streamlit Cloud
1. Put the project files in one GitHub repository:
   - `app_cap500_search_audit_normal_reload.py`
   - `scanner.py` (use the updated `scanner_cap500.py` under the filename your app imports)
   - `audit_logger.py`
   - `google_sheets_audit.py`
   - `requirements.txt`
2. Deploy the app on Streamlit Community Cloud.
3. In App settings -> Secrets, paste the contents of `secrets.toml.example` with your real service-account values.
4. Never commit a real `secrets.toml` or JSON key to GitHub.

## Dummy test before real collection
1. Deploy and confirm normal `SCAN MARKET` works.
2. Run `SCAN MARKET` twice. Confirm Google Sheet row count does not change.
3. Run `COLLECT AUDIT DATA` once. Confirm the confirmation appears and NO rows are written before pressing YES.
4. Press YES. Confirm one `Audit_Run_ID` appears in `Audit_Runs` and its signals appear in `Audit_Signals`.
5. Run `COLLECT AUDIT DATA` a second time. Confirm a different `Audit_Run_ID` is appended below the first batch.
6. Retry the same run only if the app reports a write uncertainty. The same Run ID is designed to prevent accidental duplicate appends.
7. Delete only the rows whose `Audit_Run_ID` starts with `AUDIT_` that you used for testing, or clear the entire test workbook before the real audit begins.

## Real collection schedule
Run the audit collection once per trading day, after the market closes and the final daily data is available. Recommended window: after 4:00 PM IST, once the day's NSE data is reflected by the data source.

Do not use the day's intraday high as proof of a successful signal if the signal was generated after the close. The signal's first tracking day is the next trading day.

For each signal, later populate 20 following trading days in `Daily_Performance` with Open/High/Low/Close and event flags. High determines target hits; Low determines stop/drawdown. If both target and stop are touched on the same daily candle, mark the day `AMBIGUOUS` unless intraday data establishes the order.

## Analysis plan
After enough matured signals (preferably >=200; 300-500+ is better), analyze:
- T1 hit rate
- T2 hit rate
- T3 hit rate
- stop rate
- breakout rate
- time to breakout/target
- average/median return
- best gain
- maximum drawdown

Then run bounded combinations of rating, distance, RVOL, ADX, RSI, score, rank score and the individual component scores. Do not simply pick the best in-sample combination: use time-based train/test or walk-forward validation to reduce overfitting.
