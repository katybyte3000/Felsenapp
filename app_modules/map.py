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

# --- FARBKONZEPT KONSTANTEN (Dupliziert aus app_modules/auswertung.py zur Konsistenz) ---
# Idealerweise wären diese in einer zentralen Konfigurationsdatei.
PLOT_BG_COLOR = "#FFFFFF"         # Weiss
PLOT_HIGHLIGHT_COLOR = "#006D77"  # Petrol (Hauptfarbe, z.B. für Vorstieg / begangene Gipfel)
PLOT_SECONDARY_COLOR = "#83C5BE"  # Helles Petrol (für Nachstieg und sekundäre Elemente / allgemeine Gipfel)
PLOT_TEXT_COLOR = "#1D1D1D"       # Dunkelgrau
PLOT_OUTLINE_COLOR = "#1D1D1D"    # Dunkelgrau

# --- Datenabruf für die Karte ---
@st.cache_data
def fetch_rock_locations():
    """
    Holt Felsdaten mit Koordinaten.
    """
    try:
        # Sicherstellen, dass latitude und longitude existieren
        rocks_data = supabase.table("rocks").select("id, name, latitude, longitude").range(0, 5000).execute().data
        rocks_df = pd.DataFrame(rocks_data)
        # Wichtig: Konvertiere zu float und dropna für die Karte
        rocks_df['latitude'] = pd.to_numeric(rocks_df['latitude'], errors='coerce')
        rocks_df['longitude'] = pd.to_numeric(rocks_df['longitude'], errors='coerce')
        rocks_df = rocks_df.dropna(subset=['latitude', 'longitude'])
        
        # Streamlit erwartet die Spalten als 'lat' und 'lon' für st.map
        rocks_df.rename(columns={'latitude': 'lat', 'longitude': 'lon'}, inplace=True)
        return rocks_df
    except Exception as e:
        st.error(f"Fehler beim Laden der Felskoordinaten: {e}")
        return pd.DataFrame() # Leeres DataFrame zurückgeben bei Fehler

@st.cache_data
def fetch_user_ascents_gipfel_ids(user_id):
    """
    Holt die gipfel_ids der vom Benutzer begangenen Gipfel.
    """
    if user_id:
        try:
            ascents_data = supabase.table("ascents").select("gipfel_id").eq("user_id", user_id).execute().data
            if ascents_data:
                # Extrahiere nur die gipfel_ids und mache sie einzigartig
                return set([a['gipfel_id'] for a in ascents_data if a['gipfel_id'] is not None])
            return set()
        except Exception as e:
            st.warning(f"Konnte begangene Gipfel nicht laden: {e}")
            return set()
    return set()

# --- Hauptfunktion für die Kartenansicht ---
def main_app_map(user_id=None): # user_id wird nun als Argument übergeben
    st.title("🗺️ Karte der Sächsischen Schweiz")
    st.markdown('<div class="headline-fonts">Interaktive Karte</div>', unsafe_allow_html=True)
    st.write("Entdecke die Felsen der Sächsischen Schweiz auf der Karte. Klicke auf die Punkte für weitere Details.")

    rocks_df = fetch_rock_locations()

    if not rocks_df.empty:
        # Initialisiere Farben und Größen für alle Punkte
        rocks_df['marker_color'] = PLOT_SECONDARY_COLOR # Standardfarbe für alle Gipfel
        rocks_df['marker_size'] = 20 # Standardgröße für alle Gipfel
        rocks_df['hover_text'] = rocks_df['name'] # Standard Hover Text

        num_climbed_rocks = 0
        if user_id:
            climbed_gipfel_ids = fetch_user_ascents_gipfel_ids(user_id)
            if climbed_gipfel_ids:
                rocks_df['is_climbed'] = rocks_df['id'].isin(climbed_gipfel_ids)
                # Aktualisiere Farbe und Größe für begangene Gipfel
                rocks_df.loc[rocks_df['is_climbed'], 'marker_color'] = PLOT_HIGHLIGHT_COLOR
                rocks_df.loc[rocks_df['is_climbed'], 'marker_size'] = 80 # Größer für begangene Gipfel
                # Aktualisiere Hover Text, um den Status anzuzeigen
                rocks_df['hover_text'] = rocks_df.apply(
                    lambda row: f"{row['name']} (Begangen)" if row['is_climbed'] else row['name'], axis=1
                )
                num_climbed_rocks = rocks_df['is_climbed'].sum()
                st.info(f"Du hast **{num_climbed_rocks}** von {len(rocks_df)} Gipfeln auf der Karte begangen.")
            else:
                st.info("Du hast noch keine Begehungen eingetragen, die auf der Karte angezeigt werden könnten. Fange jetzt an!")
        else:
            st.info("Melde dich an, um deine begangenen Gipfel auf der Karte hervorzuheben!")

        # Bestimme den Mittelpunkt und Zoom-Level basierend auf allen Felsen (oder angezeigten Felsen)
        center_lat = rocks_df['lat'].mean()
        center_lon = rocks_df['lon'].mean()
        
        # Streamlit's st.map ist nicht so konfigurierbar wie Plotly/Folium
        # Es nimmt direkt lat, lon, size und color Spaltennamen.
        st.map(rocks_df,
               latitude=center_lat,
               longitude=center_lon,
               size='marker_size', # Verwende die neue Spalte für die Größe
               color='marker_color', # Verwende die neue Spalte für die Farbe
               zoom=10, # Standard Zoomlevel, kann angepasst werden
               tooltip='hover_text' # Füge den Hover-Text hinzu (erfordert Streamlit >= 1.29.0)
              )
        
        st.subheader("Übersicht der Felsen auf der Karte:")
        # Zeige nur relevante Spalten und die erste Handvoll Zeilen
        display_df = rocks_df[['name', 'lat', 'lon']]
        if 'is_climbed' in rocks_df.columns:
            display_df = rocks_df[['name', 'lat', 'lon', 'is_climbed']]
            display_df.rename(columns={'is_climbed': 'Begangen'}, inplace=True)
            display_df['Begangen'] = display_df['Begangen'].apply(lambda x: "Ja" if x else "Nein")

        st.dataframe(display_df.head(10)) # Zeigt die ersten 10 Felsen

    else:
        st.info("Keine Felsen mit gültigen Koordinaten in der Datenbank gefunden, um auf der Karte anzuzeigen.")
        st.image("https://placehold.co/600x400/8CF0B4/FFFFFF?text=Ihre+Karte+hier", caption="Platzhalter für die Karte (keine Daten)")