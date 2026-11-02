"""
Métricas do módulo de enriquecimento (resultado do artigo).

Mede sobre o que já está no geno.duckdb:
- Cobertura: quantos CNPJs ganharam ao menos um domínio candidato (total e por método).
- Taxa de bloqueio: páginas/domínios bloqueados (ex.: Cloudflare) — não contornados.
- Exposição de CNPJ: % dos domínios coletados cujo texto traz um CNPJ válido
  (potencial do Método 2, independente de ter CNPJ conhecido para casar).
- Acurácia do Método 3: quando há uma verdade de referência (o candidatos com o
  domínio correto, como no proxy), mede precisão do casamento nome × título.

Gera também o METRICAS.md.

Uso:
    python -m enriquecimento.metricas [caminho_candidatos.csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import cnpj as cnpj_util
from . import config, io_contratos
from .metodo1_email import _normalizar_dominio


def _pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "—"


def coletar_metricas(con, candidatos=None) -> dict:
    m: dict = {}

    # --- cobertura ---
    total_cnpjs = con.execute("SELECT count(DISTINCT cnpj) FROM candidato_dominio").fetchone()[0]
    m["cnpjs_com_candidato"] = total_cnpjs
    m["por_metodo"] = dict(con.execute(
        "SELECT metodo, count(*) FROM candidato_dominio GROUP BY metodo ORDER BY metodo"
    ).fetchall())

    # --- páginas / bloqueio ---
    pag, bloq = con.execute(
        "SELECT count(*), count(*) FILTER (WHERE bloqueado) FROM pagina"
    ).fetchone()
    m["paginas"] = pag
    m["paginas_bloqueadas"] = bloq
    dom_total, dom_bloq, dom_vazio = con.execute(
        """
        SELECT count(*),
               count(*) FILTER (WHERE bloqueado),
               count(*) FILTER (WHERE NOT bloqueado AND (texto IS NULL OR length(texto) < 50))
        FROM (
            SELECT dominio,
                   bool_and(bloqueado) AS bloqueado,
                   max(length(texto))  AS _ml,
                   any_value(texto)    AS texto
            FROM pagina GROUP BY dominio
        )
        """
    ).fetchone()
    m["dominios"] = dom_total
    m["dominios_bloqueados"] = dom_bloq
    m["dominios_sem_texto"] = dom_vazio

    # --- exposição de CNPJ (potencial do Método 2) ---
    rows = con.execute(
        "SELECT dominio, any_value(texto) FROM pagina "
        "WHERE NOT bloqueado AND texto IS NOT NULL GROUP BY dominio"
    ).fetchall()
    com_cnpj = sum(1 for _d, t in rows if cnpj_util.extrair(t or ""))
    m["dominios_analisados"] = len(rows)
    m["dominios_com_cnpj_no_texto"] = com_cnpj

    # --- acurácia do Método 3 (precisão) contra verdade de referência ---
    if candidatos is not None:
        verdade = {}
        for _, r in candidatos.iterrows():
            dom = _normalizar_dominio(r.get("dominio_email"))
            if dom:
                verdade[str(r["cnpj"])] = dom
        propostas = con.execute(
            "SELECT cnpj, dominio FROM candidato_dominio WHERE metodo = 'nome_titulo'"
        ).fetchall()
        certos = sum(1 for c, d in propostas if verdade.get(str(c)) == d)
        m["m3_propostas"] = len(propostas)
        m["m3_corretas"] = certos

    return m


def _render_md(m: dict) -> str:
    linhas = ["# MÉTRICAS — camada de enriquecimento (Roger)", ""]
    linhas.append("Gerado por `python -m enriquecimento.metricas`. Números do `geno.duckdb` atual.")
    linhas.append("")
    linhas.append("## Cobertura")
    linhas.append(f"- CNPJs com ao menos um domínio candidato: **{m['cnpjs_com_candidato']}**")
    for metodo, n in m["por_metodo"].items():
        linhas.append(f"  - `{metodo}`: {n} hipótese(s)")
    linhas.append("")
    linhas.append("## Coleta e bloqueio")
    linhas.append(f"- Domínios visitados: **{m['dominios']}**")
    linhas.append(f"- Domínios bloqueados (ex.: Cloudflare, não contornados): "
                  f"**{m['dominios_bloqueados']}** ({_pct(m['dominios_bloqueados'], m['dominios'])})")
    linhas.append(f"- Domínios sem texto aproveitável (ex.: SPA/JS): "
                  f"**{m['dominios_sem_texto']}** ({_pct(m['dominios_sem_texto'], m['dominios'])})")
    linhas.append(f"- Páginas coletadas: {m['paginas']} (bloqueadas: {m['paginas_bloqueadas']})")
    linhas.append("")
    linhas.append("## Exposição de CNPJ (potencial do Método 2)")
    linhas.append(f"- Domínios com CNPJ válido no texto: "
                  f"**{m['dominios_com_cnpj_no_texto']}** de {m['dominios_analisados']} "
                  f"({_pct(m['dominios_com_cnpj_no_texto'], m['dominios_analisados'])})")
    if "m3_propostas" in m:
        linhas.append("")
        linhas.append("## Acurácia do Método 3 (nome × título)")
        linhas.append(f"- Precisão: **{m['m3_corretas']}/{m['m3_propostas']}** "
                      f"({_pct(m['m3_corretas'], m['m3_propostas'])}) casamentos corretos "
                      f"(verdade de referência = domínio real do proxy)")
    linhas.append("")
    linhas.append("## Ressalvas")
    linhas.append("- O **Método 1** não é avaliado aqui: no proxy o domínio de e-mail É o site, "
                  "então a medição seria circular. Sua acurácia real exige os e-mails cadastrais "
                  "do `candidatos.parquet` (Lucas).")
    linhas.append("- O **Método 2** só gera casamento quando há CNPJ cadastral conhecido para cruzar; "
                  "no proxy os CNPJs são placeholders, por isso aqui medimos a *exposição* de CNPJ nos "
                  "sites, não o casamento.")
    return "\n".join(linhas) + "\n"


def main(caminho: str | None = None) -> None:
    candidatos = None
    if caminho:
        candidatos = io_contratos.ler_candidatos(caminho)

    con = io_contratos.conectar()
    try:
        m = coletar_metricas(con, candidatos)
    finally:
        con.close()

    md = _render_md(m)
    destino = Path(config.PASTA_ENRIQUECIMENTO) / "METRICAS.md"
    destino.write_text(md, encoding="utf-8")
    print(md)
    print(f"[metricas] escrito em {destino}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
