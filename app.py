import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# Importiere die Funktionen aus deinen Modulen
from app_modules.eintragen import main_app_eintragen
from app_modules.auswertung import main_app_auswertung
from app_modules.map import main_app_map

# .env laden – stellt sicher, dass die .env-Datei im Hauptverzeichnis des Projekts gefunden wird
load_dotenv()

# Supabase-Verbindung initialisieren
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Globale Seitenkonfiguration und CSS Styling ---
st.set_page_config(page_title="Felsenapp", layout="wide")

st.markdown("""
<style>
/* === Google Fonts importieren === */
@import url('https://fonts.googleapis.com/css2?family=Georama&family=Onest:wght@600&display=swap');

/* === Gesamtseiten-Hintergrund in ocker === */
.stApp {
    background-color: #f0e68c !important;
}

/* === Headlines in Onest === */
h1, h2, h3, .stTitle, .stMarkdown h1, .stMarkdown h2 {
    font-family: 'Onest', sans-serif !important;
    color: #1e1e1e;
}

/* === Fließtext in Georama === */
html, body, .stMarkdown p, .stText, .stDataFrame, .css-18ni7ap {
    font-family: 'Georama', sans-serif !important;
    color: #222;
}

/* === Buttons in schwarz mit weißem Text === */
.stButton > button {
    background-color: #000 !important;
    color: white !important;
    border-radius: 8px;
    padding: 0.5em 1em;
    border: none;
}

.stButton > button:hover {
    background-color: #333 !important;
    transition: background-color 0.3s ease-in-out;
}

/* === Grüne Füllfarben z. B. für Plotly Balken/Donuts (empfohlen via Plotly) === */
/* Das kann bei Plotly Charts nicht direkt über CSS überschrieben werden.
   Stelle dort beim Erstellen einfach `marker_color='green'` oder ähnlich ein. */
</style>
""", unsafe_allow_html=True)


# --- Session State für Benutzerinformationen und Navigation ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home_public" # Standardseite beim ersten Laden

# --- Funktion für Login / Registrierung UI (im Hauptbereich) ---
def login_register_ui():
    """Zeigt das Login- und Registrierungsformular im Hauptbereich der App an."""
    st.title("Willkommen bei Felsenapp!")
    st.subheader("Bitte melden Sie sich an oder registrieren Sie sich.")

    with st.container(border=True):
        st.markdown("#### Anmelden / Registrieren")
        email = st.text_input("E-Mail", key="app_login_email")
        password = st.text_input("Passwort", type="password", key="app_login_password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", use_container_width=True):
                try:
                    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user_id = response.user.id
                    st.session_state.user_email = response.user.email
                    st.session_state.current_page = "home_private" # Nach Login zur privaten Startseite
                    st.success(f"Willkommen, {st.session_state.user_email}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login fehlgeschlagen: {e}")

        with col2:
            if st.button("Registrieren", use_container_width=True):
                try:
                    response = supabase.auth.sign_up({"email": email, "password": password})
                    st.session_state.user_id = response.user.id
                    st.session_state.user_email = response.user.email
                    st.session_state.current_page = "home_private" # Nach Registrierung zur privaten Startseite
                    st.success(f"Benutzer {st.session_state.user_email} registriert und eingeloggt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Registrierung fehlgeschlagen: {e}")

# --- Funktion für Logout UI (in Sidebar) ---
def logout_ui():
    """Zeigt den Logout-Button und die E-Mail des eingeloggten Benutzers in der Sidebar an."""
    st.sidebar.markdown(f"Eingeloggt als: **{st.session_state.user_email}**")
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.current_page = "home_public" # Nach Logout zur öffentlichen Startseite
        st.sidebar.success("Erfolgreich ausgeloggt.")
        st.rerun()

# --- Navigationsleiste für öffentliche Seiten (immer sichtbar) ---
def public_navigation_ui():
    """Zeigt Navigationsbuttons für öffentliche Seiten in der Sidebar an."""
    st.sidebar.title("Felsenapp")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Öffentliche Bereiche")
    if st.sidebar.button("Home (Öffentlich)"):
        st.session_state.current_page = "home_public"
    if st.sidebar.button("Karte Sächsische Schweiz"):
        st.session_state.current_page = "map_public"
    
    st.sidebar.markdown("---") # Trennlinie

# --- Navigationsleiste für private Seiten (nur bei Login sichtbar) ---
def private_navigation_ui():
    """Zeigt Navigationsbuttons für private Seiten in der Sidebar an."""
    st.sidebar.subheader("Ihre Bereiche")
    if st.sidebar.button("Home (Privat)"):
        st.session_state.current_page = "home_private"
    if st.sidebar.button("Begehung hinzufügen"):
        st.session_state.current_page = "eintragen"
    if st.sidebar.button("Statistik"):
        st.session_state.current_page = "statistik"
    
    st.sidebar.markdown("---") # Trennlinie
    logout_ui() # Logout-Button

# --- Haupt-App-Layout (entscheidet, was angezeigt wird) ---
def main_app_flow():
    # st.set_page_config(page_title="Felsenapp", layout="wide") # Hier entfernt, da jetzt global oben

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
            st.session_state.current_page = "home_private" # Setze auf private Home, wenn eingeloggt
            st.rerun()
        else:
            st.header("Willkommen bei Felsenapp!")
            st.write("Entdecken Sie die Karte der Sächsischen Schweiz oder melden Sie sich an, um Ihre Begehungen zu verwalten.")
            login_register_ui() # Zeigt das Login/Registrierungsformular an
    
    elif st.session_state.current_page == "map_public":
        main_app_map() # Ruft die Funktion für die öffentliche Karte auf

    # --- Private Seiten (nur zugänglich, wenn eingeloggt) ---
    elif st.session_state.user_id: # Nur fortfahren, wenn ein Benutzer eingeloggt ist
        if st.session_state.current_page == "home_private":
            st.header(f"Willkommen zurück, {st.session_state.user_email}!")
            st.write("Dies ist Ihre persönliche Felsenapp-Startseite.")
            st.write("Wählen Sie eine Option aus der Navigation in der Seitenleiste.")
        elif st.session_state.current_page == "eintragen":
            main_app_eintragen() # Ruft die Funktion aus app_modules/eintragen.py auf
        elif st.session_state.current_page == "statistik":
            main_app_auswertung() # Ruft die Funktion aus app_modules/auswertung.py auf
        else:
            # Fallback für unbekannte private Seiten, sollte nicht vorkommen
            st.error("Unbekannte Seite oder Zugriff verweigert. Bitte wählen Sie eine Seite aus der Navigation.")
            st.session_state.current_page = "home_private"
            st.rerun()
    else:
        # Wenn eine private Seite direkt aufgerufen wird, ohne Login
        st.warning("Sie müssen angemeldet sein, um diesen Bereich zu sehen.")
        st.session_state.current_page = "home_public" # Zurück zur öffentlichen Startseite
        st.rerun()


# --- Startpunkt der App ---
if __name__ == "__main__":
    main_app_flow()
