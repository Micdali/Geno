"""Ponto de entrada do motor de análise (dono: Micael).

A assinatura de `analisar` faz parte do contrato 4 (contratos/04_resultado_analise.md).
Hoje ela devolve o arquivo de exemplo, para o app já funcionar de ponta a ponta.
"""
from __future__ import annotations

import json
from pathlib import Path

EXEMPLO = Path(__file__).resolve().parent.parent / "contratos" / "exemplos" / "resultado_analise.exemplo.json"


def analisar(ideia: str, recorte: dict | None = None) -> dict:
    """Analisa o mercado de uma ideia descrita em texto livre.

    Args:
        ideia: texto digitado pelo usuário na tela 1.
        recorte: nicho confirmado/corrigido na tela 2 (None = o motor propõe).

    Returns:
        dict no formato do contrato 4.
    """
    # TODO (Micael): trocar pelo pipeline real, mantendo esta assinatura.
    resultado = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    resultado["ideia"] = ideia
    return resultado


if __name__ == "__main__":
    r = analisar("escola de inglês online para adultos 40+")
    print(r["recorte"]["descricao"], "|", r["confianca"]["nivel"], "|", len(r["concorrentes"]), "concorrentes")
