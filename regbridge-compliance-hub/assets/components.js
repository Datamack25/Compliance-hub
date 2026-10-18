/* RegBridge Compliance Hub — composants JavaScript embarqués (st.components.v1.html)
   - Bandeau défilant d'actualités (ticker)
   - Compteurs animés
   - Compte à rebours réglementaire (AMLR 10/07/2027)
   Les données sont injectées par Python via window.RB_DATA.
*/
(function () {
  const D = window.RB_DATA || {};

  // ---------- Ticker ----------
  const tk = document.getElementById("rb-ticker-track");
  if (tk && Array.isArray(D.news)) {
    const html = D.news.map(n =>
      `<a href="${n.link}" target="_blank" rel="noopener"><span class="dot"></span>${n.title}<em>${n.source || ""}</em></a>`
    ).join("");
    tk.innerHTML = html + html; // boucle continue
    const speed = Math.max(40, D.news.length * 9);
    tk.style.animationDuration = speed + "s";
  }

  // ---------- Compteurs ----------
  document.querySelectorAll("[data-count]").forEach(el => {
    const target = parseFloat(el.dataset.count);
    const dec = parseInt(el.dataset.dec || "0", 10);
    const t0 = performance.now(), dur = 1100;
    function step(t) {
      const p = Math.min(1, (t - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * e).toFixed(dec).replace(".", ",");
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

  // ---------- Compte à rebours ----------
  document.querySelectorAll("[data-deadline]").forEach(el => {
    const end = new Date(el.dataset.deadline + "T00:00:00");
    function tick() {
      const ms = end - new Date();
      if (ms <= 0) { el.textContent = "En vigueur"; return; }
      const d = Math.floor(ms / 864e5), h = Math.floor(ms % 864e5 / 36e5), m = Math.floor(ms % 36e5 / 6e4);
      el.textContent = `J-${d} · ${h}h ${m}min`;
    }
    tick(); setInterval(tick, 30000);
  });
})();
