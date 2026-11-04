"""Teste mínimo da conexão com o LLM configurado em LLM_PROVEDOR (dono: Micael).

Uso:  python -m motor.teste_conexao

Carrega o .env, pede a cada modelo configurado um JSON {"ok": true} pelo mesmo caminho do
motor (motor.llm.gerar_json) e imprime a resposta e o tempo. Nunca imprime a chave.
"""
from __future__ import annotations

import os
import sys
import time

from . import config, llm

CHAVES = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no terminal do Windows
    chave = CHAVES[config.LLM_PROVEDOR]
    print(f"Provedor: {config.LLM_PROVEDOR}")
    if not os.getenv(chave):
        print(f"{chave} vazia: cole a chave no .env (nunca no chat nem no Git).")
        return 1

    modelos = {"classificação": config.MODELO_CLASSIFICACAO}
    modelos.update({f"ao vivo {i}": m for i, m in enumerate(config.MODELOS_AO_VIVO, 1)})
    falhou = False
    for uso, modelo in modelos.items():
        inicio = time.monotonic()
        try:
            r, _ = llm.gerar_json('Responda {"ok": true}.', SCHEMA, [modelo], tentativas=1, timeout_s=30)
            print(f"[{uso}] {modelo}: {r} em {time.monotonic() - inicio:.1f} s")
        except Exception as e:  # mostra só tipo e mensagem do erro da API
            print(f"[{uso}] {modelo}: ERRO {type(e).__name__}: {str(e)[:200]}")
            falhou = True
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
