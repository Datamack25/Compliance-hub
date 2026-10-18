"""Composants d'interface : CSS, en-têtes, cartes, composants HTML/JS."""
from __future__ import annotations

import html
import json

import streamlit as st
import streamlit.components.v1 as components

from core.paths import ASSETS, APP_NAME

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", color="#15233B", size=12),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=40, b=10),
    colorway=["#0E7490", "#B8891B", "#5925DC", "#067647", "#B42318", "#475467"],
)


GEO_CONFIG = {"topojsonURL": "app/static/", "displaylogo": False}  # fond de carte servi localement (static/world_110m.json)


def geo_chart(fig):
    fig.update_geos(lataxis_range=[-58, 85], projection_rotation=dict(lon=0))
    st.plotly_chart(fig, use_container_width=True, config=GEO_CONFIG, theme=None)


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
        f'<div class="rb-foot">{APP_NAME} · Outil d\'aide à la décision — ne se substitue pas à l\'analyse '
        "humaine ni aux textes officiels (CMF, AMLR, listes officielles de gel). Données indicatives à vérifier.</div>",
        unsafe_allow_html=True,
    )
