"""
Mon Petit Portefeuille — Classement au portefeuille de la ligue MPP.

Architecture : au premier chargement, l'app fait TOUS les appels (4 bookmakers × N joueurs)
avec une mise fixée à 1€. Ensuite le slider de mise multiplie les résultats côté client
et le sélecteur de bookmaker switche entre les datasets pré-calculés. Zéro re-fetch.
"""
from __future__ import annotations

import io
import json
import time
from urllib import request, error

import pandas as pd
import streamlit as st

API_URL = "https://mes-profits-pronos.vercel.app/api/calculate"
BOOKMAKERS = ["best", "betclic", "unibet", "winamax"]
BOOKMAKER_LABELS = {
    "best": "🏆 Meilleure cote",
    "betclic": "Betclic",
    "unibet": "Unibet",
    "winamax": "Winamax",
}
DELAY_SEC = 0.1

# ─── Ligue par défaut : "Coupe du Mao (à mao)" ────────────────────────────────
DEFAULT_LEAGUE_NAME = "Coupe du Mao (à mao)"
DEFAULT_LEAGUE = [
    ("Adedadz",          "Adélaïde",  1,  4811),
    ("AlexRougier",      "Alexandre", 2,  4629),
    ("Sir_Chatonne",     "Alexandre", 3,  4329),
    ("K-Dab",            "Karim",     4,  4324),
    ("M9rgan",           "Morgan",    5,  4079),
    ("GOAT#UEBF1WEA",    "Gilian",    6,  3922),
    ("Foz",              "Clément",   7,  3920),
    ("CedreLePoulpe",    "Cedric",    8,  3805),
    ("Merwi",            "Marie",     9,  3713),
    ("Jean-Porc-Jajo",   "Jade",      10, 3711),
    ("HugBagr",          "Hug",       11, 3650),
    ("BRANDAO_DOBRAZIL", "Samba",     12, 3394),
    ("Pascalou_",        "Thomas",    13, 1556),
]


# ─── Setup page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mon Petit Portefeuille",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 26px; font-weight: 700; }
    h1 { letter-spacing: -0.02em; }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(244, 196, 48, 0.15);
        color: #F4C430;
        border-radius: 6px;
        font-size: 12px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)


# ─── Fetching (mise fixée à 1€, tout est linéaire) ────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_at_1eur(username: str, bookmaker: str) -> dict | None:
    body = json.dumps({"username": username, "bookmaker": bookmaker, "stake": 1}).encode()
    req = request.Request(
        API_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def load_all_data(usernames: list) -> dict:
    """Retourne {bookmaker: {username: data_1eur}}. Affiche une progress bar."""
    result: dict = {bm: {} for bm in BOOKMAKERS}
    failed: list = []
    total = len(usernames) * len(BOOKMAKERS)
    done = 0
    progress = st.progress(0.0, text="Chargement des données…")

    for u in usernames:
        for bm in BOOKMAKERS:
            done += 1
            progress.progress(done / total, text=f"[{done}/{total}]  {u}  ·  {bm}")
            data = fetch_at_1eur(u, bm)
            if data:
                result[bm][u] = data
            else:
                failed.append(f"{u} ({bm})")
            time.sleep(DELAY_SEC)

    progress.empty()
    return {"data": result, "failed": failed}


def parse_input(raw: str):
    raw = raw.strip()
    if not raw:
        return [], {}

    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
            standings = data.get("standings") if isinstance(data, dict) else data
            if isinstance(standings, list) and standings and "user" in standings[0]:
                usernames, mpp = [], {}
                for s in standings:
                    u = s["user"].get("username")
                    if not u:
                        continue
                    usernames.append(u)
                    mpp[u] = {
                        "firstname": (s["user"].get("firstName") or "").strip(),
                        "mpp_rank": s.get("ranking", {}).get("rank"),
                        "mpp_points": s.get("ranking", {}).get("points"),
                    }
                return usernames, mpp
        except json.JSONDecodeError:
            pass

    seen, usernames = set(), []
    for line in raw.split("\n"):
        u = line.strip()
        if u and u not in seen:
            usernames.append(u)
            seen.add(u)
    return usernames, {}


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown('<span class="badge">Coupe du Monde 2026</span>', unsafe_allow_html=True)
st.title("Classement au portefeuille")
st.caption(
    "Combien chaque joueur aurait gagné en pariant ses pronostics MPP pour de vrai. "
    "Données via [mes-profits-pronos.vercel.app](https://mes-profits-pronos.vercel.app) d'Arthur Labbaye."
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("👥 Ligue")
    league_mode = st.radio(
        "Ligue",
        options=[DEFAULT_LEAGUE_NAME, "Autre ligue"],
        index=0,
        label_visibility="collapsed",
    )
    if league_mode == "Autre ligue":
        st.caption("Colle une liste de pseudos (un par ligne) ou le JSON MPP.")
        custom_input = st.text_area(
            "Pseudos ou JSON",
            height=180,
            placeholder="pseudo1\npseudo2\n...",
            label_visibility="collapsed",
            key="custom_input",
        )
    else:
        custom_input = ""

    st.divider()

    st.header("⚙️ Paramètres")
    bookmaker = st.selectbox(
        "Bookmaker",
        options=BOOKMAKERS,
        format_func=lambda x: BOOKMAKER_LABELS[x],
        index=0,
    )
    stake = st.slider("Mise par pari (€)", min_value=1, max_value=100, value=10, step=1)

# ─── Résolution ligue ─────────────────────────────────────────────────────────
if league_mode == DEFAULT_LEAGUE_NAME:
    usernames = [row[0] for row in DEFAULT_LEAGUE]
    mpp_data = {row[0]: {"firstname": row[1], "mpp_rank": row[2], "mpp_points": row[3]}
                for row in DEFAULT_LEAGUE}
    league_key = f"default:{len(usernames)}"
else:
    usernames, mpp_data = parse_input(custom_input)
    league_key = f"custom:{','.join(usernames)}"

if not usernames:
    st.info("👈 Colle une liste de pseudos ou le JSON MPP dans la sidebar pour commencer.")
    st.stop()

# ─── Chargement (une fois par ligue) ──────────────────────────────────────────
if st.session_state.get("league_key") != league_key:
    with st.status(f"Chargement de {len(usernames)} joueurs × {len(BOOKMAKERS)} bookmakers…",
                   expanded=False) as status:
        loaded = load_all_data(usernames)
        st.session_state.league_data = loaded["data"]
        st.session_state.league_failed = loaded["failed"]
        st.session_state.league_key = league_key
        status.update(label=f"✓ Données chargées ({len(usernames)*len(BOOKMAKERS)} requêtes)",
                      state="complete", expanded=False)

all_data = st.session_state.league_data
failed = st.session_state.league_failed

if failed:
    with st.expander(f"⚠️ {len(failed)} appel(s) échoué(s)"):
        st.write(", ".join(failed))

# ─── Build display avec bookmaker + stake courants ────────────────────────────
current_data = all_data[bookmaker]
if not current_data:
    st.error(f"Aucune donnée pour le bookmaker {bookmaker}.")
    st.stop()

rows = []
for u, d in current_data.items():
    info = mpp_data.get(u, {})
    rows.append({
        "pseudo": u,
        "prenom": info.get("firstname", ""),
        "mpp_rank": info.get("mpp_rank"),
        "mpp_points": info.get("mpp_points"),
        # Multiplication linéaire par la mise
        "profit": d["profit"] * stake,
        "total_stake": d["totalStake"] * stake,
        # Ces valeurs sont indépendantes de la mise
        "roi": d["roi"],
        "wins": d["wins"],
        "bets": d["bets"],
        "win_rate": d["winRate"],
        "avg_odd": d["averageOdd"],
        "best_streak": d.get("bestWinStreak"),
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

st.subheader(f"📊 {BOOKMAKER_LABELS[bookmaker]}  ·  mise {stake}€")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Joueurs", len(df))
c2.metric(
    "Cumul ligue",
    f"{'+' if total_profit >= 0 else ''}{total_profit:,.2f}€".replace(",", " "),
    delta=f"ROI ligue {league_roi:+.1f}%",
    delta_color="normal" if league_roi >= 0 else "inverse",
)
c3.metric("ROI moyen joueur", f"{avg_roi:+.1f}%")
c4.metric("Rentables", f"{positives} / {len(df)}")

# ─── Podium ───────────────────────────────────────────────────────────────────
st.subheader("🏆 Podium")
p1, p2, p3 = st.columns(3)
for col, (_, row), medal in zip((p1, p2, p3), df.head(3).iterrows(), ["🥇", "🥈", "🥉"]):
    name = row["pseudo"] + (f"  ·  {row['prenom']}" if row["prenom"] else "")
    col.metric(
        label=f"{medal}  {name}",
        value=f"{'+' if row['profit']>=0 else ''}{row['profit']:.2f}€",
        delta=f"ROI {row['roi']:+.1f}%  ·  {row['wins']}/{row['bets']}",
        delta_color="off",
    )

# ─── Tableau complet ──────────────────────────────────────────────────────────
st.subheader("Classement complet")

display_df = df.copy()
display_df["#"] = display_df["money_rank"]
display_df["Joueur"] = display_df.apply(
    lambda r: f"{r['pseudo']}" + (f" · {r['prenom']}" if r['prenom'] else ""), axis=1)
display_df["Profit (€)"] = display_df["profit"].apply(lambda x: f"{'+' if x>=0 else ''}{x:.2f}")
display_df["ROI (%)"] = display_df["roi"].apply(lambda x: f"{x:+.1f}")
display_df["Bilan"] = display_df.apply(lambda r: f"{r['wins']}/{r['bets']}", axis=1)
display_df["Taux (%)"] = display_df["win_rate"].apply(lambda x: f"{x:.0f}")
display_df["Cote moy."] = display_df["avg_odd"].apply(lambda x: f"{x:.2f}")

has_mpp = "mpp_rank" in display_df.columns and display_df["mpp_rank"].notna().any()
if has_mpp:
    display_df["Rang MPP"] = display_df["mpp_rank"].apply(
        lambda x: f"#{int(x)}" if pd.notna(x) else "—")
    display_df["Δ"] = display_df.apply(
        lambda r: ("↑" + str(int(r["delta"]))) if pd.notna(r.get("delta")) and r["delta"] > 0
                 else (("↓" + str(int(abs(r["delta"])))) if pd.notna(r.get("delta")) and r["delta"] < 0
                 else "="),
        axis=1,
    )
    cols = ["#", "Joueur", "Profit (€)", "ROI (%)", "Bilan", "Taux (%)", "Cote moy.", "Rang MPP", "Δ"]
else:
    cols = ["#", "Joueur", "Profit (€)", "ROI (%)", "Bilan", "Taux (%)", "Cote moy."]

st.dataframe(
    display_df[cols].set_index("#"),
    use_container_width=True,
    height=(len(display_df) + 1) * 35 + 3,
)

# ─── Insights ─────────────────────────────────────────────────────────────────
with st.expander("💡 Insights", expanded=True):
    best = df.iloc[0]
    worst = df.iloc[-1]
    st.markdown(
        f"**Meilleur profit** : `{best['pseudo']}` avec **{best['profit']:+.2f}€** "
        f"(cote moy. {best['avg_odd']:.2f}, {best['bets']} paris)"
    )
    st.markdown(
        f"**Pire résultat** : `{worst['pseudo']}` avec **{worst['profit']:+.2f}€**"
    )

    if has_mpp and "delta" in df.columns and df["delta"].notna().any():
        deltas = df.dropna(subset=["delta"])
        climber = deltas.loc[deltas["delta"].idxmax()]
        faller = deltas.loc[deltas["delta"].idxmin()]
        if climber["delta"] > 0:
            st.markdown(
                f"**Meilleur choix de cotes** : `{climber['pseudo']}` gagne "
                f"**{int(climber['delta'])} places** vs son rang MPP (parie sur des paris mieux payés)"
            )
        if faller["delta"] < 0:
            st.markdown(
                f"**Cocheur de favoris** : `{faller['pseudo']}` perd "
                f"**{int(abs(faller['delta']))} places** vs son rang MPP (bons pronos, cotes pourries)"
            )

# ─── Comparaison bookmakers ───────────────────────────────────────────────────
with st.expander("📈 Comparer les 4 bookmakers"):
    comp_rows = []
    for bm in BOOKMAKERS:
        bm_data = all_data[bm]
        if not bm_data:
            continue
        total = sum(d["profit"] * stake for d in bm_data.values())
        avg_r = sum(d["roi"] for d in bm_data.values()) / len(bm_data)
        pos = sum(1 for d in bm_data.values() if d["profit"] > 0)
        comp_rows.append({
            "Bookmaker": BOOKMAKER_LABELS[bm],
            "Cumul ligue (€)": f"{'+' if total>=0 else ''}{total:.2f}",
            "ROI moyen (%)": f"{avg_r:+.1f}",
            "Rentables": f"{pos} / {len(bm_data)}",
        })
    st.dataframe(pd.DataFrame(comp_rows).set_index("Bookmaker"),
                 use_container_width=True)

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
)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Basé sur [Mes Profits Pronos](https://mes-profits-pronos.vercel.app) d'Arthur Labbaye. "
    "Cotes historiques via OddsPortal. Données mises en cache 1h."
)
