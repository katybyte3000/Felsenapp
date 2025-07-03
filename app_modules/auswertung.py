import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# .env laden
load_dotenv()

# Supabase-Verbindung initialisieren
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- NEUE FARBKONZEPT KONSTANTEN (Müssen mit app.py übereinstimmen) ---
PLOT_BG_COLOR = "#FFEF16"         # Hellgelb
PLOT_HIGHLIGHT_COLOR = "#006D77"  # Petrol (Hauptfarbe, z.B. für Vorstieg)
PLOT_POSITIVE_COLOR = "#3BB273"   # Grün
PLOT_NEGATIVE_COLOR = "#8E44AD"   # Lila (wird jetzt weniger verwendet)
PLOT_SECONDARY_COLOR = "#83C5BE"  # Helles Petrol (für Nachstieg und sekundäre Elemente)
PLOT_TEXT_COLOR = "#1D1D1D"       # Dunkelgrau
PLOT_OUTLINE_COLOR = "#1D1D1D"    # Dunkelgrau (für Plotly-Element-Outlines)

def apply_plotly_styles(fig):
    """
    Setzt den Hintergrund und die allgemeine Textfarbe für Plotly-Diagramme.
    Beachtet die Schriftarten aus dem globalen CSS.
    """
    fig.update_layout(
        paper_bgcolor=PLOT_BG_COLOR,
        plot_bgcolor=PLOT_BG_COLOR,
        font=dict(
            color=PLOT_TEXT_COLOR,
            family='Noto Sans, sans-serif', # Standard für Achsen, Legenden etc.
            size=12 # Standard-Schriftgröße für Plot-Text
        )
    )
    # Setzt die Farbe der Achsentitel und Ticks auf Noto Sans Bold
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=14), title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=16, weight='bold'))
    fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=14), title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=16, weight='bold'))
    return fig

@st.cache_data
def fetch_data(user_id):
    """
    Holt Daten aus Supabase, gefiltert nach der user_id.
    """
    rocks = pd.DataFrame(supabase.table("rocks").select("id, name, sector_id, latitude, longitude, hoehe").range(0, 5000).execute().data)
    routes = pd.DataFrame(supabase.table("routes").select("id, rock_id, number").range(0, 5000).execute().data)
    sectors = pd.DataFrame(supabase.table("sector").select("id, name").execute().data)

    if user_id:
        ascents_data = supabase.table("ascents").select("route_id, gipfel_id, stil, datum, partnerin, user_id").eq("user_id", user_id).order("datum", desc=True).execute().data
        ascents = pd.DataFrame(ascents_data)
    else:
        ascents = pd.DataFrame()

    return rocks, ascents, sectors, routes

# --- Hauptfunktion für die Statistikseite ---
def main_app_auswertung():
    st.title("Gipfel Statistik") # Der Haupttitel bleibt Oswald durch app.py CSS

    if st.session_state.user_id is None:
        st.error("Fehler: Kein Benutzer eingeloggt. Bitte melden Sie sich an, um Ihre Statistiken zu sehen.")
        return

    rocks, ascents, sectors, routes = fetch_data(st.session_state.user_id)

    if ascents.empty:
        st.info("Sie haben noch keine Begehungen eingetragen. Tragen Sie Ihre erste Begehung auf der Seite 'Begehung hinzufügen' ein!")
        return

    ascents['datum'] = pd.to_datetime(ascents['datum'], errors='coerce')
    current_year = datetime.now().year

    total_rocks = len(rocks)
    unique_done_rocks = ascents['gipfel_id'].dropna().astype(int).unique()
    num_done_rocks = len(unique_done_rocks)
    unique_done_routes_array = ascents['route_id'].dropna().astype(int).unique()
    num_done_routes = len(unique_done_routes_array)
    percent_done = round((num_done_rocks / total_rocks) * 100, 1) if total_rocks > 0 else 0

    # Überschrift "ÜBERBLICK" jetzt mit div-Tag
    st.markdown('<div class="headline-fonts">Überblick</div>', unsafe_allow_html=True) # headline-fonts nutzt jetzt Oswald

    col_d1, col_d2, col_stats = st.columns([1, 2, 2])

    with col_d1:
        donut_percent = percent_done
        fig_donut1 = go.Figure(go.Pie(values=[donut_percent, 100 - donut_percent], hole=0.7,
                                     marker_colors=[PLOT_HIGHLIGHT_COLOR, PLOT_SECONDARY_COLOR],
                                     marker_line_color=PLOT_OUTLINE_COLOR, marker_line_width=3,
                                     textinfo='none', sort=False))
        fig_donut1.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=250,
                                 annotations=[dict(text=f"<b>{donut_percent:.0f}%</b>", x=0.5, y=0.5,
                                                 font_size=36, showarrow=False, font_color=PLOT_TEXT_COLOR,
                                                 font_family='Oswald')])
        st.markdown("##### Geschafft", unsafe_allow_html=True)
        st.plotly_chart(apply_plotly_styles(fig_donut1), use_container_width=True)

    with col_d2:
        last_years = sorted(ascents['datum'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)[:3]
        if not last_years:
            last_years = [current_year - 2, current_year - 1, current_year]
        last_years = sorted(last_years)

        yearly_gipfel = []
        for y in last_years:
            count = ascents[ascents['datum'].dt.year == y]['gipfel_id'].dropna().astype(int).nunique()
            yearly_gipfel.append(count)
        df_years = pd.DataFrame({'Jahr': [str(y) for y in last_years], 'Gipfel': yearly_gipfel})
        df_years = df_years.sort_values(by='Gipfel', ascending=True)

        fig_years = go.Figure()
        
        if not df_years.empty:
            max_gipfel_year = df_years.loc[df_years['Gipfel'].idxmax()]
            
            for i, row in df_years.iterrows():
                bar_color = PLOT_HIGHLIGHT_COLOR if row['Jahr'] == max_gipfel_year['Jahr'] else PLOT_SECONDARY_COLOR
                fig_years.add_trace(go.Bar(y=[row['Jahr']], x=[row['Gipfel']], orientation='h',
                                             marker_color=bar_color,
                                             marker_line_color=PLOT_OUTLINE_COLOR, marker_line_width=3,
                                             text=[f"{row['Gipfel']} "],
                                             textposition='outside',
                                             insidetextfont=dict(family='Noto Sans', size=24, color='white'),
                                             textfont=dict(family='Noto Sans', size=20, color=PLOT_TEXT_COLOR),
                                             hovertemplate=f"<b>{row['Jahr']}</b><br>Gipfel: {row['Gipfel']}<extra></extra>"))
        else:
            fig_years.add_trace(go.Bar(y=[], x=[], orientation='h'))

        fig_years.update_layout(
            title="Gipfel pro Jahr",
            title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=24),
            height=300,
            margin=dict(t=40, b=20),
            showlegend=False,
            transition=dict(duration=500),
            yaxis=dict(type='category', categoryorder='array', categoryarray=df_years['Jahr'].tolist() if not df_years.empty else [],
                             tickfont=dict(size=16, color=PLOT_TEXT_COLOR, family='Noto Sans')),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False)
        )
        st.plotly_chart(apply_plotly_styles(fig_years), use_container_width=True)

    with col_stats:
        top_partner = ascents['partnerin'].dropna().mode()
        top_partner_name = top_partner.iloc[0] if not top_partner.empty else "KEINE DATEN"
        if not ascents['gipfel_id'].dropna().empty:
            top_berg_id = ascents['gipfel_id'].dropna().astype(int).mode().iloc[0]
            gipfel_info = rocks[rocks['id'] == top_berg_id]
            if not gipfel_info.empty:
                berg_name_str = gipfel_info.iloc[0]['name'] if 'name' in gipfel_info.columns else f"Gipfel #{top_berg_id}"
            else:
                berg_name_str = f"Gipfel #{top_berg_id}"
        else:
            berg_name_str = "Keine Daten"
        total_routes_done = len(ascents)
        st.markdown(f"""<div style='line-height:1.2'><span style='font-family: "Noto Sans", sans-serif; font-weight: 700; font-size:18px; color:{PLOT_TEXT_COLOR}'>Top Partner*in</span><br><span style='font-family: "Oswald", sans-serif; font-size:46px; font-weight: 700; color:{PLOT_TEXT_COLOR}'>""" + top_partner_name + """</span></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div style='line-height:1.2; margin-top:1em'><span style='font-family: "Noto Sans", sans-serif; font-weight: 700; font-size:18px; color:{PLOT_TEXT_COLOR}'>Meistbegangener Gipfel</span><br><span style='font-family: "Oswald", sans-serif; font-size:46px; font-weight: 700; color:{PLOT_TEXT_COLOR}'>""" + berg_name_str + """</span></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div style='line-height:1.2; margin-top:1em'><span style='font-family: "Noto Sans", sans-serif; font-weight: 700; font-size:18px; color:{PLOT_TEXT_COLOR}'>Begangene Routen</span><br><span style='font-family: "Oswald", sans-serif; font-size:46px; font-weight: 700; color:{PLOT_TEXT_COLOR}'>""" + str(total_routes_done) + """</span></div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🧗 Begangene Routen", f"{num_done_routes}")
    with col2:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=percent_done,
                                     number={"suffix": "%", "font": {"color": PLOT_HIGHLIGHT_COLOR, "family": 'Oswald'}},
                                     title={"text": "Erreichte Felsen (in %)", "font": {"color": PLOT_TEXT_COLOR, "family": 'Noto Sans'}},
                                     gauge={'axis': {'range': [0, 100], "tickfont": {"color": PLOT_TEXT_COLOR, "family": 'Noto Sans'}},
                                            'bar': {'color': PLOT_HIGHLIGHT_COLOR},
                                            'steps': [{'range': [0, 100], 'color': PLOT_SECONDARY_COLOR}]}))
        st.plotly_chart(apply_plotly_styles(fig), use_container_width=True)
    with col3:
        if 'stil' in ascents.columns and not ascents['stil'].empty:
            stil_counts = ascents['stil'].value_counts()
            
            most_frequent_stil = stil_counts.index[0]

            pie_colors = [PLOT_HIGHLIGHT_COLOR if s == most_frequent_stil else PLOT_SECONDARY_COLOR for s in stil_counts.index]

            fig_pie = go.Figure(data=[go.Pie(labels=stil_counts.index, values=stil_counts.values, hole=0.4, textinfo='label+percent',
                                             marker=dict(colors=pie_colors,
                                                         line=dict(color=PLOT_OUTLINE_COLOR, width=3)),
                                             textfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'))])
            fig_pie.update_layout(title_text="Verteilung der Stile",
                                  title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=24),
                                  legend=dict(font=dict(family='Noto Sans', color=PLOT_TEXT_COLOR, size=14)))
            st.plotly_chart(apply_plotly_styles(fig_pie), use_container_width=True)
        else:
            st.info("Nicht genügend Daten oder 'stil'-Spalte fehlt für die Stil-Statistik.")

    # Überschrift "Übersicht pro Gebiet" jetzt mit div-Tag
    st.markdown('<div class="headline-fonts">Übersicht pro Gebiet</div>', unsafe_allow_html=True) # headline-fonts nutzt jetzt Oswald
    rocks['done'] = rocks['id'].isin(unique_done_rocks)
    sector_stats = rocks.groupby('sector_id')['done'].agg(['sum', 'count']).reset_index()
    sector_stats = sector_stats.merge(sectors, left_on='sector_id', right_on='id', how='left')
    sector_stats.rename(columns={'sum': 'begangen', 'count': 'gesamt', 'name': 'Gebiet'}, inplace=True)
    
    sector_stats = sector_stats.sort_values("begangen", ascending=True)

    fig_bar = go.Figure()

    if not sector_stats.empty:
        max_begangen_gebiet = sector_stats.loc[sector_stats['begangen'].idxmax()]
    else:
        max_begangen_gebiet = None

    for i, row in sector_stats.iterrows():
        fig_bar.add_trace(go.Bar(y=[row['Gebiet']], x=[row['gesamt']], name='Gesamt', orientation='h',
                                 marker_color=PLOT_SECONDARY_COLOR, marker_line_color=PLOT_OUTLINE_COLOR, marker_line_width=3))

        bar_color_begangen = PLOT_HIGHLIGHT_COLOR if max_begangen_gebiet is not None and row['Gebiet'] == max_begangen_gebiet['Gebiet'] else PLOT_OUTLINE_COLOR
        fig_bar.add_trace(go.Bar(y=[row['Gebiet']], x=[row['begangen']], name='Begangen', orientation='h',
                                 marker_color=bar_color_begangen, marker_line_color=PLOT_OUTLINE_COLOR, marker_line_width=3))

    fig_bar.update_layout(
        barmode='overlay',
        title='Felsen pro Gebiet (Petrol = Top-Gebiet, Dunkelgrau = begangen)',
        title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=24),
        xaxis_title='Anzahl Felsen',
        yaxis_title='',
        height=600,
        showlegend=False,
        yaxis=dict(tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans')),
        xaxis=dict(tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans')),
    )
    st.plotly_chart(apply_plotly_styles(fig_bar), use_container_width=True)

    # Überschrift "Entwicklung der Begehungen: Vor- und Nachstieg" jetzt mit div-Tag
    st.markdown('<div class="headline-fonts">Entwicklung der Begehungen: Vor- und Nachstieg</div>', unsafe_allow_html=True) # headline-fonts nutzt jetzt Oswald
    if 'datum' in ascents.columns and 'stil' in ascents.columns:
        vorstieg_ascents = ascents[ascents['stil'] == 'Vorstieg'].dropna(subset=['datum'])
        nachstieg_ascents = ascents[ascents['stil'] == 'Nachstieg'].dropna(subset=['datum'])

        fig_time = go.Figure()

        if not vorstieg_ascents.empty:
            vorstieg_by_month = vorstieg_ascents.groupby(pd.Grouper(key='datum', freq='M')).size()
            fig_time.add_trace(go.Scatter(x=vorstieg_by_month.index, y=vorstieg_by_month.values,
                                             mode='lines+markers', name='Vorstieg',
                                             line=dict(color=PLOT_HIGHLIGHT_COLOR, width=3, dash='solid'), # <<--- DURCHGEZOGEN
                                             marker=dict(color=PLOT_HIGHLIGHT_COLOR, size=8, line=dict(color=PLOT_OUTLINE_COLOR, width=2))))
        
        if not nachstieg_ascents.empty:
            nachstieg_by_month = nachstieg_ascents.groupby(pd.Grouper(key='datum', freq='M')).size()
            fig_time.add_trace(go.Scatter(x=nachstieg_by_month.index, y=nachstieg_by_month.values,
                                             mode='lines+markers', name='Nachstieg',
                                             line=dict(color=PLOT_SECONDARY_COLOR, width=3, dash='solid'), # <<--- DURCHGEZOGEN
                                             marker=dict(color=PLOT_SECONDARY_COLOR, size=8, line=dict(color=PLOT_OUTLINE_COLOR, width=2))))


        fig_time.update_layout(
            title='Begehungen pro Monat nach Stil',
            title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=24),
            xaxis_title='Monat',
            yaxis_title='Anzahl Begehungen',
            xaxis_title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
            yaxis_title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
            xaxis=dict(tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans')),
            yaxis=dict(tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans')),
            legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)', bordercolor=PLOT_OUTLINE_COLOR, borderwidth=1,
                        font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=14))
        )
        st.plotly_chart(apply_plotly_styles(fig_time), use_container_width=True)
    else:
        st.info("Nicht genügend Daten oder 'datum'/'stil'-Spalte fehlt für die Entwicklung der Begehungen.")

    # Überschrift "Kletterpartner*innen" jetzt mit div-Tag
    st.markdown('<div class="headline-fonts">Kletterpartner*innen</div>', unsafe_allow_html=True) # headline-fonts nutzt jetzt Oswald
    if 'partnerin' in ascents.columns and not ascents['partnerin'].empty:
        partner_counts = ascents['partnerin'].dropna().value_counts().reset_index()
        partner_counts.columns = ['Partner*in', 'Anzahl']

        most_frequent_partner = partner_counts.loc[partner_counts['Anzahl'].idxmax()]

        fig_partner_bar = px.bar(partner_counts, x='Anzahl', y='Partner*in', orientation='h', title='Häufigkeit der Kletterpartner*innen')
        
        bar_colors = [PLOT_HIGHLIGHT_COLOR if p == most_frequent_partner['Partner*in'] else PLOT_SECONDARY_COLOR for p in partner_counts['Partner*in']]
        fig_partner_bar.update_traces(marker_color=bar_colors, marker_line_color=PLOT_OUTLINE_COLOR, marker_line_width=3,
                                      text=partner_counts['Anzahl'], textposition='outside',
                                      textfont=dict(family='Noto Sans', size=20, color=PLOT_TEXT_COLOR))
        
        fig_partner_bar.update_layout(
            showlegend=False,
            yaxis={'categoryorder':'total ascending', 'tickfont':dict(color=PLOT_TEXT_COLOR, family='Noto Sans')},
            xaxis={'tickfont':dict(color=PLOT_TEXT_COLOR, family='Noto Sans')},
            title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=24),
            xaxis_title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
            yaxis_title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans')
        )
        st.plotly_chart(apply_plotly_styles(fig_partner_bar), use_container_width=True)
    else:
        st.info("Nicht genügend Daten oder 'partnerin'-spalte fehlt für die Partner-Statistik.")

    # Überschrift "Dein Ziel: Alle 1201 Gipfel" jetzt mit div-Tag
    st.markdown('<div class="headline-fonts">Dein Ziel: Alle 1201 Gipfel</div>', unsafe_allow_html=True) # headline-fonts nutzt jetzt Oswald

    ascents_with_year = ascents.copy()
    ascents_with_year = ascents_with_year.dropna(subset=['datum'])
    if not ascents_with_year.empty:
        ascents_with_year['jahr'] = ascents_with_year['datum'].dt.year.astype(int)
    else:
        st.info("Nicht genügend Daten, um eine durchschnittliche Kletterstatistik pro Jahr zu berechnen.")

    yearly_unique_gipfel = pd.Series()
    if not ascents_with_year.empty:
        yearly_unique_gipfel = ascents_with_year.groupby('jahr')['gipfel_id'].nunique()

    average_yearly_peaks = 0
    if not yearly_unique_gipfel.empty:
        average_yearly_peaks = yearly_unique_gipfel.mean()
        # Verwendet die highlight-number Klasse
        st.markdown(f"Durchschnittlich kletterst du <span class='highlight-number'>**{average_yearly_peaks:.1f}**</span> neue Gipfel pro Jahr.", unsafe_allow_html=True)
    else:
        st.info("Um das Ziel zu erreichen, musst du zuerst Gipfel klettern!")

    remaining_peaks = 1201 - num_done_rocks

    years_to_finish_current = "N/A"
    if average_yearly_peaks > 0:
        years_to_finish_current = remaining_peaks / average_yearly_peaks
        # Verwendet die highlight-number Klasse
        st.markdown(f"Bei diesem Tempo erreichst du dein Ziel in ca. <span class='highlight-number'>**{years_to_finish_current:.1f} Jahren**</span>.", unsafe_allow_html=True)
    else:
        st.info("Um das Ziel zu erreichen, musst du zuerst Gipfel klettern!")

    years_to_finish_doubled = "N/A"
    if average_yearly_peaks > 0:
        years_to_finish_doubled = remaining_peaks / (average_yearly_peaks * 2)
        # Verwendet die highlight-number Klasse
        st.markdown(f"Wenn du doppelt so viele Gipfel pro Jahr kletterst, erreichst du dein Ziel in ca. <span class='highlight-number'>**{years_to_finish_doubled:.1f} Jahren**</span>.", unsafe_allow_html=True)
    else:
        st.info("Um das Ziel zu erreichen, musst du zuerst Gipfel klettern!")

    # --- GEÄNDERTE GRAFISCHE DARSTELLUNG: Deine letzten Begehungen (Bubble Chart) ---
    st.markdown('<div class="headline-fonts">Deine letzten Begehungen</div>', unsafe_allow_html=True)

    if not ascents.empty:
        # Sortieren nach Datum, um die "letzten" zu bekommen
        recent_ascents = ascents.sort_values(by='datum', ascending=False).head(10).copy()

        # Mergen mit Routen, um die Schwierigkeit zu bekommen
        merged_for_chart = recent_ascents.merge(
            routes[['id', 'number']],
            left_on='route_id',
            right_on='id',
            how='left'
        ).rename(columns={'number': 'Schwierigkeit_Num'})

        # Mergen mit Rocks, um den Gipfelnamen zu bekommen
        merged_for_chart = merged_for_chart.merge(
            rocks[['id', 'name']],
            left_on='gipfel_id', # Das ist der Schlüssel für rocks
            right_on='id',
            how='left'
        ).rename(columns={'name': 'Gipfel_Name'})

        # Vorbereiten der Daten für das Bubble-Chart
        chart_data = pd.DataFrame()
        chart_data['Datum'] = merged_for_chart['datum']
        chart_data['Schwierigkeit'] = merged_for_chart['Schwierigkeit_Num'].fillna(0).astype(int)
        chart_data['Gipfel'] = merged_for_chart['Gipfel_Name'].fillna('Unbekannter Gipfel')
        chart_data['Stil'] = merged_for_chart['stil'].fillna('Unbekannt')
        chart_data['Partner'] = merged_for_chart['partnerin'].fillna('Ohne Partner')

        # Farben basierend auf Stil (einheitliche Blautöne)
        chart_data['Farbe'] = chart_data['Stil'].apply(
            lambda x: PLOT_HIGHLIGHT_COLOR if x == 'Vorstieg' else PLOT_SECONDARY_COLOR
        )

        # Plotly Bubble Chart erstellen
        fig_last_ascents = go.Figure()

        if not chart_data.empty:
            # Sortieren nach Datum für bessere Darstellung im Bubble Chart
            chart_data = chart_data.sort_values(by='Datum', ascending=True)

            for stil_type in chart_data['Stil'].unique():
                subset = chart_data[chart_data['Stil'] == stil_type]
                fig_last_ascents.add_trace(go.Scatter(
                    x=subset['Datum'],
                    y=subset['Schwierigkeit'],
                    mode='markers',
                    name=stil_type,
                    marker=dict(
                        size=subset['Schwierigkeit'] * 5, # Größe der Bubble basierend auf Schwierigkeit
                        color=subset['Farbe'],
                        sizemode='diameter',
                        line=dict(color=PLOT_OUTLINE_COLOR, width=2)
                    ),
                    hovertemplate=(
                        "<b>Gipfel:</b> %{customdata[0]}<br>"
                        "<b>Datum:</b> %{x|%d.%m.%Y}<br>"
                        "<b>Schwierigkeit:</b> %{y}<br>"
                        "<b>Stil:</b> %{customdata[1]}<br>"
                        "<b>Partner:</b> %{customdata[2]}<extra></extra>"
                    ),
                    customdata=subset[['Gipfel', 'Stil', 'Partner']]
                ))

        fig_last_ascents.update_layout(
            title="Deine letzten 10 Begehungen (Schwierigkeit als Bubble-Größe)",
            title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=24),
            xaxis_title="Datum",
            yaxis_title="Schwierigkeit",
            xaxis_title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
            yaxis_title_font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
            xaxis=dict(tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
                       # Formatierung der Datums-Achse für bessere Lesbarkeit
                       tickformat='%d.%m.%Y'),
            yaxis=dict(tickfont=dict(color=PLOT_TEXT_COLOR, family='Noto Sans'),
                       dtick=1, # Zeigt nur ganze Zahlen für Schwierigkeit
                       range=[0.5, 10.5]), # Skaliert von 1 bis 10
            showlegend=True,
            legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)', bordercolor=PLOT_OUTLINE_COLOR, borderwidth=1,
                        font=dict(color=PLOT_TEXT_COLOR, family='Noto Sans', size=14)),
            height=500
        )
        st.plotly_chart(apply_plotly_styles(fig_last_ascents), use_container_width=True)
    else:
        st.info("Keine Begehungen im 'ascents'-DataFrame, um die letzten Gipfel grafisch anzuzeigen.")