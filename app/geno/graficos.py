"""Gráficos do Geno em SVG, desenhados à mão nas cores e fontes do site (dono: Micael).

Sem biblioteca de gráficos: nada de barra de ferramentas, zoom ou legenda padrão. Cada função devolve
um SVG que escala com a largura (viewBox) e já traz os valores escritos, para ler sem passar o mouse.
Uso: st.markdown(grafico, unsafe_allow_html=True). Textos de fora passam por html.escape.
"""
from html import escape

from .tema import CORES

_TEXTO = CORES["creme"]
_APAGADO = "rgba(250,243,231,.62)"
_LINHA = "rgba(250,243,231,.16)"
_NEUTRO = "rgba(250,243,231,.22)"


def _num(n: float, casas: int = 0) -> str:
    """1234.5 -> '1.234,5' (milhar com ponto, decimal com vírgula)."""
    t = f"{n:,.{casas}f}"
    return t.replace(",", "§").replace(".", ",").replace("§", ".")


def _svg(largura: int, altura: int, rotulo: str, corpo: str) -> str:
    return (f'<svg class="geno-grafico" viewBox="0 0 {largura} {altura}" role="img" aria-label="{escape(rotulo)}" '
            f'xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;'
            f'font-family:Manrope,sans-serif">{corpo}</svg>')


def legenda(itens: list[tuple[str, str]]) -> str:
    """Legenda simples em HTML: [(cor, rótulo), ...]."""
    return '<div class="geno-legenda">' + "".join(
        f'<span><i style="background:{cor}"></i>{escape(r)}</span>' for cor, r in itens) + "</div>"


def barras_anuais(anos: list[int], aberturas: list[int], baixas: list[int]) -> str:
    """Pares de barras arredondadas (aberturas em menta, baixas em coral) com o valor em cima de cada uma."""
    L, A, base, topo = 640, 230, 190, 34
    maximo = max(aberturas + baixas + [1])
    passo = L / len(anos)
    larg = min(44.0, passo * 0.3)
    corpo = [f'<line x1="0" y1="{base}" x2="{L}" y2="{base}" stroke="{_LINHA}"/>']
    for i, (ano, ab, bx) in enumerate(zip(anos, aberturas, baixas)):
        centro = passo * i + passo / 2
        for valor, cor, x in ((ab, CORES["menta"], centro - larg - 2), (bx, CORES["coral"], centro + 2)):
            h = (base - topo) * valor / maximo
            corpo.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{larg:.1f}" height="{h:.1f}" rx="7" fill="{cor}"/>'
                         f'<text x="{x + larg / 2:.1f}" y="{base - h - 8:.1f}" text-anchor="middle" font-size="13" '
                         f'font-weight="700" fill="{cor}">{_num(valor)}</text>')
        corpo.append(f'<text x="{centro:.1f}" y="{base + 22}" text-anchor="middle" font-size="13" fill="{_APAGADO}">{ano}</text>')
    return _svg(L, A, "Aberturas e baixas por ano", "".join(corpo)) + legenda(
        [(CORES["menta"], "Aberturas"), (CORES["coral"], "Baixas")])


def barras_horizontais(itens: list[dict], formato=lambda v: _num(v), rotulo: str = "Comparação",
                       cor_destaque: str = CORES["coral"], cor_neutra: str = _NEUTRO,
                       largura: int = 640, x_barras: int = 230) -> str:
    """Uma barra por item ({nome, valor, destaque}); o destaque vai em cor e negrito.

    Em meia coluna, use largura menor (ex.: 380) para o texto não encolher junto com o gráfico.
    """
    linha, L = 40, largura
    A = linha * len(itens) + 6
    maximo = max([i["valor"] for i in itens] + [1e-9])
    x0, largura_max = x_barras, L - x_barras - 70
    corpo = []
    for k, item in enumerate(itens):
        y = k * linha + 6
        destaque = item.get("destaque")
        cor = cor_destaque if destaque else cor_neutra
        peso = 800 if destaque else 600
        w = max(6.0, largura_max * item["valor"] / maximo)
        corpo.append(
            f'<text x="0" y="{y + 18}" font-size="15" font-weight="{peso}" fill="{_TEXTO}">{escape(item["nome"])}</text>'
            f'<rect x="{x0}" y="{y + 3}" width="{w:.1f}" height="22" rx="7" fill="{cor}"/>'
            f'<text x="{x0 + w + 10:.1f}" y="{y + 19}" font-size="15" font-weight="{peso}" '
            f'fill="{cor_destaque if destaque else _TEXTO}">{escape(formato(item["valor"]))}</text>')
    return _svg(L, A, rotulo, "".join(corpo))


def linha_sobrevivencia(pontos: list[dict]) -> str:
    """% ainda ativos por ano de abertura ({ano, pct_ativos}); marca o primeiro, o do meio e o último."""
    L, A, base, topo, margem = 640, 200, 160, 30, 24
    n = len(pontos)
    if n < 2:
        return ""
    x = lambda i: margem + (L - 2 * margem) * i / (n - 1)  # noqa: E731
    y = lambda p: base - (base - topo) * p / 100  # noqa: E731
    coords = " ".join(f"{x(i):.1f},{y(p['pct_ativos']):.1f}" for i, p in enumerate(pontos))
    corpo = [f'<line x1="{margem}" y1="{base}" x2="{L - margem}" y2="{base}" stroke="{_LINHA}"/>',
             f'<polyline fill="none" stroke="{CORES["menta"]}" stroke-width="3" stroke-linejoin="round" '
             f'stroke-linecap="round" points="{coords}"/>']
    for i in sorted({0, n // 2, n - 1}):
        p = pontos[i]
        ancora = "start" if i == 0 else "end" if i == n - 1 else "middle"
        corpo.append(f'<circle cx="{x(i):.1f}" cy="{y(p["pct_ativos"]):.1f}" r="5" fill="{CORES["menta"]}"/>'
                     f'<text x="{x(i):.1f}" y="{y(p["pct_ativos"]) - 12:.1f}" text-anchor="{ancora}" font-size="14" '
                     f'font-weight="700" fill="{_TEXTO}">{_num(p["pct_ativos"])} de 100</text>'
                     f'<text x="{x(i):.1f}" y="{base + 22}" text-anchor="{ancora}" font-size="13" '
                     f'fill="{_APAGADO}">abertas em {p["ano"]}</text>')
    return _svg(L, A, "Percentual de ativos por ano de abertura", "".join(corpo))


def rosca(parte: int, total: int, titulo: str, linhas: list[str]) -> str:
    """Rosca com a porcentagem no meio e duas ou três linhas de texto ao lado."""
    pct = 100 * parte / total if total else 0
    r, c = 52, 2 * 3.14159 * 52
    corpo = [f'<circle cx="70" cy="75" r="{r}" fill="none" stroke="{_LINHA}" stroke-width="20"/>',
             f'<circle cx="70" cy="75" r="{r}" fill="none" stroke="{CORES["coral"]}" stroke-width="20" '
             f'stroke-dasharray="{c * pct / 100:.1f} {c:.1f}" transform="rotate(-90 70 75)" stroke-linecap="round"/>',
             f'<text x="70" y="84" text-anchor="middle" font-family="Fraunces,Georgia,serif" font-size="26" '
             f'font-weight="700" fill="{_TEXTO}">{_num(pct)}%</text>']
    for k, linha in enumerate(linhas):
        corpo.append(f'<text x="150" y="{58 + 24 * k}" font-size="14" font-weight="{700 if k % 2 == 0 else 500}" '
                     f'fill="{_TEXTO if k % 2 == 0 else _APAGADO}">{escape(linha)}</text>')
    return _svg(380, 150, titulo, "".join(corpo))
