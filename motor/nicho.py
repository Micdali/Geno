"""Ideia em texto livre → recorte do nicho (tela 2), com até 3 perguntas de afunilamento (dono: Micael).

    from motor.nicho import propor_recorte
    r = propor_recorte("escola de inglês online para adultos 40+")
    # o usuário responde às perguntas na tela 2:
    r = propor_recorte(ideia, respostas={"As aulas seriam principalmente:": "Conversação"})
    resultado = analisar(ideia, recorte=r)
"""
from __future__ import annotations

from . import config, llm

PROMPT_VERSAO = "v1"
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
                               "opcoes": {"type": "array", "items": {"type": "string"}}},
                "required": ["pergunta", "opcoes"],
            },
        },
    },
    "required": ["descricao", "atributos", "cnaes", "perguntas"],
}


def propor_recorte(ideia: str, respostas: dict[str, str] | None = None, gerar=None) -> dict:
    """Propõe o recorte da ideia (chama o LLM ao vivo).

    Returns:
        {"descricao", "atributos": {publico, produto_servico, canal}, "uf", "cnaes": [...],
         "perguntas": [{"pergunta", "opcoes"}]}. Os três primeiros campos são o `recorte` do
        contrato 4; `cnaes` e `perguntas` são extras para a tela 2 e para a saturação.
    """
    cnaes = "\n".join(f"- {c}: {d}" for c, d in config.CNAES_PILOTO.items())
    extra = ""
    if respostas:
        extra = "Respostas da pessoa às perguntas anteriores (use-as e não pergunte de novo):\n" + \
                "\n".join(f"- {p} {r}" for p, r in respostas.items())
    prompt = (config.PASTA_PROMPTS / f"nicho_{PROMPT_VERSAO}.md").read_text(encoding="utf-8").format(
        max_perguntas=MAX_PERGUNTAS, cnaes=cnaes, ideia=ideia.strip(), respostas=extra)
    r, _ = (gerar or llm.gerar_json)(prompt, SCHEMA, config.MODELOS_AO_VIVO,
                                         tentativas=config.TENTATIVAS_AO_VIVO)
    r["uf"] = config.UF_PILOTO
    r["cnaes"] = [c for c in r.get("cnaes", []) if c in config.CNAES_PILOTO] or list(config.CNAES_PILOTO)
    r["perguntas"] = [] if respostas and len(respostas) >= MAX_PERGUNTAS else r.get("perguntas", [])[:MAX_PERGUNTAS]
    return r
