"""
Mon Petit Portefeuille — Classement au portefeuille de la ligue MPP.

Données figées via fetch_data.py. Zéro appel réseau à l'exécution.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from data import DATA, LEAGUE, LEAGUE_NAME, GENERATED_AT

BOOKMAKERS = ["best", "betclic", "unibet", "winamax"]
BOOKMAKER_LABELS = {
    "best": "🏆 Meilleure cote",
    "betclic": "Betclic",
    "unibet": "Unibet",
    "winamax": "Winamax",
}

# ─── Setup page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mon Petit Portefeuille",
    page_icon="⚽",
    layout="centered",  # meilleur rendu mobile qu'en wide
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Padding global réduit pour mobile */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1000px;
    }

    /* HERO */
    .hero-eyebrow {
        display: inline-block;
        padding: 5px 12px;
        background: rgba(244, 196, 48, 0.15);
        color: #F4C430;
        border-radius: 6px;
        font-size: 11px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: clamp(2.2rem, 8vw, 3.5rem);
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.05;
        margin: 0 0 12px 0;
        background: linear-gradient(135deg, #FFFFFF 0%, #A8B0C7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-subtitle {
        font-size: clamp(1.1rem, 4vw, 1.5rem);
        color: #F4C430;
        font-weight: 500;
        margin: 0 0 8px 0;
        line-height: 1.3;
    }
    .hero-caption {
        color: #7C8AA5;
        font-size: 0.9rem;
    }

    /* METRICS : plus compactes sur mobile */
    [data-testid="stMetricValue"] {
        font-size: clamp(20px, 5vw, 26px) !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #7C8AA5 !important;
    }
    [data-testid="stMetric"] {
        background: rgba(20, 27, 45, 0.6);
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(35, 45, 72, 0.6);
    }

    /* Podium : cards plus élégantes */
    .podium-card {
        background: linear-gradient(135deg, #141B2D 0%, #1A2237 100%);
        border: 1px solid #232D48;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 8px;
    }
    .podium-card.gold { border-color: #F4C430; box-shadow: 0 0 20px rgba(244,196,48,0.15); }
    .podium-card.silver { border-color: rgba(201, 207, 221, 0.5); }
    .podium-card.bronze { border-color: rgba(205, 140, 94, 0.5); }
    .podium-rank {
        font-size: 32px;
        line-height: 1;
        margin-bottom: 6px;
    }
    .podium-name {
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 8px;
        word-break: break-word;
    }
    .podium-profit {
        font-size: 24px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
    }
    .podium-profit.pos { color: #10D07E; }
    .podium-profit.neg { color: #FF5D5D; }
    .podium-meta {
        font-size: 11px;
        color: #7C8AA5;
        margin-top: 6px;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Insights et compare : cards visuelles */
    .insight-card {
        background: rgba(20, 27, 45, 0.6);
        border: 1px solid rgba(35, 45, 72, 0.6);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 8px;
    }
    .insight-label {
        font-size: 10px;
        letter-spacing: 0.1em;
        color: #7C8AA5;
        text-transform: uppercase;
        margin-bottom: 6px;
        font-family: 'JetBrains Mono', monospace;
    }
    .insight-value {
        font-size: 15px;
        line-height: 1.4;
    }
    .insight-value strong { color: #F4C430; }

    /* Comparateur bookmakers en tableau compact */
    .compare-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .compare-table th {
        text-align: left;
        padding: 8px;
        color: #7C8AA5;
        font-weight: 500;
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        border-bottom: 1px solid #232D48;
    }
    .compare-table td {
        padding: 10px 8px;
        border-bottom: 1px solid rgba(35, 45, 72, 0.4);
    }
    .compare-table tr.current td {
        background: rgba(244, 196, 48, 0.08);
    }
    .compare-table tr.current td:first-child::before {
        content: '▸ ';
        color: #F4C430;
    }
    .compare-table td.num {
        font-family: 'JetBrains Mono', monospace;
        text-align: right;
    }
    .compare-table .pos { color: #10D07E; }
    .compare-table .neg { color: #FF5D5D; }

    /* Sections */
    .section-title {
        font-size: 11px;
        letter-spacing: 0.15em;
        color: #7C8AA5;
        text-transform: uppercase;
        margin: 32px 0 12px;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Tableau du classement */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Sidebar totalement masquée */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* Cache Streamlit menu et footer sur mobile pour gagner de la place */
    @media (max-width: 640px) {
        .block-container { padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ─── Hero ─────────────────────────────────────────────────────────────────────
hero_html = (
    '<div>'
    f'<div class="hero-eyebrow">Coupe du Monde 2026 · {LEAGUE_NAME}</div>'
    '<h1 class="hero-title">Mon Petit Portefeuille</h1>'
    '<p class="hero-subtitle">Et si tu avais parié pour de vrai tes pronos MPP ?</p>'
    '<p class="hero-caption">Basé sur <a href="https://mes-profits-pronos.vercel.app" style="color:#7C8AA5">mes-profits-pronos.vercel.app</a> d\'Arthur Labbaye</p>'
    '</div>'
)
st.markdown(hero_html, unsafe_allow_html=True)

# ─── Sidebar : leviers live ───────────────────────────────────────────────────
mpp_data = {u: {"firstname": fn, "mpp_rank": r, "mpp_points": p} for u, fn, r, p in LEAGUE}

# ─── Paramètres inline (bookmaker + mise) ─────────────────────────────────────
col_bm, col_stake = st.columns([1, 2])
with col_bm:
    bookmaker = st.selectbox(
        "Bookmaker",
        options=BOOKMAKERS,
        format_func=lambda x: BOOKMAKER_LABELS[x],
        index=1,  # Betclic par défaut
    )
with col_stake:
    stake = st.slider("Mise par pari (€)", min_value=1, max_value=100, value=10, step=1)

# ─── Construction des lignes ──────────────────────────────────────────────────
current_data = DATA[bookmaker]
rows = []
for u, d in current_data.items():
    info = mpp_data.get(u, {})
    rows.append({
        "pseudo": u,
        "prenom": info.get("firstname", ""),
        "mpp_rank": info.get("mpp_rank"),
        "mpp_points": info.get("mpp_points"),
        "profit": d["profit"] * stake,
        "total_stake": d["totalStake"] * stake,
        "roi": d["roi"],
        "wins": d["wins"],
        "bets": d["bets"],
        "win_rate": d["winRate"],
        "avg_odd": d["averageOdd"],
    })

rows.sort(key=lambda r: r["profit"], reverse=True)
for i, r in enumerate(rows, start=1):
    r["money_rank"] = i
    if r["mpp_rank"]:
        r["delta"] = r["mpp_rank"] - i

df = pd.DataFrame(rows)

# ─── Stats ligue ──────────────────────────────────────────────────────────────
total_profit = df["profit"].sum()
avg_roi = df["roi"].mean()
positives = int((df["profit"] > 0).sum())
total_stakes = df["total_stake"].sum()
league_roi = (total_profit / total_stakes * 100) if total_stakes > 0 else 0

st.markdown('<div class="section-title">Chiffres de la ligue</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Joueurs", len(df))
c2.metric(
    "Cumul",
    f"{'+' if total_profit >= 0 else ''}{total_profit:,.0f}€".replace(",", " "),
    delta=f"{league_roi:+.1f}%",
    delta_color="normal" if league_roi >= 0 else "inverse",
)
c3.metric("ROI moyen", f"{avg_roi:+.1f}%")
c4.metric("Rentables", f"{positives}/{len(df)}")

# ─── Insights + Comparaison bookmakers (2 colonnes sur desktop, stackées mobile) ──
has_mpp = df["mpp_rank"].notna().any()
best = df.iloc[0]
worst = df.iloc[-1]
climber = faller = None
if has_mpp and "delta" in df.columns:
    deltas = df.dropna(subset=["delta"])
    if not deltas.empty:
        climber = deltas.loc[deltas["delta"].idxmax()]
        faller = deltas.loc[deltas["delta"].idxmin()]

col_insight, col_compare = st.columns([1, 1])

with col_insight:
    st.markdown('<div class="section-title">Insights</div>', unsafe_allow_html=True)
    parts = []
    parts.append(
        f'<div class="insight-card"><div class="insight-label">💰 Meilleur profit</div>'
        f'<div class="insight-value"><strong>{best["pseudo"]}</strong> · '
        f'{"+" if best["profit"]>=0 else ""}{best["profit"]:.2f}€ '
        f'<span style="color:#7C8AA5"> · cote moy. {best["avg_odd"]:.2f}</span></div></div>'
    )
    parts.append(
        f'<div class="insight-card"><div class="insight-label">📉 Pire résultat</div>'
        f'<div class="insight-value"><strong>{worst["pseudo"]}</strong> · '
        f'{"+" if worst["profit"]>=0 else ""}{worst["profit"]:.2f}€</div></div>'
    )
    if climber is not None and climber["delta"] > 0:
        parts.append(
            f'<div class="insight-card"><div class="insight-label">🎯 Meilleur choix de cotes</div>'
            f'<div class="insight-value"><strong>{climber["pseudo"]}</strong> gagne '
            f'<strong>{int(climber["delta"])} places</strong>'
            f'<span style="color:#7C8AA5"> vs son rang MPP</span></div></div>'
        )
    if faller is not None and faller["delta"] < 0:
        parts.append(
            f'<div class="insight-card"><div class="insight-label">🐑 Cocheur de favoris</div>'
            f'<div class="insight-value"><strong>{faller["pseudo"]}</strong> perd '
            f'<strong>{int(abs(faller["delta"]))} places</strong>'
            f'<span style="color:#7C8AA5"> (bons pronos, cotes pourries)</span></div></div>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)

with col_compare:
    st.markdown('<div class="section-title">Comparaison bookmakers</div>', unsafe_allow_html=True)
    body_parts = []
    for bm in BOOKMAKERS:
        bm_data = DATA[bm]
        if not bm_data:
            continue
        total = sum(d["profit"] * stake for d in bm_data.values())
        pos = sum(1 for d in bm_data.values() if d["profit"] > 0)
        current_class = "current" if bm == bookmaker else ""
        pn_class = "pos" if total >= 0 else "neg"
        sign = "+" if total >= 0 else ""
        body_parts.append(
            f'<tr class="{current_class}"><td>{BOOKMAKER_LABELS[bm]}</td>'
            f'<td class="num {pn_class}">{sign}{total:.0f}€</td>'
            f'<td class="num" style="color:#7C8AA5">{pos}/{len(bm_data)}</td></tr>'
        )
    compare_html = (
        '<div class="insight-card" style="padding: 8px 14px;">'
        '<table class="compare-table">'
        '<thead><tr><th>Bookmaker</th>'
        '<th style="text-align:right">Cumul</th>'
        '<th style="text-align:right">Rentables</th></tr></thead>'
        '<tbody>' + "".join(body_parts) + '</tbody></table></div>'
    )
    st.markdown(compare_html, unsafe_allow_html=True)

# ─── Podium ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Podium</div>', unsafe_allow_html=True)

top3 = df.head(3)
p_cols = st.columns(3)
medals = ["🥇", "🥈", "🥉"]
classes = ["gold", "silver", "bronze"]
for col, (_, row), medal, cls in zip(p_cols, top3.iterrows(), medals, classes):
    with col:
        name = row["pseudo"] + (f"<br><span style='font-size:11px;color:#7C8AA5;font-weight:400'>{row['prenom']}</span>" if row["prenom"] else "")
        profit_class = "pos" if row['profit'] >= 0 else "neg"
        sign = "+" if row['profit'] >= 0 else ""
        podium_html = (
            f'<div class="podium-card {cls}">'
            f'<div class="podium-rank">{medal}</div>'
            f'<div class="podium-name">{name}</div>'
            f'<div class="podium-profit {profit_class}">{sign}{row["profit"]:.2f}€</div>'
            f'<div class="podium-meta">ROI {row["roi"]:+.1f}% · {row["wins"]}/{row["bets"]}</div>'
            f'</div>'
        )
        st.markdown(podium_html, unsafe_allow_html=True)

# ─── Tableau complet ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Classement complet</div>', unsafe_allow_html=True)

display_df = df.copy()
display_df["#"] = display_df["money_rank"]
display_df["Joueur"] = display_df.apply(
    lambda r: f"{r['pseudo']}" + (f" · {r['prenom']}" if r['prenom'] else ""), axis=1)
display_df["Profit"] = display_df["profit"].apply(lambda x: f"{'+' if x>=0 else ''}{x:.2f}€")
display_df["ROI"] = display_df["roi"].apply(lambda x: f"{x:+.1f}%")
display_df["Bilan"] = display_df.apply(lambda r: f"{r['wins']}/{r['bets']}", axis=1)
display_df["Cote"] = display_df["avg_odd"].apply(lambda x: f"{x:.2f}")

if has_mpp:
    display_df["MPP"] = display_df["mpp_rank"].apply(
        lambda x: f"#{int(x)}" if pd.notna(x) else "—")
    display_df["Δ"] = display_df.apply(
        lambda r: ("↑" + str(int(r["delta"]))) if pd.notna(r.get("delta")) and r["delta"] > 0
                 else (("↓" + str(int(abs(r["delta"])))) if pd.notna(r.get("delta")) and r["delta"] < 0
                 else "="),
        axis=1,
    )
    cols = ["#", "Joueur", "Profit", "ROI", "Bilan", "Cote", "MPP", "Δ"]
else:
    cols = ["#", "Joueur", "Profit", "ROI", "Bilan", "Cote"]

st.dataframe(
    display_df[cols].set_index("#"),
    use_container_width=True,
    height=(len(display_df) + 1) * 36 + 3,
)

# ─── Export CSV ───────────────────────────────────────────────────────────────
csv_buf = io.StringIO()
export_cols = ["money_rank", "pseudo", "prenom", "profit", "roi", "wins", "bets",
               "win_rate", "avg_odd", "total_stake", "mpp_rank", "mpp_points"]
if "delta" in df.columns:
    export_cols.append("delta")
df[export_cols].to_csv(csv_buf, index=False)

st.download_button(
    "📥 Télécharger le CSV",
    data=csv_buf.getvalue(),
    file_name=f"classement-{bookmaker}-{stake}eur.csv",
    mime="text/csv",
    use_container_width=True,
)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.caption(
    f"Cotes historiques via OddsPortal (Betclic, Unibet, Winamax). "
    f"Données figées du {GENERATED_AT}."
)
