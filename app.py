import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# Importiere die Funktion aus deiner eintragen.py Datei
# Stelle sicher, dass pages/eintragen.py existiert und die Funktion main_app_eintragen enthält
from pages.eintragen import main_app_eintragen

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
                    # Versucht, den Benutzer mit E-Mail und Passwort anzumelden
                    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    
                    # Wenn erfolgreich, Benutzer-ID und E-Mail im Session State speichern
                    st.session_state.user_id = response.user.id
                    st.session_state.user_email = response.user.email
                    st.success(f"Willkommen, {st.session_state.user_email}!")
                    st.rerun() # Seite neu laden, um die Haupt-App anzuzeigen
                except Exception as e:
                    st.error(f"Login fehlgeschlagen: {e}")

        with col2:
            if st.button("Registrieren", use_container_width=True):
                try:
                    # Versucht, einen neuen Benutzer zu registrieren
                    response = supabase.auth.sign_up({"email": email, "password": password})
                    
                    # Wenn erfolgreich, Benutzer-ID und E-Mail im Session State speichern
                    st.session_state.user_id = response.user.id
                    st.session_state.user_email = response.user.email
                    st.success(f"Benutzer {st.session_state.user_email} registriert und eingeloggt!")
                    st.rerun() # Seite neu laden
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
    logout_ui() # Logout-Button in der Sidebar

    st.sidebar.markdown("---")
    # Navigationsbuttons in der Seitenleiste
    if st.sidebar.button("Home"):
        st.session_state.current_page = "home"
    if st.sidebar.button("Begehung hinzufügen"):
        st.session_state.current_page = "eintragen"
    # Hier könnten weitere Navigationsbuttons für andere Seiten sein, z.B. Statistik
    # if st.sidebar.button("Statistik"):
    #     st.session_state.current_page = "statistik"

    st.markdown("---") # Trennlinie im Hauptbereich

    # Inhalte basierend auf der ausgewählten Seite anzeigen
    if st.session_state.current_page == "home":
        st.header(f"Willkommen zurück, {st.session_state.user_email}!")
        st.write("Dies ist Ihre persönliche Felsenapp-Startseite.")
        st.write("Wählen Sie eine Option aus der Navigation in der Seitenleiste.")
    elif st.session_state.current_page == "eintragen":
        main_app_eintragen() # <<< HIER WIRD DIE FUNKTION AUS eintragen.py AUFGERUFEN!
    # elif st.session_state.current_page == "statistik":
    #     # Hier würde die Funktion für die Statistik-Seite aufgerufen werden
    #     st.write("Statistik-Seite kommt hierher.")


# --- App-Flow steuern (eingeloggt oder nicht) ---
if st.session_state.user_id:
    logged_in_app_layout() # Zeigt das Hauptlayout der App an
else:
    login_register_ui() # Zeigt Login/Registrierung an
