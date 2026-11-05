"""
Método 3 — nome fantasia × título da página inicial.

Para cada home já coletada (tabela `pagina`), compara o título/<h1> do site com o
nome fantasia de cada empresa conhecida. O melhor casamento acima do limiar vira
uma hipótese em `candidato_dominio` (metodo='nome_titulo'). Sinal mais fraco que o
CNPJ no rodapé, então a confiança acompanha a similaridade.

Uso:
    python -m enriquecimento.metodo3_nome_titulo
"""
from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz, process
from unidecode import unidecode

from . import coletor, io_contratos

METODO = "nome_titulo"
LIMIAR = 80          # similaridade mínima (0-100) para aceitar
CONFIANCA_MAX = 0.9  # título bate bem, mas é mais fraco que CNPJ no rodapé


def _norm(s: object) -> str:
    return " ".join(unidecode(str(s or "")).lower().split())


def gerar_candidatos_titulo(con, candidatos: pd.DataFrame, limiar: int = LIMIAR) -> pd.DataFrame:
    nomes = candidatos.dropna(subset=["nome_fantasia"])
    nomes = nomes[nomes["nome_fantasia"].astype(str).str.strip() != ""]
    cnpjs = list(nomes["cnpj"])
    escolhas = [_norm(n) for n in nomes["nome_fantasia"]]
    if not escolhas:
        return _vazio()

    rows = con.execute(
        "SELECT dominio, texto FROM pagina "
        "WHERE tipo = 'home' AND NOT bloqueado AND texto IS NOT NULL"
    ).fetchall()

    agora = pd.Timestamp.now()
    saida = []
    for dominio, texto in rows:
        titulo = _norm(coletor.titulo_de(texto))
        if not titulo:
            continue
        match = process.extractOne(titulo, escolhas, scorer=fuzz.token_set_ratio)
        if match is None:
            continue
        _, score, idx = match
        if score >= limiar:
            saida.append({
                "cnpj": cnpjs[idx], "dominio": dominio, "metodo": METODO,
                "confianca": min(CONFIANCA_MAX, round(score / 100, 2)),
                "validado": False, "verificado_em": agora,
            })

    return pd.DataFrame(saida) if saida else _vazio()


def _vazio() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["cnpj", "dominio", "metodo", "confianca", "validado", "verificado_em"]
    )


def gravar(con, candidatos: pd.DataFrame) -> int:
    if candidatos.empty:
        return 0
    con.register("_novos_titulo", candidatos)
    con.execute(
        """
        INSERT OR REPLACE INTO candidato_dominio
            (cnpj, dominio, metodo, confianca, validado, verificado_em)
        SELECT cnpj, dominio, metodo, confianca, validado, verificado_em
        FROM _novos_titulo
        """
    )
    con.unregister("_novos_titulo")
    return len(candidatos)


def main() -> None:
    df = io_contratos.ler_candidatos()
    con = io_contratos.conectar()
    try:
        io_contratos.criar_tabelas(con)
        candidatos = gerar_candidatos_titulo(con, df)
        print(f"[metodo3] {len(candidatos)} casamento(s) por nome × título:")
        if not candidatos.empty:
            print(candidatos.to_string(index=False))
        n = gravar(con, candidatos)
        total = con.execute(
            "SELECT count(*) FROM candidato_dominio WHERE metodo = ?", [METODO]
        ).fetchone()[0]
        print(f"[metodo3] {n} gravado(s); total com metodo='nome_titulo': {total}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
