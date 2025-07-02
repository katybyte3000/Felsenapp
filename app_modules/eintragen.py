import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# .env laden – robust für Seiten im "app_modules/"-Ordner
# Stellt sicher, dass die .env-Datei im Hauptverzeichnis des Projekts gefunden wird
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

# Supabase-Verbindung initialisieren
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Haupt-App-Logik für das Eintragen von Begehungen ---
# Diese Funktion wird nun von app.py aufgerufen, wenn der Benutzer eingeloggt ist
def main_app_eintragen():
    """Enthält die Hauptlogik der Anwendung zum Hinzufügen von Begehungen."""
    st.title("🧗 Begehung hinzufügen")

    # Sicherstellen, dass user_id im Session State vorhanden ist
    # Dies sollte von app.py gesetzt werden, nachdem sich ein Benutzer angemeldet hat.
    if st.session_state.user_id is None:
        st.error("Fehler: Kein Benutzer eingeloggt. Bitte melden Sie sich über die Hauptseite an.")
        return # Die App-Logik nicht ausführen, wenn kein User eingeloggt ist

    # 1. Sektoren laden
    sectors = supabase.table("sector").select("id, name").execute().data
    sectors_df = pd.DataFrame(sectors)

    selected_sector = st.selectbox("1️⃣ Gebiet auswählen", sectors_df["name"])
    selected_sector_id = sectors_df.loc[sectors_df["name"] == selected_sector, "id"].values[0]

    # 2. Rocks aus gewähltem Gebiet
    rocks = supabase.table("rocks").select("id, name, sector_id").eq("sector_id", selected_sector_id).execute().data
    rocks_df = pd.DataFrame(rocks)

    selected_rock = st.selectbox("2️⃣ Fels auswählen", rocks_df["name"])
    selected_rock_id = rocks_df.loc[rocks_df["name"] == selected_rock, "id"].values[0]

    # 3. Routen aus gewähltem Rock
    routes = supabase.table("routes").select("id, name, rock_id").eq("rock_id", selected_rock_id).execute().data
    routes_df = pd.DataFrame(routes)

    selected_route = st.selectbox("3️⃣ Route auswählen", routes_df["name"])
    selected_route_id = routes_df.loc[routes_df["name"] == selected_route, "id"].values[0]

    # 4. Formular zur Begehung
    st.subheader("4️⃣ Begehung eintragen")

    with st.form("neue_begehung"):
        datum = st.date_input("Datum")
        partnerin = st.text_input("Partner*in")
        stil = st.selectbox("Stil", ["Vorstieg", "Nachstieg", "Solo", "Spritze"])
        kommentar = st.text_area("Kommentar")
        
        schwierigkeit_optionen = {
            "1: leicht": 1,
            "2: ok": 2,
            "3: schwer": 3
        }
        schwierigkeit_label = st.radio("Schwierigkeit", list(schwierigkeit_optionen.keys()))
        bewertung = schwierigkeit_optionen[schwierigkeit_label]

        submitted = st.form_submit_button("Begehung speichern")

    # 5. Speichern
    if submitted:
        # Überprüfen, ob ein Benutzer eingeloggt ist, bevor gespeichert wird
        if st.session_state.user_id:
            try:
                response = supabase.table("ascents").insert({
                    "datum": str(datum),
                    "route_id": int(selected_route_id),
                    "gipfel_id": int(selected_rock_id),
                    "partnerin": partnerin,
                    "stil": stil,
                    "kommentar": kommentar,
                    "bewertung": int(bewertung),
                    "user_id": st.session_state.user_id
                }).execute()

                if response.data:
                    st.success("✅ Begehung erfolgreich gespeichert!")
                else:
                    st.error("❌ Fehler beim Speichern – evtl. Policy fehlt oder Daten sind ungültig.")

            except Exception as e:
                st.error(f"❌ Ausnahme beim Speichern: {e}")
        else:
            st.warning("Bitte melden Sie sich an, um eine Begehung zu speichern.")

# Hinweis: Der if __name__ == "__main__": Block wird entfernt, da diese Datei als Modul importiert wird.
