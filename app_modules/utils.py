# app_modules/utils.py

import pandas as pd
import streamlit as st
from supabase import Client

def get_last_climbed_rocks_data(supabase: Client, user_id: str, num_rocks: int = 10):
    """
    Ruft die Daten der letzten N bestiegenen Felsen für einen bestimmten Benutzer ab.
    Gibt eine Liste von Dictionaries mit 'name' und 'gipfel_id' zurück.
    """
    if not user_id:
        return []

    try:
        # 1. Begehungen (ascents) abrufen, sortiert nach Datum absteigend
        ascents_data = supabase.table("ascents").select("gipfel_id, datum").eq("user_id", user_id).order("datum", desc=True).limit(num_rocks * 3).execute().data
        ascents_df = pd.DataFrame(ascents_data)

        if ascents_df.empty:
            return []

        # Sicherstellen, dass 'datum' ein datetime-Objekt ist und ungültige Daten entfernen
        ascents_df['datum'] = pd.to_datetime(ascents_df['datum'], errors='coerce')
        ascents_df.dropna(subset=['datum'], inplace=True)

        # 2. Felsen (rocks) abrufen, um Namen zu bekommen
        unique_gipfel_ids = ascents_df['gipfel_id'].dropna().astype(int).unique().tolist()
        if not unique_gipfel_ids:
            return []

        rocks_data = supabase.table("rocks").select("id, name").in_("id", unique_gipfel_ids).execute().data
        rocks_df = pd.DataFrame(rocks_data)

        if rocks_df.empty:
            return []

        # 3. Begehungen mit Felsen-Namen mergen und die letzten N einzigartigen auswählen
        merged_df = pd.merge(
            ascents_df,
            rocks_df,
            left_on='gipfel_id',
            right_on='id',
            how='inner'
        )

        # Sortiere nochmals nach Datum (wichtig, um die neuesten Duplikate zu behalten)
        merged_df = merged_df.sort_values(by='datum', ascending=False)

        # Entferne Duplikate basierend auf 'gipfel_id', behalte den ersten (also den neuesten)
        last_unique_climbs = merged_df.drop_duplicates(subset=['gipfel_id'], keep='first')

        # Wähle die letzten N einzigartigen bestiegenen Felsen aus
        result = last_unique_climbs[['name', 'gipfel_id']].head(num_rocks).to_dict(orient='records')
        
        return result

    except Exception as e:
        st.error(f"Fehler beim Abrufen der letzten bestiegenen Felsen: {e}")
        return []

# --- Neue Funktion zum Anzeigen in Streamlit ---
def display_last_climbed_rocks(supabase: Client, user_id: str, num_rocks: int = 10):
    """
    Zeigt die Liste der letzten N bestiegenen Felsen in Streamlit an.
    """
    st.subheader(f"Zuletzt bestiegene Gipfel ({num_rocks})")
    
    last_climbs = get_last_climbed_rocks_data(supabase, user_id, num_rocks)

    if last_climbs:
        for i, rock in enumerate(last_climbs):
            st.markdown(f"- **{rock['name']}** (ID: {rock['gipfel_id']})")
    else:
        st.info("Noch keine Gipfel bestiegen oder keine Daten gefunden.")