"""
Coletor de páginas — coleta responsável (seção 9 do relatório / README do módulo).

Regras (não negociáveis):
- Respeita robots.txt (e o crawl-delay quando houver).
- No máximo 1 requisição por segundo por domínio.
- User-Agent identificando o projeto (GENO_USER_AGENT no .env).
- Bloqueios (ex.: Cloudflare, 403/429/503) são REGISTRADOS, nunca contornados.
  A taxa de bloqueio é uma métrica do artigo.
- Guarda só o texto limpo, com hash, para não reprocessar.

Para cada domínio candidato coleta até 3 páginas: home, "sobre" e "preços"
(as duas últimas descobertas por links da home). Grava na tabela `pagina`.

Uso:
    python -m enriquecimento.coletor                  # usa os domínios de candidato_dominio
    python -m enriquecimento.coletor exemplo.com ...  # domínios avulsos (teste)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sys
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from . import config, io_contratos

# Limites de coleta responsável
INTERVALO_MIN_S = 1.0          # 1 req/s por domínio
TIMEOUT_S = 15.0
MAX_TEXTO = 20_000             # trunca o texto limpo guardado
SEP_TITULO = " || "            # separa título || h1 || corpo dentro de `texto`

# Palavras que identificam as páginas "sobre" e "preços" (no href ou no texto do link)
PADROES = {
    "sobre": ["sobre", "quem-somos", "quem somos", "a-escola", "institucional", "about"],
    "precos": ["preco", "preço", "planos", "valores", "mensalidade", "matricula",
               "matrícula", "investimento", "pricing", "assinatura"],
}

# Marcas de página de bloqueio (não contornar — só registrar)
MARCAS_BLOQUEIO = [
    "cf-browser-verification", "__cf_chl", "attention required",
    "checking your browser", "captcha", "access denied",
]
STATUS_BLOQUEIO = {403, 429, 503}


@dataclass
class Resultado:
    url: str
    dominio: str
    tipo: str              # 'home' | 'sobre' | 'precos'
    status_http: int | None
    bloqueado: bool
    texto: str
    hash_texto: str | None


def _texto_limpo(html: str) -> str:
    """Texto limpo no formato: '<title> || <h1> || <corpo>' (para o Método 3 usar o título)."""
    tree = HTMLParser(html)
    t = tree.css_first("title")
    titulo = t.text(strip=True) if t else ""
    h1 = tree.css_first("h1")
    h1_txt = h1.text(strip=True) if h1 else ""
    for tag in tree.css("script, style, noscript, svg, template"):
        tag.decompose()
    raiz = tree.body or tree.root
    corpo = raiz.text(separator=" ", strip=True) if raiz else ""
    corpo = " ".join(corpo.split())
    return f"{titulo}{SEP_TITULO}{h1_txt}{SEP_TITULO}{corpo}"[:MAX_TEXTO]


def titulo_de(texto: str) -> str:
    """Devolve a região de título (<title> + <h1>) guardada no começo de `texto`."""
    if not texto:
        return ""
    partes = texto.split(SEP_TITULO)
    return " ".join(partes[:2]).strip()


def _parece_bloqueio(status: int, html: str) -> bool:
    if status in STATUS_BLOQUEIO:
        return True
    return any(m in html[:4000].lower() for m in MARCAS_BLOQUEIO)


def _carregar_robots(client: httpx.Client, base: str) -> RobotFileParser:
    rp = RobotFileParser()
    try:
        r = client.get(urljoin(base, "/robots.txt"), timeout=TIMEOUT_S)
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except httpx.HTTPError:
        rp.parse([])  # sem robots acessível: trata como liberado
    return rp


def _buscar(client: httpx.Client, url: str, dominio: str, tipo: str) -> tuple[Resultado | None, str]:
    """Faz UMA requisição. Devolve (Resultado, html_cru). Resultado é None se nem respondeu."""
    try:
        r = client.get(url, timeout=TIMEOUT_S, follow_redirects=True)
    except httpx.HTTPError as e:
        print(f"  ! {tipo}: sem resposta ({type(e).__name__}) {url}")
        return None, ""
    html = r.text or ""
    if _parece_bloqueio(r.status_code, html):
        print(f"  x {tipo}: BLOQUEADO (status {r.status_code}) {url}")
        return Resultado(url, dominio, tipo, r.status_code, True, "", None), html
    texto = _texto_limpo(html)
    h = hashlib.sha256(texto.encode("utf-8")).hexdigest() if texto else None
    print(f"  . {tipo}: ok (status {r.status_code}, {len(texto)} chars) {url}")
    return Resultado(url, dominio, tipo, r.status_code, False, texto, h), html


def _descobrir_subpaginas(html: str, base: str) -> dict[str, str]:
    """A partir do HTML da home, acha a 1ª URL de 'sobre' e de 'preços' no mesmo domínio."""
    tree = HTMLParser(html)
    dom_base = urlparse(base).netloc
    achados: dict[str, str] = {}
    for a in tree.css("a"):
        href = a.attributes.get("href") or ""
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        alvo = urljoin(base, href)
        if urlparse(alvo).netloc != dom_base:
            continue
        chave = (href + " " + (a.text() or "")).lower()
        for tipo, palavras in PADROES.items():
            if tipo not in achados and any(p in chave for p in palavras):
                achados[tipo] = alvo
        if len(achados) == 2:
            break
    return achados


class _Ritmo:
    """Garante no mínimo INTERVALO_MIN_S entre requisições do mesmo domínio."""
    def __init__(self) -> None:
        self._ultimo = 0.0

    def esperar(self) -> None:
        falta = INTERVALO_MIN_S - (time.monotonic() - self._ultimo)
        if falta > 0:
            time.sleep(falta)
        self._ultimo = time.monotonic()


def coletar_dominio(client: httpx.Client, dominio: str) -> list[Resultado]:
    """Coleta home + sobre + preços de um domínio, respeitando robots e 1 req/s."""
    base = f"https://{dominio}/"
    print(f"[dominio] {dominio}")
    rp = _carregar_robots(client, base)
    ua = config.USER_AGENT
    ritmo = _Ritmo()
    resultados: list[Resultado] = []

    # 1) home
    if not rp.can_fetch(ua, base):
        print("  - home barrada pelo robots.txt; pulando domínio")
        return resultados
    ritmo.esperar()
    home, home_html = _buscar(client, base, dominio, "home")
    if home is None:
        return resultados
    resultados.append(home)
    if home.bloqueado or not home_html:
        return resultados  # sem HTML aproveitável, não dá para achar subpáginas

    # 2) sobre e preços descobertos na home
    for tipo, url in _descobrir_subpaginas(home_html, base).items():
        if not rp.can_fetch(ua, url):
            print(f"  - {tipo} barrado pelo robots.txt; pulando")
            continue
        ritmo.esperar()
        res, _ = _buscar(client, url, dominio, tipo)
        if res is not None:
            resultados.append(res)
    return resultados


def gravar(con, resultados: list[Resultado]) -> int:
    if not resultados:
        return 0
    agora = dt.datetime.now()
    linhas = [
        (r.url, r.dominio, r.tipo, r.status_http, r.bloqueado, r.texto, r.hash_texto, agora)
        for r in resultados
    ]
    con.executemany(
        """
        INSERT OR REPLACE INTO pagina
            (url, dominio, tipo, status_http, bloqueado, texto, hash_texto, coletado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        linhas,
    )
    return len(linhas)


def _dominios_de_candidatos(con) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT dominio FROM candidato_dominio ORDER BY dominio"
    ).fetchall()
    return [d for (d,) in rows]


def main(argv: list[str]) -> None:
    con = io_contratos.conectar()
    io_contratos.criar_tabelas(con)
    try:
        dominios = argv or _dominios_de_candidatos(con)
        if not dominios:
            print("[coletor] nenhum domínio em candidato_dominio. "
                  "Rode um método (ex.: metodo1_email) ou passe domínios na linha de comando.")
            return
        print(f"[coletor] {len(dominios)} domínio(s) a coletar")

        headers = {"User-Agent": config.USER_AGENT}
        total = 0
        with httpx.Client(headers=headers) as client:
            for dom in dominios:
                total += gravar(con, coletar_dominio(client, dom))

        paginas = con.execute("SELECT count(*) FROM pagina").fetchone()[0]
        bloqueadas = con.execute("SELECT count(*) FROM pagina WHERE bloqueado").fetchone()[0]
        print(f"[coletor] {total} página(s) gravada(s) nesta rodada. "
              f"Total na tabela: {paginas} (bloqueadas: {bloqueadas}).")
    finally:
        con.close()


if __name__ == "__main__":
    main(sys.argv[1:])
