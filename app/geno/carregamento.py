"""Animação de carregamento do Geno: a constelação de empresas (dono: Micael).

Os pontos do fundo (um por empresa) se acendem, viajam e formam um aglomerado que gira no centro,
com linhas entre vizinhos e alguns pontos coral (o que ninguém atende). Fica girando até o
carregamento acabar. Quem pede menos movimento no sistema vê o aglomerado já formado, parado.

O desenho roda num iframe que o app cria uma vez por carregamento; o texto da etapa fica fora dele,
num fragment, para trocar de frase sem reiniciar a animação.
"""
import streamlit as st

ALTURA = 340

_HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; height: 100%; background: transparent; overflow: hidden; }
canvas { display: block; width: 100%; height: 100%; }
</style></head><body><canvas id="c" role="img" aria-label="Animação de carregamento"></canvas><script>
const cv = document.getElementById('c'), x = cv.getContext('2d');
const reduz = matchMedia('(prefers-reduced-motion: reduce)').matches;
let W, H, pts = [], sel = [];
function montar() {
  const d = devicePixelRatio || 1, r = cv.getBoundingClientRect();
  W = r.width; H = r.height; cv.width = W * d; cv.height = H * d; x.setTransform(d, 0, 0, d, 0, 0);
  pts = [];
  const raio = Math.min(W, H) * 0.42;
  for (let gx = 9; gx < W; gx += 18) for (let gy = 9; gy < H; gy += 18) {
    const p = { hx: gx + (Math.random() - .5) * 4, hy: gy + (Math.random() - .5) * 4 };
    const dc = Math.hypot(p.hx - W / 2, p.hy - H / 2);
    p.sel = Math.random() < (dc < W * .45 ? .2 : .08);
    p.cor = Math.random() < .12;
    p.a = Math.random() * Math.PI * 2;
    p.r = raio * (0.18 + Math.random() * 0.82);
    p.v = (p.r < raio * .5 ? 1.5 : 1) * (Math.random() < .5 ? 1 : 1.15);
    p.atraso = Math.random() * .8;
    pts.push(p);
  }
  sel = pts.filter(p => p.sel);
}
montar(); addEventListener('resize', montar);
const t0 = performance.now();
function quadro(agora) {
  const t = reduz ? 99 : (agora - t0) / 1000;
  x.clearRect(0, 0, W, H);
  const cx = W / 2, cy = H / 2;
  for (const p of pts) {
    if (!p.sel) {
      x.fillStyle = 'rgba(250,243,231,' + (0.08 + 0.05 * Math.sin(agora / 700 + p.hx)) + ')';
      x.beginPath(); x.arc(p.hx, p.hy, 1.2, 0, 7); x.fill(); continue;
    }
    const k = Math.max(0, Math.min(1, (t - p.atraso) / 2.2));
    const e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    const ang = p.a + t * 0.35 * p.v;
    const tx = cx + Math.cos(ang) * p.r * 1.45, ty = cy + Math.sin(ang) * p.r * 0.78;
    p.x = p.hx + (tx - p.hx) * e; p.y = p.hy + (ty - p.hy) * e; p.e = e;
  }
  x.lineWidth = .7;
  for (let i = 0; i < sel.length; i++) for (let j = i + 1; j < sel.length; j++) {
    const a = sel[i], b = sel[j];
    if (a.e < .85 || b.e < .85) continue;
    const dd = Math.hypot(a.x - b.x, a.y - b.y);
    if (dd < 40) { x.strokeStyle = 'rgba(143,211,189,' + (0.32 * (1 - dd / 40)) + ')';
      x.beginPath(); x.moveTo(a.x, a.y); x.lineTo(b.x, b.y); x.stroke(); }
  }
  for (const p of sel) {
    const c = p.cor ? '232,97,60' : '143,211,189';
    x.fillStyle = 'rgba(' + c + ',' + (0.35 + 0.65 * p.e) + ')';
    x.beginPath(); x.arc(p.x, p.y, 1.4 + 1.8 * p.e, 0, 7); x.fill();
    if (p.e > .9) { x.fillStyle = 'rgba(' + c + ',.12)'; x.beginPath(); x.arc(p.x, p.y, 7, 0, 7); x.fill(); }
  }
  if (!reduz) requestAnimationFrame(quadro);
}
requestAnimationFrame(quadro);
</script></body></html>
"""


def animacao() -> None:
    """Desenha a constelação. Chamar fora de fragments, uma vez por carregamento."""
    st.iframe(_HTML, height=ALTURA)  # HTML fixo deste módulo, nunca texto vindo de fora
