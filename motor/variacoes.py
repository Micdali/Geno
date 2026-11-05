"""Variações próximas da ideia, para procurar lacunas além da combinação original (dono: Micael).

O LLM só propõe as variações (mudando público, serviço ou canal); quem diz se cada uma é rara é o
motor, contando as escolas que já oferecem (lacunas.calcular). Nada aqui afirma demanda.
"""
from __future__ import annotations

from . import config, llm

PROMPT_VERSAO = "v1"
MIN_VARIACOES, MAX_VARIACOES = 6, 8
CANAIS = ["presencial", "online", "delivery", "hibrido", "indeterminado"]

SCHEMA = {
    "type": "object",
    "properties": {
        "variacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "publico": {"type": "string"},
                    "produto_servico": {"type": "string"},
                    "canal": {"type": "string", "enum": CANAIS},
                },
                "required": ["titulo", "publico", "produto_servico", "canal"],
            },
        },
    },
    "required": ["variacoes"],
}


def propor(ideia: str, recorte: dict, gerar=None) -> list[dict]:
    """Variações da ideia: [{titulo, atributos: {publico, produto_servico, canal}}]. Vazio se o LLM falhar."""
    a = recorte["atributos"]
    prompt = (config.PASTA_PROMPTS / f"variacoes_{PROMPT_VERSAO}.md").read_text(encoding="utf-8").format(
        min_variacoes=MIN_VARIACOES, max_variacoes=MAX_VARIACOES, ideia=ideia.strip(),
        produto_servico=a.get("produto_servico", ""), publico=a.get("publico", ""), canal=a.get("canal", ""))
    try:
        r, _ = (gerar or llm.gerar_json)(prompt, SCHEMA, config.MODELOS_AO_VIVO, temperatura=0.5,
                                         tentativas=config.TENTATIVAS_AO_VIVO, timeout_s=config.TIMEOUT_AO_VIVO_S)
    except llm.LLMIndisponivel:
        return []
    saida = []
    for v in r.get("variacoes", [])[:MAX_VARIACOES]:
        if not (v.get("titulo") or "").strip() or not (v.get("produto_servico") or "").strip():
            continue
        saida.append({"titulo": v["titulo"].strip(), "atributos": {
            "publico": (v.get("publico") or "indeterminado").strip(),
            "produto_servico": v["produto_servico"].strip(),
            "canal": v.get("canal") if v.get("canal") in CANAIS else "indeterminado"}})
    return saida
