import streamlit as st

st.set_page_config(
    page_title="Gipfel App",
    page_icon="🧗",
    layout="centered",
)

st.title("🏔️ Gipfel App Übersicht")

st.markdown("""
Willkommen zur **Gipfel App**!  
Navigiere über die Seitenleiste zu den folgenden Funktionen:

- ➕ Begehung hinzufügen
- 📊 Auswertungen anzeigen
- 🔍 Gipfel oder Routen suchen
- 🧑‍💻 (später: Login & Nutzerverwaltung)

---
""")

st.info("Nutze die Seitenleiste links, um zwischen den Funktionen zu wechseln.")
