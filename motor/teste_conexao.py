"""Teste mínimo da conexão com o Gemini (dono: Micael).

Uso:  python -m motor.teste_conexao

Carrega o .env, chama os dois modelos configurados com "responda só OK" e
imprime a resposta. Nunca imprime a chave.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google import genai


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no terminal do Windows
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY vazia: cole a chave no .env (nunca no chat nem no Git).")
        return 1

    client = genai.Client()  # lê GEMINI_API_KEY do ambiente
    modelos = {
        "classificação": os.getenv("LLM_MODELO_CLASSIFICACAO"),
        "análise": os.getenv("LLM_MODELO_ANALISE"),
    }
    falhou = False
    for uso, modelo in modelos.items():
        if not modelo:
            print(f"[{uso}] LLM_MODELO_* não definido no .env")
            falhou = True
            continue
        try:
            r = client.models.generate_content(model=modelo, contents="Responda só OK.")
            print(f"[{uso}] {modelo}: {r.text.strip()!r}")
        except Exception as e:  # mostra só tipo e mensagem do erro da API
            print(f"[{uso}] {modelo}: ERRO {type(e).__name__}: {e}")
            falhou = True
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
