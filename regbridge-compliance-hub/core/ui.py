"""Composants d'interface : CSS, en-têtes, cartes, composants HTML/JS."""
from __future__ import annotations

import html
import json

import streamlit as st
import streamlit.components.v1 as components

import os

import pandas as pd

from core.paths import APP_AUTHOR, APP_NAME, APP_RELEASE, APP_VERSION, ASSETS

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", color="#15233B", size=12),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=40, b=10),
    colorway=["#0E7490", "#B8891B", "#5925DC", "#067647", "#B42318", "#475467"],
)


LIGHT_THEME = {"theme.base": "light", "theme.primaryColor": "#0E7490", "theme.backgroundColor": "#F4F6FA",
               "theme.secondaryBackgroundColor": "#FFFFFF", "theme.textColor": "#15233B"}


def force_light_theme():
    """Impose le thème clair même si .streamlit/config.toml n'est pas déployé ou si le navigateur est en mode sombre."""
    from streamlit import config as _cfg
    for k, v in LIGHT_THEME.items():
        try:
            _cfg.set_option(k, v)
        except Exception:
            pass


# Fond de carte : CDN Plotly par défaut ; copie locale (static/) si RB_LOCAL_TOPOJSON=1 et enableStaticServing actif
GEO_CONFIG = {"displaylogo": False, "responsive": True}
if os.environ.get("RB_LOCAL_TOPOJSON") == "1":
    GEO_CONFIG["topojsonURL"] = "app/static/"
CHART_CONFIG = {"displaylogo": False, "responsive": True, "displayModeBar": False}


def _light(fig):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
                      font=dict(family="Inter, sans-serif", color="#15233B"),
                      legend=dict(font=dict(color="#15233B"), bgcolor="rgba(255,255,255,0.85)"),
                      hoverlabel=dict(bgcolor="#0B1F3A", font_color="#FFFFFF"))
    fig.update_xaxes(color="#344054", gridcolor="#E3E8F0", linecolor="#D0D7E2", title_font_color="#344054")
    fig.update_yaxes(color="#344054", gridcolor="#E3E8F0", linecolor="#D0D7E2", title_font_color="#344054")
    if fig.layout.title and fig.layout.title.text:
        fig.update_layout(title_font=dict(color="#0B1F3A", size=14))
    return fig


def chart(fig, use_container_width=True, **_):
    """Graphique Plotly lisible quel que soit le thème (fond blanc, textes sombres)."""
    st.plotly_chart(_light(fig), use_container_width=True, config=CHART_CONFIG, theme=None)


def geo_chart(fig):
    fig.update_geos(lataxis_range=[-58, 85], projection_rotation=dict(lon=0), bgcolor="rgba(0,0,0,0)",
                    showland=True, landcolor="#EEF2F6", showcountries=True, countrycolor="#FFFFFF", showframe=False, showcoastlines=False)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, sans-serif", color="#15233B"),
                      legend=dict(font=dict(color="#15233B")), template="plotly_white")
    st.plotly_chart(fig, use_container_width=True, config=GEO_CONFIG, theme=None)


def _cfg_label(cfg, col):
    if isinstance(cfg, str):
        return cfg
    if isinstance(cfg, dict) and cfg.get("label"):
        return cfg["label"]
    return str(col).replace("_", " ").capitalize()


def table(df: pd.DataFrame, height: int | None = None, column_config: dict | None = None, max_rows: int = 500, **_):
    """Tableau HTML élégant (en-tête bleu nuit, lignes alternées, barres de progression, pastilles de risque)."""
    import numpy as np
    column_config = column_config or {}
    if df is None or len(df) == 0:
        st.markdown('<div class="rb-empty">Aucune donnée à afficher.</div>', unsafe_allow_html=True)
        return
    d = df.head(max_rows).reset_index(drop=True)
    pills = {"Très élevé": "red", "Critique": "red", "Élevé": "red", "Haute": "amber", "Modéré": "amber", "Moyenne": "amber",
             "Faible": "green", "Standard": "teal", "Conforme": "green", "Non conforme": "red", "Partiel": "amber", "OUI": "red",
             "Succès": "green", "Échec": "red", "noire": "red", "grise": "amber", "En vigueur": "teal", "À venir": "amber",
             "champion": "green", "P1": "red", "P2": "amber", "P3": "teal", "Actif": "green"}
    head = "".join(f"<th>{html.escape(_cfg_label(column_config.get(c), c))}</th>" for c in d.columns)
    rows = []
    for _, r in d.iterrows():
        cells = []
        for c in d.columns:
            v, cfg = r[c], column_config.get(c)
            tc = (cfg or {}).get("type_config", {}) if isinstance(cfg, dict) else {}
            if tc.get("type") == "progress" and pd.notna(v):
                lo, hi = tc.get("min_value", 0) or 0, tc.get("max_value", 100) or 100
                pct = max(0, min(100, 100 * (float(v) - lo) / ((hi - lo) or 1)))
                col = "#B42318" if pct < 42 else "#EA580C" if pct < 62 else "#CA8A04" if pct < 80 else "#067647"
                if hi <= 1:
                    col = "#0E7490"
                txt = f"{float(v):.2f}" if hi <= 1 else f"{float(v):.1f}"
                cells.append(f'<td><div class="rb-bar"><span style="width:{pct:.0f}%;background:{col}"></span></div><small>{txt}</small></td>')
                continue
            if isinstance(v, float):
                if np.isnan(v):
                    s = "—"
                elif abs(v) >= 1000:
                    s = f"{v:,.0f}".replace(",", " ")
                else:
                    s = f"{v:.3f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(v)}"
            else:
                s = "—" if v is None or (isinstance(v, str) and v == "") else str(v)
            if isinstance(v, str) and v.startswith("http"):
                cells.append(f'<td><a href="{html.escape(v)}" target="_blank">Ouvrir ↗</a></td>')
            elif s in pills:
                cells.append(f'<td><span class="rb-pill {pills[s]}">{html.escape(s)}</span></td>')
            else:
                cls = ' class="nw"' if len(s) <= 14 else ""
                cells.append(f"<td{cls}>{html.escape(s)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    style = f' style="max-height:{height}px"' if height else ""
    more = f'<div class="rb-tmore">{len(df) - max_rows} ligne(s) supplémentaire(s) — utilisez l\'export Excel.</div>' if len(df) > max_rows else ""
    st.markdown(f'<div class="rb-table"{style}><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>{more}',
                unsafe_allow_html=True)


def inject_css():
    css = (ASSETS / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def hero(title: str, subtitle: str, kicker: str = APP_NAME, badge: str | None = None):
    b = f'<div class="rb-badge">{html.escape(badge)}</div>' if badge else ""
    st.markdown(
        f'<div class="rb-hero">{b}<div class="rb-kicker">{html.escape(kicker)}</div>'
        f"<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(f'<div class="rb-section"><div class="bar"></div><h3>{html.escape(title)}</h3></div>', unsafe_allow_html=True)


def kpi(label: str, value, sub: str = "", tone: str = ""):
    st.markdown(
        f'<div class="rb-kpi {tone}"><div class="lbl">{html.escape(label)}</div>'
        f'<div class="val{" txt" if len(str(value)) > 9 else ""}">{html.escape(str(value))}</div><div class="sub">{html.escape(sub)}</div></div>',
        unsafe_allow_html=True,
    )


def card(title: str, body: str):
    st.markdown(f'<div class="rb-card"><h4>{html.escape(title)}</h4><p>{body}</p></div>', unsafe_allow_html=True)


def agent_card(icon: str, name: str, mission: str, status_html: str = ""):
    st.markdown(
        f'<div class="rb-agent"><div class="ic">{icon}</div><div><h5>{html.escape(name)}</h5>'
        f"<p>{html.escape(mission)}</p>{status_html}</div></div>",
        unsafe_allow_html=True,
    )


def js_ticker(news: list[dict], height: int = 46):
    """Bandeau défilant (HTML + CSS + JavaScript)."""
    js = (ASSETS / "components.js").read_text(encoding="utf-8")
    data = json.dumps({"news": news[:30]}, ensure_ascii=False)
    components.html(
        f"""
<style>
 body{{margin:0;font-family:Inter,system-ui,sans-serif}}
 .wrap{{display:flex;align-items:center;background:#0B1F3A;border-radius:12px;overflow:hidden;height:{height - 6}px}}
 .lab{{background:#0E7490;color:#fff;font-weight:800;font-size:12px;letter-spacing:.12em;padding:0 14px;height:100%;display:flex;align-items:center;white-space:nowrap}}
 .viewport{{overflow:hidden;flex:1;position:relative}}
 #rb-ticker-track{{display:inline-flex;gap:38px;white-space:nowrap;animation:scroll linear infinite;padding-left:20px}}
 #rb-ticker-track:hover{{animation-play-state:paused}}
 #rb-ticker-track a{{color:#E6EDF7;text-decoration:none;font-size:13px;display:inline-flex;align-items:center;gap:8px}}
 #rb-ticker-track a:hover{{color:#7DD3E8}}
 #rb-ticker-track em{{color:#8FA3BF;font-style:normal;font-size:11px}}
 .dot{{width:6px;height:6px;border-radius:50%;background:#F59E0B;display:inline-block}}
 @keyframes scroll{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
</style>
<div class="wrap"><div class="lab">● EN DIRECT</div><div class="viewport"><div id="rb-ticker-track"></div></div></div>
<script>window.RB_DATA={data};</script><script>{js}</script>
""",
        height=height,
    )


def js_counters(items: list[tuple[str, float, int, str]], deadline: str | None = None, height: int = 118):
    """Rangée de compteurs animés + compte à rebours (JavaScript)."""
    js = (ASSETS / "components.js").read_text(encoding="utf-8")
    cells = "".join(
        f'<div class="c"><div class="l">{html.escape(l)}</div><div class="v" data-count="{v}" data-dec="{d}">0</div>'
        f'<div class="s">{html.escape(s)}</div></div>'
        for l, v, d, s in items
    )
    if deadline:
        cells += (f'<div class="c dl"><div class="l">AMLR applicable</div><div class="v sm" data-deadline="{deadline}">…</div>'
                  f'<div class="s">10 juillet 2027 · Règl. (UE) 2024/1624</div></div>')
    components.html(
        f"""
<style>
 body{{margin:0;font-family:Inter,system-ui,sans-serif}}
 .row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
 .c{{background:#fff;border:1px solid #E3E8F0;border-radius:14px;padding:12px 14px;box-shadow:0 1px 2px rgba(16,24,40,.05),0 4px 16px rgba(16,24,40,.06)}}
 .l{{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:#5B6B82;font-weight:700}}
 .v{{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;color:#0B1F3A;margin-top:2px}}
 .v.sm{{font-size:19px;color:#B54708;margin-top:8px}}
 .s{{font-size:11.5px;color:#5B6B82}}
 .dl{{background:linear-gradient(135deg,#FFFAEB,#fff)}}
</style>
<div class="row">{cells}</div><script>{js}</script>
""",
        height=height,
    )


def locked(plan_needed: str):
    st.markdown(
        f'<div class="rb-lock"><b>🔒 Fonctionnalité réservée à l\'offre {html.escape(plan_needed)}.</b><br>'
        "Rendez-vous dans <b>Mon compte → Abonnement</b> pour activer votre accès (paiement en ligne ou code d'activation).</div>",
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        f'<div class="rb-foot"><b>{APP_NAME}</b> · version {APP_VERSION} ({APP_RELEASE}) · Conçu et développé par <b>{APP_AUTHOR}</b><br>'
        "Outil d'aide à la décision — ne se substitue pas à l'analyse humaine ni aux textes officiels "
        "(CMF, AMLR, listes officielles de gel). Données indicatives à vérifier.</div>",
        unsafe_allow_html=True,
    )
