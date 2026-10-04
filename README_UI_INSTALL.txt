NIFTY TOP 250 SCANNER - UI REDESIGN INSTALLATION

IMPORTANT:
This UI redesign does NOT replace or modify scanner.py.
Keep your existing scanner.py exactly as it is.

GitHub files:
1. Replace/add app.py with this package's app.py.
2. Add .streamlit/config.toml exactly at .streamlit/config.toml.
3. Keep your existing requirements.txt. The current scanner requirements already contain all libraries used by this UI.
4. Do not delete scanner.py.
5. Delete the old streamlit_app.py only if your Streamlit Cloud app is changed to use app.py as its Main file.

Streamlit Community Cloud:
- Open your deployed app -> Manage app -> Settings / Edit deployment.
- Set Main file path to: app.py
- Save/redeploy.

Local test:
pip install -r requirements.txt
streamlit run app.py

The scanner logic, data fetching and scoring remain in scanner.py and are called by app.py.
