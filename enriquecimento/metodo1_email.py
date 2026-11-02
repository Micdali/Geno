"""
Método 1 — domínio do e-mail cadastral.

O mais barato dos métodos: o domínio do e-mail da Receita costuma ser o site da
empresa. Duas limpezas são obrigatórias (seção 9 do relatório / README do módulo):

1. Descartar provedores de e-mail gratuitos (gmail, hotmail, ...), que não são o
   site da empresa.
2. Descartar domínios que aparecem em MUITOS CNPJs — tipicamente o escritório de
   contabilidade ou a hospedagem que cadastrou vários clientes com o próprio e-mail.

O que sobra vira uma linha em `candidato_dominio` com metodo='email'.

Uso:
    python -m enriquecimento.metodo1_email
"""
from __future__ import annotations

import pandas as pd

from . import config, io_contratos

METODO = "email"

# Confiança do método (0 a 1). v0: um pouco maior quando o domínio é exclusivo de
# um CNPJ no lote; menor quando é compartilhado por poucos.
CONFIANCA_EXCLUSIVO = 0.75
CONFIANCA_COMPARTILHADO = 0.65

# Acima de quantos CNPJs distintos um mesmo domínio é tratado como infra
# compartilhada (contador/hospedagem) e descartado. Ajustável.
MAX_CNPJS_POR_DOMINIO = 5

# Provedores de e-mail gratuitos / genéricos — nunca são o site da empresa.
PROVEDORES_EMAIL = {
    "gmail.com", "googlemail.com",
    "hotmail.com", "hotmail.com.br",
    "outlook.com", "outlook.com.br", "live.com", "msn.com",
    "yahoo.com", "yahoo.com.br", "ymail.com",
    "icloud.com", "me.com",
    "bol.com.br", "uol.com.br", "terra.com.br", "ig.com.br",
    "globo.com", "globomail.com", "oi.com.br", "zipmail.com.br",
    "aol.com", "protonmail.com", "gmx.com",
}


def _normalizar_dominio(valor: object) -> str | None:
    """Minúsculas, sem www., sem caminho/espaços. Retorna None se vazio/inválido."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    dom = str(valor).strip().lower()
    if not dom or dom == "nan":
        return None
    # se vier um e-mail inteiro, fica só o domínio
    if "@" in dom:
        dom = dom.rsplit("@", 1)[-1]
    dom = dom.removeprefix("http://").removeprefix("https://").removeprefix("www.")
    dom = dom.split("/", 1)[0].strip()
    return dom or None


def gerar_candidatos_email(
    df: pd.DataFrame,
    max_cnpjs_por_dominio: int = MAX_CNPJS_POR_DOMINIO,
) -> pd.DataFrame:
    """Recebe os candidatos (contrato 2) e devolve linhas para `candidato_dominio`.

    Colunas de saída: cnpj, dominio, metodo, confianca, validado, verificado_em.
    """
    base = df[["cnpj", "dominio_email"]].copy()
    base["dominio"] = base["dominio_email"].map(_normalizar_dominio)
    base = base.dropna(subset=["dominio"])

    # (1) descartar provedores gratuitos
    base = base[~base["dominio"].isin(PROVEDORES_EMAIL)]

    # cada par (cnpj, dominio) conta uma vez
    base = base.drop_duplicates(subset=["cnpj", "dominio"])

    # (2) descartar domínios compartilhados por muitos CNPJs (contadores/hospedagem)
    cnpjs_por_dominio = base.groupby("dominio")["cnpj"].nunique()
    compartilhado_demais = cnpjs_por_dominio[cnpjs_por_dominio > max_cnpjs_por_dominio].index
    base = base[~base["dominio"].isin(compartilhado_demais)]

    if base.empty:
        return _vazio()

    # confiança conforme exclusividade do domínio no lote filtrado
    n_por_dominio = base.groupby("dominio")["cnpj"].transform("nunique")
    base["confianca"] = (n_por_dominio == 1).map(
        {True: CONFIANCA_EXCLUSIVO, False: CONFIANCA_COMPARTILHADO}
    )
    base["metodo"] = METODO
    base["validado"] = False
    base["verificado_em"] = pd.Timestamp.now()

    saida = base[["cnpj", "dominio", "metodo", "confianca", "validado", "verificado_em"]]
    return saida.reset_index(drop=True)


def _vazio() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["cnpj", "dominio", "metodo", "confianca", "validado", "verificado_em"]
    )


def gravar(con, candidatos: pd.DataFrame) -> int:
    """Grava (upsert) as linhas na tabela candidato_dominio. Retorna quantas."""
    if candidatos.empty:
        return 0
    con.register("_novos_email", candidatos)
    con.execute(
        """
        INSERT OR REPLACE INTO candidato_dominio
            (cnpj, dominio, metodo, confianca, validado, verificado_em)
        SELECT cnpj, dominio, metodo, confianca, validado, verificado_em
        FROM _novos_email
        """
    )
    con.unregister("_novos_email")
    return len(candidatos)


def main() -> None:
    df = io_contratos.ler_candidatos()
    candidatos = gerar_candidatos_email(df)

    print(f"[metodo1] {len(candidatos)} candidato(s) por domínio de e-mail:")
    if not candidatos.empty:
        print(candidatos.to_string(index=False))

    con = io_contratos.conectar()
    try:
        io_contratos.criar_tabelas(con)
        n = gravar(con, candidatos)
        print(f"[metodo1] {n} linha(s) gravada(s) em candidato_dominio.")
        total = con.execute(
            "SELECT count(*) FROM candidato_dominio WHERE metodo = ?", [METODO]
        ).fetchone()[0]
        print(f"[metodo1] total com metodo='email' no banco: {total}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
