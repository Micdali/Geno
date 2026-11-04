"""Ponto de entrada do motor de análise (dono: Micael).

A assinatura de `analisar` faz parte do contrato 4 (contratos/04_resultado_analise.md).

Precisa de: dados/geno.duckdb (Lucas), motor/cache/classificacao.jsonl (python -m motor.classificar)
e motor/cache/embedding.parquet (python -m motor.embeddings). Chama o LLM ao vivo para propor o
recorte (se não vier pronto da tela 2) e para o diferencial.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import classificar, confianca, config, diferencial, embeddings, lacunas, nicho

EXEMPLO = Path(__file__).resolve().parent.parent / "contratos" / "exemplos" / "resultado_analise.exemplo.json"
SITUACAO = {"02": "ativa", "08": "baixada", "03": "suspensa", "04": "inapta", "01": "nula"}


def exemplo(ideia: str) -> dict:
    """Resultado FICTÍCIO do contrato 4, para desenvolver o app sem banco. Nunca usar como resultado."""
    resultado = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    resultado["ideia"] = ideia
    return resultado


# --- acesso ao banco do Lucas (substituível nos testes) ---------------------------------------
def _publicos(cnpjs: list[str]) -> pd.DataFrame:
    from dados import consultas
    return consultas.dados_publicos(cnpjs)


def _saturacao(cnaes: list[str]) -> pd.DataFrame:
    from dados.geno_db import consultas
    ini, fim = config.periodo()
    return consultas.saturacao(cnaes, ano_ini=ini, ano_fim=fim)


def _ativos_setor(cnaes: list[str]) -> int:
    """Estabelecimentos em situação ativa (02) hoje, com CNAE principal do recorte.

    O `ativos_fim_ano` da saturação conta quem não foi baixado, o que inclui inaptas e suspensas
    (em idiomas, 5.610 contra 4.199 ativas em 04/11/2026); a tela diz "ativos", então conta só a 02.
    """
    from dados.geno_db import consultas
    con = consultas.conectar()
    try:
        return int(con.execute(
            "SELECT count(*) FROM vw_publico WHERE situacao = '02' "
            "AND cnae_principal IN (SELECT unnest(?::VARCHAR[]))", [list(cnaes)]).fetchall()[0][0])
    finally:
        con.close()


# --- montagem ---------------------------------------------------------------------------------
def _texto_recorte(recorte: dict) -> str:
    a = recorte["atributos"]
    return embeddings.texto_origem({"descricao_nicho": recorte.get("descricao"), "produto_servico": a.get("produto_servico"),
                                    "publico_atendido": a.get("publico"), "canal_atendimento": a.get("canal")})


def _bloco_saturacao(cnaes: list[str]) -> dict:
    df = _saturacao(cnaes)
    voluntarias = (df["baixas"] - df["baixas_oficio"]).astype(int)
    nomes = ", ".join(f"{c} {config.CNAES_PILOTO.get(c, '')}".strip() for c in cnaes)
    bloco = {
        "anos": df["ano"].astype(int).tolist(),
        "aberturas": df["aberturas"].astype(int).tolist(),
        "baixas": voluntarias.tolist(),
        "total_aberturas": int(df["aberturas"].sum()),
        "total_baixas": int(voluntarias.sum()),
        "fonte": (f"Receita Federal — Dados Abertos do CNPJ, competência 2026-10. Estabelecimentos do "
                  f"{config.UF_PILOTO} com CNAE principal {nomes}. Baixas de ofício excluídas."),
    }
    return bloco


def _concorrentes(ranking: list[tuple[str, float]], classif: pd.DataFrame, publicos: pd.DataFrame) -> list[dict]:
    c = classif.set_index("cnpj")
    p = publicos.set_index("cnpj")
    saida = []
    for cnpj, sim in ranking[: config.MAX_CONCORRENTES]:
        if cnpj not in p.index:  # fora do banco (ex.: CNPJ de outro recorte): não exibe
            continue
        cl, pub = c.loc[cnpj], p.loc[cnpj]
        situacao = SITUACAO.get(pub["situacao"], pub["situacao"])
        o_que = cl["produto_servico"] if cl["produto_servico"] != "indeterminado" else cl["descricao_nicho"]
        saida.append({
            "cnpj": cnpj,
            "nome_exibicao": pub["nome_exibicao"],  # vw_publico: nunca nome de titular de MEI
            "o_que_oferece": o_que,
            "publico": cl["publico_atendido"],
            "canal": cl["canal_atendimento"],
            "situacao": situacao,
            "ano_baixa": int(pd.Timestamp(pub["data_situacao"]).year) if situacao == "baixada" and pd.notna(pub["data_situacao"]) else None,
            "semelhanca": sim,
            "site": cl.get("site"),
        })
    return saida


def analisar(ideia: str, recorte: dict | None = None) -> dict:
    """Analisa o mercado de uma ideia descrita em texto livre.

    Args:
        ideia: texto digitado pelo usuário na tela 1.
        recorte: nicho confirmado/corrigido na tela 2 (None = o motor propõe, via nicho.propor_recorte).

    Returns:
        dict no formato do contrato 4.
    """
    if recorte is None:
        recorte = nicho.propor_recorte(ideia)
    cnaes = [c for c in recorte.get("cnaes", []) if c in config.CNAES_PILOTO] or list(config.CNAES_PILOTO)

    saturacao = _bloco_saturacao(cnaes)
    n_setor = _ativos_setor(cnaes)

    classif = classificar.carregar()
    cnpjs, matriz = embeddings.carregar()
    vetor, vetor_servico = embeddings.vetorizar([_texto_recorte(recorte), recorte["atributos"]["produto_servico"]])
    ranking = lacunas.ranquear(vetor, cnpjs, matriz)
    ranking = lacunas.filtrar_por_servico(vetor_servico, ranking, embeddings.carregar_servico())
    ranking = [(c, s) for c, s in ranking if c in set(classif["cnpj"])]

    publicos = _publicos([c for c, _ in ranking]) if ranking else pd.DataFrame(columns=["cnpj", "nome_exibicao", "situacao", "data_situacao"])
    no_banco = set(publicos["cnpj"])
    ranking = [(c, s) for c, s in ranking if c in no_banco]
    ativos = set(publicos.loc[publicos["situacao"] == "02", "cnpj"])

    parecidas = classif.set_index("cnpj").loc[[c for c, _ in ranking]].reset_index().to_dict("records")
    marcas = lacunas.marcar_atendimento(recorte, parecidas, embeddings.vetorizar)
    lista_lacunas, aviso = lacunas.calcular(recorte, marcas, ativos)
    concorrentes = _concorrentes(ranking, classif, publicos)

    return {
        "ideia": ideia,
        "recorte": {"descricao": recorte.get("descricao", ""), "atributos": recorte["atributos"],
                    "uf": recorte.get("uf", config.UF_PILOTO)},
        "confianca": confianca.avaliar(n_setor, [p["confianca"] for p in parecidas], usou_setor_amplo=True,
                                       aviso_lacuna=aviso),
        "concorrentes": concorrentes,
        "saturacao": saturacao,
        "lacunas": lista_lacunas,
        "diferencial": diferencial.gerar(ideia, recorte, concorrentes, lista_lacunas),
        "gerado_em": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = analisar(" ".join(sys.argv[1:]) or "escola de inglês online para adultos 40+")
    print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
