import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# .env laden – robust für Seiten im "app_modules/"-Ordner
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

# Supabase-Verbindung initialisieren
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Hauptfunktion für die Kartenansicht ---
def main_app_map():
    """
    Zeigt die Karte der Sächsischen Schweiz an.
    Diese Seite ist öffentlich zugänglich (kein Login erforderlich).
    """
    st.title("🗺️ Karte der Sächsischen Schweiz")
    st.write("Dies ist eine öffentliche Seite. Sie können die Karte sehen, ohne angemeldet zu sein.")

    # Hier würde der tatsächliche Code für deine Karte eingefügt werden.
    # Zum Beispiel:
    # - Abfrage von Fels- oder Sektordaten aus Supabase
    # - Erstellung einer interaktiven Karte mit Folium, PyDeck oder Plotly
    
    # Beispiel: Einfache Anzeige von Felsdaten
    try:
        rocks_data = supabase.table("rocks").select("id, name, sector_id").range(0, 1000).execute().data
        rocks_df = pd.DataFrame(rocks_data)
        
        if not rocks_df.empty:
            st.subheader("Einige Felsen aus der Datenbank:")
            st.dataframe(rocks_df.head()) # Zeigt die ersten 5 Felsen
            st.info("Hier würde Ihre interaktive Karte erscheinen.")
        else:
            st.info("Keine Felsen in der Datenbank gefunden, um auf der Karte anzuzeigen.")
            
    except Exception as e:
        st.error(f"Fehler beim Laden der Felsdaten für die Karte: {e}")

    # Beispiel für einen Platzhalter
    st.image("https://placehold.co/600x400/8CF0B4/FFFFFF?text=Ihre+Karte+hier", caption="Platzhalter für die Karte")

# Hinweis: Der if __name__ == "__main__": Block wird entfernt, da diese Datei als Modul importiert wird.
