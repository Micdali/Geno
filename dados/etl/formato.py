"""Formatação em português para os documentos gerados pelo ETL (DECISOES.md, METRICAS.md).

Números no padrão do artigo: milhar com ponto, decimal com vírgula, porcentagem com 1 casa.
"""
from __future__ import annotations

_MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}


def num(n) -> str:
    """1234567 -> '1.234.567'."""
    return f"{int(n):,}".replace(",", ".")


def dec(x: float, casas: int = 1) -> str:
    """12.34 -> '12,3'."""
    return f"{x:.{casas}f}".replace(".", ",")


def pct(fracao: float) -> str:
    """0.2751 -> '27,5%'."""
    return dec(100 * fracao) + "%"


def nome_proprio(texto: str) -> str:
    """'RIO DE JANEIRO' -> 'Rio de Janeiro' (artigos e preposições em minúscula)."""
    palavras = texto.lower().split()
    return " ".join(p if (i and p in _MINUSCULAS) else p.capitalize() for i, p in enumerate(palavras))


def tabela_md(cabecalho: list[str], linhas: list[list]) -> str:
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "|".join(["---"] * len(cabecalho)) + "|"]
    out += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(out)
