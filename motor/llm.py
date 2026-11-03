"""Chamadas ao LLM (OpenAI ou Gemini, por LLM_PROVEDOR) com saída JSON por schema, novas tentativas
e modelo de reserva (dono: Micael)."""
from __future__ import annotations

import copy
import json
import threading
import time
from collections import defaultdict
from functools import lru_cache

import openai
from google import genai
from google.genai import errors, types

TENTATIVAS = 4
ESPERA_INICIAL = 2.0  # segundos; dobra a cada tentativa
# Tokens gastos neste processo, por modelo (só OpenAI): {modelo: [entrada, saída]}. Para a tabela de custo.
USO: dict[str, list[int]] = defaultdict(lambda: [0, 0])
_TRAVA_USO = threading.Lock()


class LLMIndisponivel(RuntimeError):
    """Nenhum modelo respondeu depois das novas tentativas."""


@lru_cache(maxsize=4)
def _cliente_gemini(timeout_s: int) -> genai.Client:
    from . import config  # noqa: F401  (carrega o .env)
    # Sem as novas tentativas internas do SDK: quem tenta de novo (e troca de modelo) é gerar_json.
    opcoes = types.HttpOptions(timeout=timeout_s * 1000, retry_options=types.HttpRetryOptions(attempts=1))
    return genai.Client(http_options=opcoes)  # lê GEMINI_API_KEY do ambiente


@lru_cache(maxsize=4)
def _cliente_openai(timeout_s: int) -> openai.OpenAI:
    from . import config  # noqa: F401  (carrega o .env)
    return openai.OpenAI(max_retries=0, timeout=float(timeout_s))  # lê OPENAI_API_KEY do ambiente


def schema_estrito(schema: dict) -> dict:
    """Cópia do schema no formato estrito da OpenAI: todo objeto com additionalProperties false
    e todos os campos em required. O Gemini continua recebendo o schema original."""
    s = copy.deepcopy(schema)

    def ajustar(no):
        if isinstance(no, dict):
            if no.get("type") == "object" and "properties" in no:
                no["additionalProperties"] = False
                no["required"] = list(no["properties"])
            for v in no.values():
                ajustar(v)
        elif isinstance(no, list):
            for v in no:
                ajustar(v)

    ajustar(s)
    return s


def _temporario(e: Exception) -> bool:
    """429 (cota), 5xx (sobrecarga), estouro do tempo e falha de conexão valem nova tentativa;
    o resto é erro de verdade."""
    if isinstance(e, (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)):
        return True  # APIConnectionError inclui APITimeoutError
    if isinstance(e, openai.APIStatusError):
        return e.status_code in (408, 429) or e.status_code >= 500
    codigo = getattr(e, "code", None)
    return isinstance(e, errors.ServerError) or codigo == 429 or "Timeout" in type(e).__name__


def _gerar_gemini(prompt, schema, modelo, sistema, temperatura, timeout_s) -> str:
    cfg = types.GenerateContentConfig(
        system_instruction=sistema,
        temperature=temperatura,
        response_mime_type="application/json",
        response_json_schema=schema,
    )
    return _cliente_gemini(timeout_s).models.generate_content(model=modelo, contents=prompt, config=cfg).text


def _gerar_openai(prompt, schema, modelo, sistema, temperatura, timeout_s) -> str:
    from . import config
    entrada = ([{"role": "system", "content": sistema}] if sistema else []) + [{"role": "user", "content": prompt}]
    extra = {}
    if config.OPENAI_ESFORCO and not modelo.startswith(("gpt-4", "gpt-3")):  # só modelos com raciocínio
        extra["reasoning"] = {"effort": config.OPENAI_ESFORCO}
    r = _cliente_openai(timeout_s).responses.create(
        model=modelo,
        input=entrada,
        temperature=temperatura,
        text={"format": {"type": "json_schema", "name": "saida", "schema": schema_estrito(schema), "strict": True}},
        **extra,
    )
    if r.usage:
        with _TRAVA_USO:
            USO[modelo][0] += r.usage.input_tokens
            USO[modelo][1] += r.usage.output_tokens
    return r.output_text  # vazio em recusa ou resposta incompleta: o json.loads falha e tenta de novo


def gerar_json(prompt: str, schema: dict, modelos: list[str], sistema: str | None = None,
               temperatura: float = 0.2, tentativas: int = TENTATIVAS,
               timeout_s: int = 60) -> tuple[dict, str]:
    """Pede ao LLM um JSON no formato `schema`.

    Tenta cada modelo de `modelos` em ordem, com até `tentativas` por modelo em erro temporário.

    Returns:
        (objeto JSON, nome do modelo que respondeu)
    """
    from . import config
    chamar = _gerar_openai if config.LLM_PROVEDOR == "openai" else _gerar_gemini
    ultimo: Exception | None = None
    for modelo in modelos:
        espera = ESPERA_INICIAL
        for tentativa in range(1, tentativas + 1):
            try:
                return json.loads(chamar(prompt, schema, modelo, sistema, temperatura, timeout_s)), modelo
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
