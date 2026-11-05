"""
Utilitários de CNPJ: normalização, validação do dígito verificador e extração de
CNPJs de um texto.

Suporta o CNPJ numérico tradicional e o novo CNPJ alfanumérico (12 primeiras
posições em [0-9A-Z], 2 últimas numéricas), cujo DV usa o valor ASCII menos 48.
"""
from __future__ import annotations

import re

_PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

# CNPJ formatado (alfanumérico ou numérico) — alta precisão
_RE_FORMATADO = re.compile(
    r"\b([0-9A-Za-z]{2}\.[0-9A-Za-z]{3}\.[0-9A-Za-z]{3}/[0-9A-Za-z]{4}-\d{2})\b"
)
# 14 posições sem pontuação, sem grudar em outros alfanuméricos
_RE_CRU = re.compile(r"(?<![0-9A-Za-z])([0-9A-Za-z]{12}\d{2})(?![0-9A-Za-z])")


def normalizar(valor: str) -> str:
    """Tira pontuação e devolve em maiúsculas (14 posições se for CNPJ)."""
    return re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()


def _dv(base: str, pesos: list[int]) -> str:
    soma = sum((ord(c) - 48) * p for c, p in zip(base, pesos))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def valido(cnpj: str) -> bool:
    """True se o CNPJ (14 posições, com ou sem pontuação) tem DV correto."""
    c = normalizar(cnpj)
    if len(c) != 14 or not c[:12].isalnum() or not c[12:].isdigit():
        return False
    if c == c[0] * 14:  # sequência repetida (ex.: 00000000000000)
        return False
    dv1 = _dv(c[:12], _PESOS_DV1)
    dv2 = _dv(c[:12] + dv1, _PESOS_DV2)
    return c[12:] == dv1 + dv2


def extrair(texto: str) -> list[str]:
    """Extrai CNPJs válidos de um texto, normalizados e sem repetição (ordem estável)."""
    if not texto:
        return []
    achados: list[str] = []
    vistos: set[str] = set()
    for regex in (_RE_FORMATADO, _RE_CRU):
        for m in regex.finditer(texto):
            c = normalizar(m.group(1))
            if len(c) == 14 and c not in vistos and valido(c):
                vistos.add(c)
                achados.append(c)
    return achados
