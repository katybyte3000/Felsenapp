import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# Importiere die Funktionen aus deinen Seiten-Dateien
# Stelle sicher, dass pages/eintragen.py und pages/auswertung.py existieren
from pages.eintragen import main_app_eintragen
from pages.auswertung import main_app_auswertung # <<< NEU: Import der Statistik-Funktion

# .env laden – stellt sicher, dass die .env-Datei im Hauptverzeichnis des Projekts gefunden wird
load_dotenv()

# Supabase-Verbindung initialisieren
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Session State für Benutzerinformationen und Navigation ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home" # Standardseite nach Login

# --- Funktion für Login / Registrierung UI ---
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
                    st.success(f"Benutzer {st.session_state.user_email} registriert und eingeloggt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Registrierung fehlgeschlagen: {e}")

# --- Funktion für Logout UI ---
def logout_ui():
    """Zeigt den Logout-Button und die E-Mail des eingeloggten Benutzers in der Sidebar an."""
    st.sidebar.markdown(f"Eingeloggt als: **{st.session_state.user_email}**")
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.current_page = "home" # Setze Seite zurück auf Home/Login
        st.sidebar.success("Erfolgreich ausgeloggt.")
        st.rerun()

# --- Haupt-Anwendungs-Layout nach Login ---
def logged_in_app_layout():
    """Zeigt das Hauptlayout der App an, wenn ein Benutzer eingeloggt ist."""
    st.set_page_config(page_title="Felsenapp", layout="wide")

    st.sidebar.title("Felsenapp Navigation")
    
    # Navigationsbuttons in der Seitenleiste direkt nach dem Titel
    if st.sidebar.button("Home"):
        st.session_state.current_page = "home"
    if st.sidebar.button("Begehung hinzufügen"):
        st.session_state.current_page = "eintragen"
    if st.sidebar.button("Statistik"): # <<< NEU: Button für Statistik
        st.session_state.current_page = "statistik"

    st.sidebar.markdown("---") # Trennlinie in der Sidebar
    logout_ui() # Logout-Button nach den Navigationsbuttons

    st.markdown("---") # Trennlinie im Hauptbereich

    # Inhalte basierend auf der ausgewählten Seite anzeigen
    if st.session_state.current_page == "home":
        st.header(f"Willkommen zurück, {st.session_state.user_email}!")
        st.write("Dies ist Ihre persönliche Felsenapp-Startseite.")
        st.write("Wählen Sie eine Option aus der Navigation in der Seitenleiste.")
    elif st.session_state.current_page == "eintragen":
        main_app_eintragen() # Ruft die Funktion aus pages/eintragen.py auf
    elif st.session_state.current_page == "statistik": # <<< NEU: Aufruf der Statistik-Funktion
        main_app_auswertung()


# --- App-Flow steuern (eingeloggt oder nicht) ---
if st.session_state.user_id:
    logged_in_app_layout() # Zeigt das Hauptlayout der App an
else:
    login_register_ui() # Zeigt Login/Registrierung an
