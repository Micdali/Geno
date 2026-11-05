"""Ponto de entrada do motor de análise (dono: Micael).

A assinatura de `analisar` faz parte do contrato 4 (contratos/04_resultado_analise.md).

Precisa de: dados/geno.duckdb (Lucas), motor/cache/classificacao.jsonl (python -m motor.classificar)
e motor/cache/embedding.parquet (python -m motor.embeddings). Chama o LLM ao vivo para propor o
recorte (se não vier pronto da tela 2) e para o diferencial.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
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


# Nomes curtos dos nichos do piloto, para os gráficos e a leitura comparada
NOME_NICHO = {"8593700": "Idiomas", "8599603": "Informática", "8599605": "Concursos",
              "8599604": "Treinamento gerencial", "8599699": "Outros cursos livres"}


@lru_cache(maxsize=1)
def _comparativo_nichos() -> tuple[dict, ...]:
    """Aberturas, baixas (sem as de ofício) e razão baixas/aberturas de cada nicho do piloto no período.

    Não depende da ideia: calculado uma vez por processo. Os 5 nichos estão inteiros no banco do Lucas,
    então a comparação é justa (outros setores só aparecem lá quando têm ensino como atividade secundária).
    """
    linhas = []
    for cnae in config.CNAES_PILOTO:
        df = _saturacao([cnae])
        ab, bx = int(df["aberturas"].sum()), int((df["baixas"] - df["baixas_oficio"]).sum())
        linhas.append({"cnae": cnae, "nome": NOME_NICHO.get(cnae, cnae), "aberturas": ab, "baixas": bx,
                       "razao": round(bx / ab, 3) if ab else 0.0})
    return tuple(sorted(linhas, key=lambda l: -l["razao"]))


def _contexto_setor(cnaes: list[str]) -> dict:
    """Dados para os gráficos extras da tela de saturação, só com estabelecimentos dos CNAEs do recorte.

    sobrevivencia: % ainda ativos por ano de abertura; municipios: os 5 com mais ativos;
    porte: ativos que são MEI ou não (vw_publico.opcao_mei).
    """
    from dados.geno_db import consultas
    con = consultas.conectar()
    alvo = "cnae_principal IN (SELECT unnest(?::VARCHAR[]))"
    try:
        sobrevivencia = con.execute(
            f"SELECT year(data_inicio) AS ano, count(*) AS abertos, "
            f"count(*) FILTER (WHERE situacao = '02') AS ativos FROM vw_publico "
            f"WHERE {alvo} AND year(data_inicio) BETWEEN ? AND ? GROUP BY 1 ORDER BY 1",
            [list(cnaes), ANO_SOBREVIVENCIA, config.periodo()[1]]).fetchall()
        municipios = con.execute(
            f"SELECT municipio, count(*) FROM vw_publico WHERE {alvo} AND situacao = '02' "
            f"GROUP BY 1 ORDER BY 2 DESC LIMIT 5", [list(cnaes)]).fetchall()
        mei = con.execute(
            f"SELECT count(*) FILTER (WHERE opcao_mei = 'S'), count(*) FROM vw_publico "
            f"WHERE {alvo} AND situacao = '02'", [list(cnaes)]).fetchall()[0]
    finally:
        con.close()
    return {
        "sobrevivencia": [{"ano": int(a), "abertos": int(n), "pct_ativos": round(100 * at / n, 1)}
                          for a, n, at in sobrevivencia if n],
        "municipios": [{"municipio": nome_municipio(m), "ativos": int(n)} for m, n in municipios],
        "porte": {"mei": int(mei[0]), "total": int(mei[1])},
    }


ANO_SOBREVIVENCIA = 2015  # primeiro ano de abertura do gráfico de sobrevivência

# A Receita grava os municípios em maiúsculas e sem acento; os mais comuns do RJ, escritos direito
_MUNICIPIOS = {"NITEROI": "Niterói", "PETROPOLIS": "Petrópolis", "NOVA IGUACU": "Nova Iguaçu",
               "SAO GONCALO": "São Gonçalo", "SAO JOAO DE MERITI": "São João de Meriti", "MARICA": "Maricá",
               "ITABORAI": "Itaboraí", "TERESOPOLIS": "Teresópolis", "MACAE": "Macaé", "MAGE": "Magé",
               "NILOPOLIS": "Nilópolis", "ITAGUAI": "Itaguaí", "SEROPEDICA": "Seropédica",
               "CAMPOS DOS GOYTACAZES": "Campos dos Goytacazes", "SAO PEDRO DA ALDEIA": "São Pedro da Aldeia"}


def nome_municipio(nome: str | None) -> str:
    """'RIO DE JANEIRO' -> 'Rio de Janeiro'; 'NITEROI' -> 'Niterói'."""
    nome = (nome or "").strip().upper()
    if nome in _MUNICIPIOS:
        return _MUNICIPIOS[nome]
    return " ".join(p.lower() if p.lower() in ("de", "da", "do", "das", "dos", "e") else p.capitalize()
                    for p in nome.split())


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


def interpretar_saturacao(bloco: dict, n_setor: int, comparativo: list[dict] | None = None,
                          cnaes: list[str] | None = None) -> dict:
    """O que os números de aberturas e baixas querem dizer na prática, em linguagem simples.

    Regras fixas sobre os dados (sem LLM, para não inventar): razão baixas/aberturas, saldo, a
    tendência do primeiro ao último ano e, com `comparativo`, a posição do nicho entre os nichos de
    ensino do piloto. Nunca diz para abrir ou não abrir.

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
    comparacao = _frase_comparativa(razao, comparativo, cnaes) if comparativo else None
    return {"titulo": titulo, "paragrafos": [p for p in [comparacao] if p] + [
        f"De {a0} a {a1}, abriram {_num(total_ab)} estabelecimentos e {_num(total_bx)} deram baixa no CNPJ: "
        f"para cada 10 que abriram, cerca de {por_10} fecharam. O saldo foi de {'+' if saldo > 0 else '-'}"
        f"{_num(abs(saldo))} e hoje o setor tem {_num(n_setor)} estabelecimentos ativos no {config.UF_PILOTO}.",
        tendencia,
        pratica,
    ]}


def _frase_comparativa(razao: float, comparativo: list[dict], cnaes: list[str] | None) -> str | None:
    """Como o recorte se compara aos outros nichos de ensino: a frase que abre a leitura da saturação."""
    outros = [c for c in comparativo if c["cnae"] not in (cnaes or [])]
    if not outros:
        return None
    ab, bx = sum(c["aberturas"] for c in comparativo), sum(c["baixas"] for c in comparativo)
    media = bx / ab if ab else 0
    acima = sum(c["razao"] > razao for c in outros)
    nomes = [NOME_NICHO.get(c, c) for c in (cnaes or [])]
    nome = (f"o nicho de {nomes[0]}" if len(nomes) == 1 else f"os nichos de {' e '.join(nomes)}") if nomes else "o seu nicho"
    plural = len(nomes) > 1
    v = lambda r: f"{r * 10:.1f}".replace(".", ",")  # noqa: E731
    verbo = "fecham" if plural else "fecha"
    if razao > media * 1.05:
        lado = f"{verbo} mais negócios do que a média do ensino livre"
    elif razao < media * 0.95:
        lado = f"{verbo} menos negócios do que a média do ensino livre"
    else:
        lado = f"{verbo} negócios no mesmo ritmo da média do ensino livre"
    posicao = ("a maior taxa de fechamento" if acima == 0 else "a menor taxa de fechamento" if acima == len(outros)
               else f"a {acima + 1}ª maior taxa de fechamento")
    return (f"Comparado aos outros nichos de ensino do RJ, {nome} {lado}: {v(razao)} baixas a cada 10 "
            f"aberturas, contra {v(media)} na média dos {len(comparativo)} nichos. É {posicao} entre eles.")


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
    comparativo = list(_comparativo_nichos())
    saturacao["comparativo"] = comparativo
    saturacao.update(_contexto_setor(cnaes))
    saturacao["interpretacao"] = interpretar_saturacao(saturacao, n_setor, comparativo, cnaes)

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
