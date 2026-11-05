"""
Método 2 — CNPJ no rodapé do site.

Evidência forte: se o CNPJ cadastral aparece numa página já coletada do domínio
candidato (tipicamente no rodapé), o domínio é da empresa. O CNPJ é extraído do
texto e tem o dígito verificador conferido antes de valer.

Lê a tabela `pagina` (preenchida pelo coletor) e cruza com os CNPJs conhecidos
(do candidatos.parquet / CSV de exemplo). Grava em `candidato_dominio`.

Uso:
    python -m enriquecimento.metodo2_rodape
"""
from __future__ import annotations

import pandas as pd

from . import cnpj as cnpj_util
from . import io_contratos

METODO = "rodape_cnpj"
CONFIANCA = 0.95  # CNPJ exato no site é evidência forte


def gerar_candidatos_rodape(con, cnpjs_conhecidos: set[str]) -> pd.DataFrame:
    """Para cada página coletada, acha CNPJs válidos e casa com os CNPJs conhecidos."""
    rows = con.execute(
        "SELECT dominio, texto FROM pagina WHERE NOT bloqueado AND texto IS NOT NULL"
    ).fetchall()

    pares: set[tuple[str, str]] = set()
    for dominio, texto in rows:
        for c in cnpj_util.extrair(texto):
            if c in cnpjs_conhecidos:
                pares.add((c, dominio))

    if not pares:
        return _vazio()

    agora = pd.Timestamp.now()
    data = [
        {"cnpj": c, "dominio": d, "metodo": METODO, "confianca": CONFIANCA,
         "validado": False, "verificado_em": agora}
        for c, d in sorted(pares)
    ]
    return pd.DataFrame(data)


def _vazio() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["cnpj", "dominio", "metodo", "confianca", "validado", "verificado_em"]
    )


def gravar(con, candidatos: pd.DataFrame) -> int:
    if candidatos.empty:
        return 0
    con.register("_novos_rodape", candidatos)
    con.execute(
        """
        INSERT OR REPLACE INTO candidato_dominio
            (cnpj, dominio, metodo, confianca, validado, verificado_em)
        SELECT cnpj, dominio, metodo, confianca, validado, verificado_em
        FROM _novos_rodape
        """
    )
    con.unregister("_novos_rodape")
    return len(candidatos)


def main() -> None:
    df = io_contratos.ler_candidatos()
    conhecidos = set(df["cnpj"])

    con = io_contratos.conectar()
    try:
        io_contratos.criar_tabelas(con)
        candidatos = gerar_candidatos_rodape(con, conhecidos)
        print(f"[metodo2] {len(candidatos)} casamento(s) por CNPJ no rodapé:")
        if not candidatos.empty:
            print(candidatos.to_string(index=False))
        n = gravar(con, candidatos)
        total = con.execute(
            "SELECT count(*) FROM candidato_dominio WHERE metodo = ?", [METODO]
        ).fetchone()[0]
        print(f"[metodo2] {n} gravado(s); total com metodo='rodape_cnpj': {total}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
