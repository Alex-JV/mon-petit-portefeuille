"""
Mon Petit Portefeuille — Classement au portefeuille de la ligue MPP.

Streamlit app à déployer sur Streamlit Community Cloud.
"""
from __future__ import annotations

import io
import json
import time
from urllib import request, error

import pandas as pd
import streamlit as st

API_URL = "https://mes-profits-pronos.vercel.app/api/calculate"
DELAY_SEC = 0.25

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

# CSS pour un look plus soigné
st.markdown("""
<style>
    /* Podium metrics */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }
    /* Tables plus jolies */
    .dataframe { font-size: 14px; }
    /* Headers */
    h1 { letter-spacing: -0.02em; }
    /* Ligne de badge sous titre */
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


# ─── Fetching (avec cache pour éviter de spammer Arthur) ──────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_one(username: str, bookmaker: str, stake: float) -> dict | None:
    body = json.dumps({"username": username, "bookmaker": bookmaker, "stake": stake}).encode()
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


def parse_input(raw: str) -> tuple[list[str], dict]:
    """Retourne (usernames, mpp_map). mpp_map: username -> {firstname, mpp_rank, mpp_points}"""
    raw = raw.strip()
    if not raw:
        return [], {}

    # Try JSON
    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
            standings = data.get("standings") if isinstance(data, dict) else data
            if isinstance(standings, list) and standings and "user" in standings[0]:
                usernames = []
                mpp = {}
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

    # Fallback: line-per-username
    seen = set()
    usernames = []
    for line in raw.split("\n"):
        u = line.strip()
        if u and u not in seen:
            usernames.append(u)
            seen.add(u)
    return usernames, {}


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown('<span class="badge">Coupe du Monde 2026</span>', unsafe_allow_html=True)
st.title("Classement au portefeuille")
st.markdown(
    "Combien chaque joueur de la ligue aurait gagné en pariant réellement ses pronostics MPP ? "
    "L'app compare tes pronos aux cotes historiques Betclic / Unibet / Winamax."
)
st.caption("Données via [mes-profits-pronos.vercel.app](https://mes-profits-pronos.vercel.app) d'Arthur Labbaye")

# ─── Sidebar : config ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    bookmaker = st.selectbox(
        "Bookmaker",
        options=["best", "betclic", "unibet", "winamax"],
        format_func=lambda x: {"best": "Meilleure cote", "betclic": "Betclic", "unibet": "Unibet", "winamax": "Winamax"}[x],
        index=0,
    )

    stake = st.number_input("Mise par pari (€)", min_value=1, max_value=100, value=10, step=1)

    st.divider()

    st.subheader("👥 Ligue")
    league_mode = st.radio(
        "Choix de la ligue",
        options=["Coupe du Mao (à mao)", "Autre ligue"],
        index=0,
        label_visibility="collapsed",
    )

    if league_mode == "Autre ligue":
        st.caption("Colle ci-dessous une liste de pseudos (un par ligne) ou le JSON complet renvoyé par `api.mpp.football/challenge-standings/users-standings`.")
        custom_input = st.text_area(
            "Pseudos ou JSON MPP",
            height=200,
            placeholder="pseudo1\npseudo2\n...",
            label_visibility="collapsed",
        )
    else:
        custom_input = ""

# ─── Résolution de la ligue à utiliser ────────────────────────────────────────
if league_mode == "Coupe du Mao (à mao)":
    usernames = [row[0] for row in DEFAULT_LEAGUE]
    mpp_data = {row[0]: {"firstname": row[1], "mpp_rank": row[2], "mpp_points": row[3]} for row in DEFAULT_LEAGUE}
else:
    usernames, mpp_data = parse_input(custom_input)

# ─── UI principale ────────────────────────────────────────────────────────────
col_info, col_action = st.columns([3, 1])
with col_info:
    if usernames:
        st.markdown(f"**{len(usernames)}** joueur{'s' if len(usernames) > 1 else ''} · **{bookmaker}** · **{stake}€** / pari")
    else:
        st.warning("Aucun pseudo à traiter. Colle une liste dans la sidebar.")

with col_action:
    run = st.button("🎲 Calculer", use_container_width=True, type="primary", disabled=not usernames)

if run:
    progress = st.progress(0.0, text="Récupération des données...")
    results = []
    failed = []

    for i, u in enumerate(usernames):
        progress.progress((i + 1) / len(usernames), text=f"[{i+1}/{len(usernames)}] {u}")
        data = fetch_one(u, bookmaker, stake)
        if data is None:
            failed.append(u)
        else:
            info = mpp_data.get(u, {})
            results.append({
                "pseudo": u,
                "prenom": info.get("firstname", ""),
                "mpp_rank": info.get("mpp_rank"),
                "mpp_points": info.get("mpp_points"),
                "profit": data["profit"],
                "roi": data["roi"],
                "wins": data["wins"],
                "bets": data["bets"],
                "win_rate": data["winRate"],
                "avg_odd": data["averageOdd"],
                "total_stake": data["totalStake"],
                "best_streak": data.get("bestWinStreak"),
            })
        time.sleep(DELAY_SEC)

    progress.empty()

    if failed:
        st.error(f"❌ {len(failed)} pseudo{'s introuvables' if len(failed)>1 else ' introuvable'} : {', '.join(failed)}")

    if not results:
        st.stop()

    # Trier par profit
    results.sort(key=lambda r: r["profit"], reverse=True)
    for i, r in enumerate(results, start=1):
        r["money_rank"] = i
        if r["mpp_rank"]:
            r["delta"] = r["mpp_rank"] - i

    df = pd.DataFrame(results)

    # ─── Stats ligue ──────────────────────────────────────────────────────
    st.divider()
    total_profit = df["profit"].sum()
    avg_roi = df["roi"].mean()
    positives = (df["profit"] > 0).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Joueurs", len(df))
    c2.metric("Cumul ligue", f"{'+' if total_profit >= 0 else ''}{total_profit:.2f}€",
              delta=f"{total_profit / (stake * df['bets'].sum()) * 100:.1f}% ROI ligue" if df['bets'].sum() > 0 else None)
    c3.metric("ROI moyen", f"{avg_roi:+.1f}%")
    c4.metric("Rentables", f"{positives} / {len(df)}")

    # ─── Podium ───────────────────────────────────────────────────────────
    st.subheader("🏆 Podium")
    p1, p2, p3 = st.columns(3)
    for col, (_, row), medal in zip((p1, p2, p3), df.head(3).iterrows(), ["🥇", "🥈", "🥉"]):
        with col:
            name = row["pseudo"] + (f"  ·  {row['prenom']}" if row["prenom"] else "")
            col.metric(
                label=f"{medal}  {name}",
                value=f"{'+' if row['profit']>=0 else ''}{row['profit']:.2f}€",
                delta=f"ROI {row['roi']:+.1f}% · {row['wins']}/{row['bets']}",
                delta_color="off",
            )

    # ─── Tableau complet ──────────────────────────────────────────────────
    st.subheader("📊 Classement complet")

    display_df = df.copy()
    display_df["#"] = display_df["money_rank"]
    display_df["Joueur"] = display_df.apply(
        lambda r: f"{r['pseudo']}" + (f" · {r['prenom']}" if r['prenom'] else ""), axis=1)
    display_df["Profit (€)"] = display_df["profit"].apply(lambda x: f"{'+' if x>=0 else ''}{x:.2f}")
    display_df["ROI (%)"] = display_df["roi"].apply(lambda x: f"{x:+.1f}")
    display_df["Bilan"] = display_df.apply(lambda r: f"{r['wins']}/{r['bets']}", axis=1)
    display_df["Taux (%)"] = display_df["win_rate"].apply(lambda x: f"{x:.0f}")
    display_df["Cote moy."] = display_df["avg_odd"].apply(lambda x: f"{x:.2f}")

    if "delta" in display_df.columns and display_df["mpp_rank"].notna().any():
        display_df["Rang MPP"] = display_df["mpp_rank"].apply(lambda x: f"#{int(x)}" if pd.notna(x) else "—")
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

    # ─── Export CSV ───────────────────────────────────────────────────────
    csv_buf = io.StringIO()
    export_df = df[["money_rank", "pseudo", "prenom", "profit", "roi", "wins", "bets",
                    "win_rate", "avg_odd", "total_stake", "mpp_rank", "mpp_points"]].copy()
    if "delta" in df.columns:
        export_df["delta"] = df["delta"]
    export_df.to_csv(csv_buf, index=False)

    st.download_button(
        "📥 Télécharger le CSV",
        data=csv_buf.getvalue(),
        file_name=f"classement-{bookmaker}-{stake}eur.csv",
        mime="text/csv",
    )

    # ─── Détail biggest wins ──────────────────────────────────────────────
    with st.expander("💡 Insights"):
        best = df.iloc[0]
        worst = df.iloc[-1]
        st.markdown(f"**Meilleur pari cumulé** : `{best['pseudo']}` avec **{best['profit']:+.2f}€** ({best['bets']} paris, cote moy. {best['avg_odd']:.2f})")
        st.markdown(f"**Pire résultat** : `{worst['pseudo']}` avec **{worst['profit']:+.2f}€**")

        if "delta" in df.columns and df["delta"].notna().any():
            climber = df.loc[df["delta"].idxmax()]
            faller = df.loc[df["delta"].idxmin()]
            if pd.notna(climber["delta"]) and climber["delta"] > 0:
                st.markdown(f"**Meilleur choix de cotes** : `{climber['pseudo']}` gagne **{int(climber['delta'])} places** vs son rang MPP (parie sur des paris mieux payés)")
            if pd.notna(faller["delta"]) and faller["delta"] < 0:
                st.markdown(f"**Cocheur de favoris** : `{faller['pseudo']}` perd **{int(abs(faller['delta']))} places** vs son rang MPP (bons pronos mais cotes pourries)")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Fait avec ❤️ et Streamlit. Basé sur l'app [Mes Profits Pronos](https://mes-profits-pronos.vercel.app) d'Arthur Labbaye. "
    "Cotes historiques via OddsPortal (Betclic, Unibet, Winamax)."
)
