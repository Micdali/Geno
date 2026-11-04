"""Ideia em texto livre → recorte do nicho (tela 2), com até 3 perguntas de afunilamento (dono: Micael).

    from motor.nicho import propor_recorte
    r = propor_recorte("escola de inglês online para adultos 40+")
    # o usuário responde às perguntas na tela 2:
    r = propor_recorte(ideia, respostas={"As aulas seriam principalmente:": "Conversação"})
    resultado = analisar(ideia, recorte=r)
"""
from __future__ import annotations

from . import config, embeddings, llm

PROMPT_VERSAO = "v2"  # v2: perguntas de múltipla escolha (multipla) e sem "Outro" nas opções
MAX_PERGUNTAS = 3

SCHEMA = {
    "type": "object",
    "properties": {
        "descricao": {"type": "string"},
        "atributos": {
            "type": "object",
            "properties": {
                "publico": {"type": "string"},
                "produto_servico": {"type": "string"},
                "canal": {"type": "string", "enum": ["presencial", "online", "delivery", "hibrido", "indeterminado"]},
            },
            "required": ["publico", "produto_servico", "canal"],
        },
        "cnaes": {"type": "array", "items": {"type": "string", "enum": list(config.CNAES_PILOTO)}},
        "perguntas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"pergunta": {"type": "string"},
                               "opcoes": {"type": "array", "items": {"type": "string"}},
                               "multipla": {"type": "boolean"}},  # true: a pessoa pode marcar várias
                "required": ["pergunta", "opcoes", "multipla"],
            },
        },
    },
    "required": ["descricao", "atributos", "cnaes", "perguntas"],
}


def propor_recorte(ideia: str, respostas: dict[str, str] | None = None, gerar=None) -> dict:
    """Propõe o recorte da ideia (chama o LLM ao vivo).

    Returns:
        {"descricao", "atributos": {publico, produto_servico, canal}, "uf", "cnaes": [...],
         "perguntas": [{"pergunta", "opcoes", "multipla"}]}. A tela acrescenta "Outro" com texto livre. Os três primeiros campos são o `recorte` do
        contrato 4; `cnaes` e `perguntas` são extras para a tela 2 e para a saturação.
    """
    cnaes = "\n".join(f"- {c}: {d}" for c, d in config.CNAES_PILOTO.items())
    extra = ""
    if respostas:
        extra = "Respostas da pessoa às perguntas anteriores (use-as e não pergunte de novo):\n" + \
                "\n".join(f"- {p} {r}" for p, r in respostas.items())
    prompt = (config.PASTA_PROMPTS / f"nicho_{PROMPT_VERSAO}.md").read_text(encoding="utf-8").format(
        max_perguntas=MAX_PERGUNTAS, cnaes=cnaes, ideia=ideia.strip(), respostas=extra)
    if gerar is None:  # chamada real (tela 1): o modelo de embedding carrega enquanto a pessoa lê a tela 2
        embeddings.aquecer()
    r, _ = (gerar or llm.gerar_json)(prompt, SCHEMA, config.MODELOS_AO_VIVO,
                                         tentativas=config.TENTATIVAS_AO_VIVO, timeout_s=config.TIMEOUT_AO_VIVO_S)
    r["uf"] = config.UF_PILOTO
    # "Ensino de música · aulas · crianças · indeterminado": o pedaço "indeterminado" não vai para a tela
    partes = [p.strip() for p in (r.get("descricao") or "").split("·")]
    r["descricao"] = " · ".join(p for p in partes if p and p.lower() != "indeterminado")
    r["cnaes"] = [c for c in r.get("cnaes", []) if c in config.CNAES_PILOTO] or list(config.CNAES_PILOTO)
    perguntas = [] if respostas and len(respostas) >= MAX_PERGUNTAS else r.get("perguntas", [])[:MAX_PERGUNTAS]
    for p in perguntas:  # "Outro" é da tela, com texto livre; o LLM às vezes o inclui mesmo assim
        p["opcoes"] = [o for o in p.get("opcoes", []) if o.strip().lower().rstrip(".:") != "outro"]
        p["multipla"] = bool(p.get("multipla"))
    r["perguntas"] = perguntas
    return r
