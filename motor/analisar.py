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

import numpy as np
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


def _vetorizar_com_memoria(textos_iniciais: list[str]):
    """Vetoriza `textos_iniciais` agora e devolve um vetorizar que reaproveita esses vetores."""
    memoria = dict(zip(textos_iniciais, embeddings.vetorizar(textos_iniciais)))

    def vetorizar(textos: list[str]) -> np.ndarray:
        faltam = list(dict.fromkeys(t for t in textos if t not in memoria))
        if faltam:
            memoria.update(zip(faltam, embeddings.vetorizar(faltam)))
        return np.stack([memoria[t] for t in textos]) if textos else np.zeros((0, 384), dtype=np.float32)

    return vetorizar


def _num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def interpretar_saturacao(bloco: dict, n_setor: int) -> dict:
    """O que os números de aberturas e baixas querem dizer na prática, em linguagem simples.

    Regras fixas sobre os dados (sem LLM, para não inventar): razão baixas/aberturas, saldo e a
    tendência do primeiro ao último ano. Nunca diz para abrir ou não abrir.

    Returns:
        {"titulo": frase-resumo, "paragrafos": [...]}; vazio se não houver dados.
    """
    anos, ab, bx = bloco.get("anos") or [], bloco.get("aberturas") or [], bloco.get("baixas") or []
    if not anos or not sum(ab):
        return {"titulo": "", "paragrafos": []}
    total_ab, total_bx = bloco["total_aberturas"], bloco["total_baixas"]
    saldo, razao = total_ab - total_bx, total_bx / total_ab
    a0, a1 = anos[0], anos[-1]
    var = lambda xs: (xs[-1] - xs[0]) / xs[0] * 100 if xs[0] else 0.0  # noqa: E731
    v_ab, v_bx = var(ab), var(bx)

    if saldo <= 0:
        titulo = "Setor encolhendo: mais negócios fecharam do que abriram"
        pratica = ("Na prática, há espaço deixado por quem saiu, mas o setor está perdendo empresas. "
                   "Vale entender por que tantos fecharam antes de entrar.")
    elif razao >= 0.6:
        titulo = "Setor com muita rotatividade: muita gente entra e muita gente sai"
        pratica = ("Na prática, entrar neste mercado é comum; permanecer é o desafio. "
                   "Boa parte de quem abre não chega longe, então diferenciação e custo baixo pesam.")
    else:
        titulo = "Setor em expansão: abrem bem mais negócios do que fecham"
        pratica = ("Na prática, o setor atrai gente nova todo ano. Isso sugere procura, mas também "
                   "concorrência chegando: você disputaria espaço com empresas novas, não só com as antigas.")

    if v_bx > v_ab + 15:
        tendencia = (f"Mas as baixas cresceram mais rápido que as aberturas ({v_bx:+.0f}% contra {v_ab:+.0f}% "
                     f"de {a0} a {a1}): o mercado está ficando mais apertado.")
    elif v_ab > v_bx + 15:
        tendencia = (f"E as aberturas cresceram mais rápido que as baixas ({v_ab:+.0f}% contra {v_bx:+.0f}% "
                     f"de {a0} a {a1}): o setor segue atraindo gente nova.")
    else:
        tendencia = (f"Aberturas ({v_ab:+.0f}%) e baixas ({v_bx:+.0f}%) variaram no mesmo ritmo de {a0} a {a1}: "
                     "o ritmo do setor está estável.")

    por_10 = max(0, round(razao * 10))
    return {"titulo": titulo, "paragrafos": [
        f"De {a0} a {a1}, abriram {_num(total_ab)} estabelecimentos e {_num(total_bx)} deram baixa no CNPJ: "
        f"para cada 10 que abriram, cerca de {por_10} fecharam. O saldo foi de {'+' if saldo > 0 else '-'}"
        f"{_num(abs(saldo))} e hoje o setor tem {_num(n_setor)} estabelecimentos ativos no {config.UF_PILOTO}.",
        tendencia,
        pratica,
    ]}


def analisar(ideia: str, recorte: dict | None = None, progresso=None) -> dict:
    """Analisa o mercado de uma ideia descrita em texto livre.

    Args:
        ideia: texto digitado pelo usuário na tela 1.
        recorte: nicho confirmado/corrigido na tela 2 (None = o motor propõe, via nicho.propor_recorte).
        progresso: opcional; chamado com o texto de cada etapa real (o app mostra na animação).

    Returns:
        dict no formato do contrato 4.
    """
    avisar = progresso or (lambda texto: None)
    if recorte is None:
        avisar("Identificando o nicho da sua ideia")
        recorte = nicho.propor_recorte(ideia)
    cnaes = [c for c in recorte.get("cnaes", []) if c in config.CNAES_PILOTO] or list(config.CNAES_PILOTO)

    avisar("Contando aberturas e baixas no setor")
    saturacao = _bloco_saturacao(cnaes)
    n_setor = _ativos_setor(cnaes)
    saturacao["interpretacao"] = interpretar_saturacao(saturacao, n_setor)

    classif = classificar.carregar()
    cnpjs, matriz = embeddings.carregar()
    avisar(f"Comparando com as {_num(len(cnpjs))} escolas com site")
    # Todos os textos da ideia numa chamada só, antes de abrir o banco: no app (Streamlit), vetorizar
    # depois das consultas ao DuckDB chegou a levar 6 s para 2 textos (04/11/2026).
    vetorizar = _vetorizar_com_memoria([_texto_recorte(recorte), recorte["atributos"]["produto_servico"],
                                        recorte["atributos"]["publico"]])
    vetor, vetor_servico = vetorizar([_texto_recorte(recorte), recorte["atributos"]["produto_servico"]])
    ranking = lacunas.ranquear(vetor, cnpjs, matriz)
    ranking = lacunas.filtrar_por_servico(vetor_servico, ranking, embeddings.carregar_servico())
    ranking = [(c, s) for c, s in ranking if c in set(classif["cnpj"])]

    avisar("Consultando a situação das parecidas na Receita")
    publicos = _publicos([c for c, _ in ranking]) if ranking else pd.DataFrame(columns=["cnpj", "nome_exibicao", "situacao", "data_situacao"])
    no_banco = set(publicos["cnpj"])
    ranking = [(c, s) for c, s in ranking if c in no_banco]
    ativos = set(publicos.loc[publicos["situacao"] == "02", "cnpj"])

    parecidas = classif.set_index("cnpj").loc[[c for c, _ in ranking]].reset_index().to_dict("records")
    try:
        vetores_publico = embeddings.carregar_atributo("publico")
    except RuntimeError:  # parquet de antes de 04/11/2026: o público é vetorizado na hora
        vetores_publico = {}
    marcas = lacunas.marcar_atendimento(recorte, parecidas, vetorizar, vetores={
        "publico": vetores_publico, "produto_servico": embeddings.carregar_servico()})
    avisar("Procurando o que ninguém atende")
    lista_lacunas, aviso = lacunas.calcular(recorte, marcas, ativos)
    concorrentes = _concorrentes(ranking, classif, publicos)
    avisar("Escrevendo o que é comum e o que pode diferenciar")
    texto_diferencial = diferencial.gerar(ideia, recorte, concorrentes, lista_lacunas)

    return {
        "ideia": ideia,
        "recorte": {"descricao": recorte.get("descricao", ""), "atributos": recorte["atributos"],
                    "uf": recorte.get("uf", config.UF_PILOTO)},
        "confianca": confianca.avaliar(n_setor, [p["confianca"] for p in parecidas], usou_setor_amplo=True,
                                       aviso_lacuna=aviso),
        "concorrentes": concorrentes,
        "saturacao": saturacao,
        "lacunas": lista_lacunas,
        "diferencial": texto_diferencial,
        "gerado_em": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = analisar(" ".join(sys.argv[1:]) or "escola de inglês online para adultos 40+")
    print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
