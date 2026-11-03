"""Chamadas ao Gemini com saída JSON por schema, novas tentativas e modelo de reserva (dono: Micael)."""
from __future__ import annotations

import json
import time
from functools import lru_cache

from google import genai
from google.genai import errors, types

TENTATIVAS = 4
ESPERA_INICIAL = 2.0  # segundos; dobra a cada tentativa


class LLMIndisponivel(RuntimeError):
    """Nenhum modelo respondeu depois das novas tentativas."""


@lru_cache(maxsize=4)
def _cliente(timeout_s: int) -> genai.Client:
    from . import config  # noqa: F401  (carrega o .env)
    # Sem as novas tentativas internas do SDK: quem tenta de novo (e troca de modelo) é gerar_json.
    opcoes = types.HttpOptions(timeout=timeout_s * 1000, retry_options=types.HttpRetryOptions(attempts=1))
    return genai.Client(http_options=opcoes)  # lê GEMINI_API_KEY do ambiente


def _temporario(e: Exception) -> bool:
    """429 (cota), 5xx (sobrecarga) e estouro do tempo valem nova tentativa; o resto é erro de verdade."""
    codigo = getattr(e, "code", None)
    return isinstance(e, errors.ServerError) or codigo == 429 or "Timeout" in type(e).__name__


def gerar_json(prompt: str, schema: dict, modelos: list[str], sistema: str | None = None,
               temperatura: float = 0.2, tentativas: int = TENTATIVAS,
               timeout_s: int = 60) -> tuple[dict, str]:
    """Pede ao LLM um JSON no formato `schema`.

    Tenta cada modelo de `modelos` em ordem, com até `tentativas` por modelo em erro temporário.

    Returns:
        (objeto JSON, nome do modelo que respondeu)
    """
    cfg = types.GenerateContentConfig(
        system_instruction=sistema,
        temperature=temperatura,
        response_mime_type="application/json",
        response_json_schema=schema,
    )
    ultimo: Exception | None = None
    for modelo in modelos:
        espera = ESPERA_INICIAL
        for tentativa in range(1, tentativas + 1):
            try:
                r = _cliente(timeout_s).models.generate_content(model=modelo, contents=prompt, config=cfg)
                return json.loads(r.text), modelo
            except json.JSONDecodeError as e:  # raro com schema; tenta de novo
                ultimo = e
            except Exception as e:
                if not _temporario(e):
                    raise
                ultimo = e
            if tentativa < tentativas:  # na última, troca de modelo sem esperar
                time.sleep(espera)
                espera *= 2
    raise LLMIndisponivel(f"Nenhum modelo respondeu ({', '.join(modelos)}): {ultimo}")
