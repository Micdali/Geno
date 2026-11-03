"""Em comum / possíveis diferenciais / não verificado (dono: Micael). Chama o LLM ao vivo."""
from __future__ import annotations

from . import config, llm

PROMPT_VERSAO = "v1"
CAMPOS = ["em_comum", "possiveis_diferenciais", "nao_verificado"]
SCHEMA = {"type": "object", "properties": {c: {"type": "string"} for c in CAMPOS}, "required": CAMPOS}


def gerar(ideia: str, recorte: dict, concorrentes: list[dict], lacunas: list[dict], gerar_json=None) -> dict:
    if not concorrentes:
        return {"em_comum": "Não encontramos empresas parecidas com site analisado.",
                "possiveis_diferenciais": "Sem empresas parecidas para comparar, não dá para apontar diferenciais.",
                "nao_verificado": "Empresas sem site, preços e demanda."}
    lista = "\n".join(f"- {c['o_que_oferece']} | público: {c['publico']} | canal: {c['canal']} | "
                      f"{c['situacao']} | semelhança {c['semelhanca']:.2f}" for c in concorrentes)
    lac = "\n".join(f"- {l['titulo']}: {l['n_empresas_que_oferecem']} de {l['n_empresas_analisadas']} oferecem"
                    for l in lacunas) or "- nenhuma (ou dados insuficientes)"
    prompt = (config.PASTA_PROMPTS / f"diferencial_{PROMPT_VERSAO}.md").read_text(encoding="utf-8").format(
        ideia=ideia.strip(), recorte=recorte.get("descricao", ""), concorrentes=lista, lacunas=lac)
    try:
        r, _ = (gerar_json or llm.gerar_json)(prompt, SCHEMA, config.MODELOS_AO_VIVO, temperatura=0.3,
                                               tentativas=config.TENTATIVAS_AO_VIVO)
    except llm.LLMIndisponivel:
        return {"em_comum": "Não foi possível gerar este resumo agora.",
                "possiveis_diferenciais": "Veja as lacunas e a lista de concorrentes acima.",
                "nao_verificado": "O serviço de IA não respondeu; tente de novo em instantes."}
    return {c: r.get(c, "").strip() for c in CAMPOS}
