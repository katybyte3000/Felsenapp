import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# Importiere die Funktionen aus deinen Modulen
from app_modules.eintragen import main_app_eintragen
from app_modules.auswertung import main_app_auswertung
from app_modules.map import main_app_map
from app_modules.utils import display_last_climbed_rocks
from app_modules.filtermap import show_filter_map_page # Importiere die Funktion für die Filterkarte aus dem Unterverzeichnis

# .env laden
load_dotenv()

# Supabase-Verbindung initialisieren (Globale Initialisierung)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None # Initialisiere supabase als None
is_supabase_ready = False # Neuer Status-Flag für Supabase-Verbindung

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("FEHLER: SUPABASE_URL oder SUPABASE_KEY wurden nicht gefunden. Stellen Sie sicher, dass Ihre .env-Datei korrekt ist und die Variablen gesetzt sind.")
    st.info("Die Anwendung kann ohne Datenbankverbindung nicht gestartet werden.")
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        is_supabase_ready = True # Setze Flag auf True, wenn Verbindung erfolgreich
    except Exception as e:
        st.error(f"FEHLER: Verbindung zur Supabase-Datenbank fehlgeschlagen: {e}")
        st.info("Bitte überprüfen Sie Ihre Internetverbindung und die Supabase-Konfiguration.")


# --- NEUE FARBKONZEPT KONSTANTEN (Global für CSS) ---
BG_COLOR = "#FFEF16"        # Dein lebendiges Gelb
HIGHLIGHT_COLOR = "#006D77" # Petrol
POSITIVE_COLOR = "#3BB277"  # Grün
NEGATIVE_COLOR = "#8E44AD"  # Lila
SECONDARY_COLOR = "#83C5BE" # Helles Petrol
TEXT_COLOR = "#1D1D1D"      # Dunkelgrau

# --- Globale Seitenkonfiguration und CSS Styling ---
st.set_page_config(page_title="Felsenapp", layout="wide")

st.markdown(f"""
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Noto+Sans:wght@400;700&display=swap'); /* NEU: Oswald und Noto Sans */
@import url('https://fonts.googleapis.com/css2?family=Lacquer&display=swap'); /* Lacquer ist weiterhin importiert, wird aber nicht aktiv für Headlines genutzt */

/* === Gesamtseiten-Hintergrund === */
.stApp {{
    background-color: {BG_COLOR} !important;
}}

/* === Headlines in Oswald === */
h1, h2, h3, .stTitle, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
.headline-fonts, [data-testid="stMetricValue"], .st-emotion-cache-10q20n3 h1 {{ /* Letztere sind spezifische IDs/Klassen, die auch in Oswald sein sollen */
    font-family: 'Oswald', sans-serif !important;
    color: {TEXT_COLOR};
    font-weight: 700 !important; /* Oswald Bold */
}}

/* === Fließtext in Noto Sans Bold === */
html, body, .stMarkdown p, .stText, .stDataFrame, .css-18ni7ap,
.st-emotion-cache-nahz7x, .st-emotion-cache-l9bibm, .st-emotion-cache-1ftrzg7,
[data-testid="stMetricLabel"] {{ /* Sicherstellen, dass Metric Label auch Noto Sans ist */
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
    color: {TEXT_COLOR};
}}

/* === Buttons im Highlight-Stil === */
.stButton > button {{
    background-color: {HIGHLIGHT_COLOR} !important;
    color: white !important;
    border-radius: 8px;
    padding: 0.5em 1em;
    border: 3px solid {HIGHLIGHT_COLOR} !important;
    box-shadow: 4px 4px 0px 0px rgba(0,0,0,0.75);
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
}}

.stButton > button:hover {{
    background-color: {HIGHLIGHT_COLOR}D0 !important;
    border: 3px solid {HIGHLIGHT_COLOR} !important;
    box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.75);
    transition: background-color 0.3s ease-in-out, box-shadow 0.1s ease-in-out;
}}

/* === Allgemeine Streamlit-Elemente (Container, Inputs) mit Outlines === */
.st-emotion-cache-1ftrzg7,
.st-emotion-cache-nahz7x,
.st-emotion-cache-l9bibm {{
    border: 3px solid {HIGHLIGHT_COLOR} !important;
    border-radius: 8px;
    box-shadow: 6px 6px 0px 0px rgba(0,0,0,0.75);
    padding: 10px;
    margin-bottom: 15px;
}}

/* Für Inputs, Textbereiche */
.stTextInput > div > div > input,
.stTextArea > div > textarea {{
    border: 3px solid {HIGHLIGHT_COLOR} !important;
    border-radius: 8px;
    box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.75);
    padding: 8px;
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
    color: {TEXT_COLOR};
}}

/* Für Selectboxen/Dropdowns */
.stSelectbox > div > div {{
    border: 3px solid {HIGHLIGHT_COLOR} !important;
    border-radius: 8px;
    box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.75);
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
    color: {TEXT_COLOR};
}}

/* Anpassung der Metric-Werte - jetzt auch Oswald */
[data-testid="stMetricValue"] {{
    font-family: 'Oswald', sans-serif !important;
    font-weight: 700 !important;
    font-size: 3em !important;
    color: {HIGHLIGHT_COLOR} !important;
}}
[data-testid="stMetricLabel"] {{
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
    color: {TEXT_COLOR} !important;
}}

/* Sidebar Header / Navigation */
.st-emotion-cache-10q20n3 {{
    background-color: {HIGHLIGHT_COLOR};
    color: white;
}}
.st-emotion-cache-10q20n3 h1, .st-emotion-cache-10q20n3 h2, .st-emotion-cache-10q20n3 h3, .st-emotion-cache-10q20n3 h4, .st-emotion-cache-10q20n3 h5, .st-emotion-cache-10q20n3 h6 {{
    color: white;
    font-family: 'Oswald', sans-serif !important;
}}
.st-emotion-cache-1r6dm1b {{
    background-color: {HIGHLIGHT_COLOR};
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
}}
.st-emotion-cache-1r6dm1b .stButton>button {{
    background-color: white !important;
    color: {HIGHLIGHT_COLOR} !important;
    border: 2px solid {HIGHLIGHT_COLOR} !important;
    box-shadow: none;
}}
.st-emotion-cache-1r6dm1b .stButton>button:hover {{
    background-color: {SECONDARY_COLOR} !important;
    color: white !important;
    border: 2px solid {HIGHLIGHT_COLOR} !important;
}}

/* Allgemeine Plotly-Achsentitel und -Labels (als Fallback) */
/* Diese werden in auswertung.py explizit auf Noto Sans gesetzt */
.modebar, .g-gtitle {{
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
    color: {TEXT_COLOR} !important;
}}

/* Spezifischer Stil für Haupt-Überschriften (via headline-fonts Div) */
.headline-fonts {{
    font-family: 'Oswald', sans-serif !important;
    font-size: 3em !important;
    color: {TEXT_COLOR};
    text-shadow: none;
    text-transform: none;
    line-height: 1.2;
    margin-top: 1em;
    margin-bottom: 0.5em;
}}

/* Stil für hervorgehobene Zahlen/Werte im Fließtext (unverändert) */
.highlight-number {{
    font-family: 'Noto Sans', sans-serif !important;
    font-size: 1.2em !important;
    font-weight: 700 !important;
    color: {HIGHLIGHT_COLOR};
}}

</style>
""", unsafe_allow_html=True)


# --- Session State für Benutzerinformationen und Navigation ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home_public"

# --- Funktion für Login / Registrierung UI (im Hauptbereich) ---
def login_register_ui():
    st.title("Willkommen bei Felsenapp!")
    st.subheader("Bitte melden Sie sich an oder registrieren Sie sich.")

    with st.container(border=True): # Dieser Container erbt die neuen Border-Styles
        st.markdown("#### Anmelden / Registrieren")
        email = st.text_input("E-Mail", key="app_login_email")
        password = st.text_input("Passwort", type="password", key="app_login_password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", use_container_width=True):
                # Prüfen, ob supabase initialisiert ist
                if supabase:
                    try:
                        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user_id = response.user.id
                        st.session_state.user_email = response.user.email
                        st.session_state.current_page = "home_private"
                        st.success(f"Willkommen, {st.session_state.user_email}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login fehlgeschlagen: {e}")
                else:
                    st.error("Datenbankverbindung nicht verfügbar. Bitte überprüfen Sie Ihre Konfiguration.")

        with col2:
            if st.button("Registrieren", use_container_width=True):
                # Prüfen, ob supabase initialisiert ist
                if supabase:
                    try:
                        response = supabase.auth.sign_up({"email": email, "password": password})
                        st.session_state.user_id = response.user.id
                        st.session_state.user_email = response.user.email
                        st.session_state.current_page = "home_private"
                        st.success(f"Benutzer {st.session_state.user_email} registriert und eingeloggt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Registrierung fehlgeschlagen: {e}")
                else:
                    st.error("Datenbankverbindung nicht verfügbar. Bitte überprüfen Sie Ihre Konfiguration.")

# --- Funktion für Logout UI (in Sidebar) ---
def logout_ui():
    st.sidebar.markdown(f"Eingeloggt als: **{st.session_state.user_email}**")
    if st.sidebar.button("Logout"):
        if supabase: # Prüfen, ob supabase initialisiert ist
            supabase.auth.sign_out()
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.current_page = "home_public"
        st.sidebar.success("Erfolgreich ausgeloggt.")
        st.rerun()

# --- Navigationsleiste für öffentliche Seiten (immer sichtbar) ---
def public_navigation_ui():
    # Direktes Styling für den Sidebar-Header
    st.sidebar.markdown(f"""
        <div style="background-color: {HIGHLIGHT_COLOR}; padding: 1rem; border-radius: 8px 8px 0 0; text-align: center; margin-bottom: 10px;">
            <h1 style="color: white; font-family: 'Oswald', sans-serif; margin: 0;">FELSENAPP</h1>
        </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("---")
    st.sidebar.markdown(f'<p style="font-family: \'Noto Sans\', sans-serif; font-weight: 700; color:{TEXT_COLOR};">Öffentliche Bereiche</p>', unsafe_allow_html=True)

    # Buttons im Sidebar (werden durch das CSS unten gestylt)
    if st.sidebar.button("Home (Öffentlich)"):
        st.session_state.current_page = "home_public"
    if st.sidebar.button("Karte Sächsische Schweiz"):
        st.session_state.current_page = "map_public"

    st.sidebar.markdown("---")

# --- Navigationsleiste für private Seiten (nur bei Login sichtbar) ---
def private_navigation_ui():
    st.sidebar.markdown(f'<p style="font-family: \'Noto Sans\', sans-serif; font-weight: 700; color:{TEXT_COLOR};">Ihre Bereiche</p>', unsafe_allow_html=True)
    if st.sidebar.button("Home (Privat)"):
        st.session_state.current_page = "home_private"
    if st.sidebar.button("Begehung hinzufügen"):
        st.session_state.current_page = "eintragen"
    if st.sidebar.button("Filterkarte"): # Button für Filterkarte
        # st.session_state.current_page = "filterkarte" # Dies wird unten im main_app_flow behandelt
        st.session_state.current_page = "filterkarte" # Setze die Seite hier
    if st.sidebar.button("Statistik"):
        st.session_state.current_page = "statistik"

    st.sidebar.markdown("---")
    logout_ui()

# --- Haupt-App-Layout ---
def main_app_flow():
    # Wenn supabase nicht initialisiert werden konnte, zeige eine Fehlermeldung und beende.
    # Dies ist die erste Stelle, an der wir die App stoppen können, wenn die DB nicht bereit ist.
    if not is_supabase_ready:
        st.error("Die Anwendung konnte aufgrund fehlender Datenbankverbindung nicht gestartet werden. Bitte beheben Sie die oben genannten Fehler und starten Sie die App neu.")
        st.stop() # Stoppt die Ausführung der App hier

    # Immer die öffentliche Navigation anzeigen
    public_navigation_ui()

    # Wenn eingeloggt, auch die private Navigation anzeigen
    if st.session_state.user_id:
        private_navigation_ui()

    # Inhalte basierend auf der ausgewählten Seite und dem Login-Status anzeigen
    if st.session_state.current_page == "home_public":
        if st.session_state.user_id:
            st.header(f"Willkommen zurück, {st.session_state.user_email}!")
            st.write("Sie sind erfolgreich eingeloggt. Wählen Sie eine Option aus der Navigation in der Seitenleiste.")
            st.session_state.current_page = "home_private"
            st.rerun()
        else:
            st.header("Willkommen bei Felsenapp!")
            st.write("Entdecken Sie die Karte der Sächsischen Schweiz oder melden Sie sich an, um Ihre Begehungen zu verwalten.")
            login_register_ui()

    elif st.session_state.current_page == "map_public":
        main_app_map(st.session_state.user_id) # user_id wird an main_app_map übergeben

    # --- Private Seiten (nur zugänglich, wenn eingeloggt) ---
    elif st.session_state.user_id: # Dieser Block wird nur ausgeführt, wenn user_id existiert
        if st.session_state.current_page == "home_private":
            st.header(f"Willkommen zurück, {st.session_state.user_email}!")
            st.write("Dies ist Ihre persönliche Felsenapp-Startseite.")
            st.write("Wählen Sie eine Option aus der Navigation in der Seitenleiste.")

            st.markdown("---")
            display_last_climbed_rocks(supabase, st.session_state.user_id, num_rocks=10)
            st.markdown("---")

        elif st.session_state.current_page == "eintragen":
            main_app_eintragen()
        elif st.session_state.current_page == "filterkarte": # Aufruf der Filterkarte-Seite
            show_filter_map_page(supabase) # HIER WURDE DIE ÜBERGABE HINZUGEFÜGT
        elif st.session_state.current_page == "statistik":
            main_app_auswertung()
        else:
            st.error("Unbekannte Seite oder Zugriff verweigert. Bitte wählen Sie eine Seite aus der Navigation.")
            st.session_state.current_page = "home_private"
            st.rerun()
    else: # Fallback: Wenn current_page eine private Seite ist, aber user_id nicht existiert
        st.warning("Sie müssen angemeldet sein, um diesen Bereich zu sehen.")
        st.session_state.current_page = "home_public"
        st.rerun()

# --- Startpunkt der App ---
if __name__ == "__main__":
    main_app_flow()
