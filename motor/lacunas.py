"""Concorrentes por similaridade e lacunas determinísticas (dono: Micael).

Lacuna = combinação dos atributos da ideia (público × serviço × canal, ou pares deles) que quase
nenhuma empresa parecida oferece. Regra do dados/config.yaml (Lucas): é lacuna quando no máximo
max(lacuna_max_abs, lacuna_max_pct × ativos analisados) oferecem, e só se aponta com pelo menos
limiar_recuo ativos analisados. Cada lacuna traz os CNPJs que a embasam.
"""
from __future__ import annotations

import re
from itertools import combinations

import numpy as np

from . import config

ATRIBUTOS = ("publico", "produto_servico", "canal")
COLUNA = {"publico": "publico_atendido", "produto_servico": "produto_servico", "canal": "canal_atendimento"}
ROTULO = {"publico": "para {}", "produto_servico": "{}", "canal": "{}"}


def ranquear(vetor_ideia: np.ndarray, cnpjs: list[str], matriz: np.ndarray,
             minimo: float = config.SEMELHANCA_MIN) -> list[tuple[str, float]]:
    """(cnpj, semelhança 0..1) das empresas acima de `minimo`, da mais parecida para a menos."""
    if len(cnpjs) == 0:
        return []
    sims = matriz @ vetor_ideia  # vetores já normalizados: produto interno = cosseno
    ordem = np.argsort(-sims)
    return [(cnpjs[i], round(float(max(0.0, sims[i])), 3)) for i in ordem if sims[i] >= minimo]


def filtrar_por_servico(vetor_servico: np.ndarray, ranking: list[tuple[str, float]],
                        vetores_servico: dict[str, np.ndarray],
                        minimo: float = config.SERVICO_MIN) -> list[tuple[str, float]]:
    """Mantém do ranking só as empresas do mesmo nicho: serviço com semelhança >= `minimo` ao da ideia.
    Quem não tem serviço conhecido sai (o site não diz o que vende)."""
    return [(c, s) for c, s in ranking
            if c in vetores_servico and float(vetores_servico[c] @ vetor_servico) >= minimo]


def atende_canal(canal_ideia: str, canal_empresa: str | None) -> bool | None:
    """Híbrido atende presencial e online. None = não dá para saber."""
    if not canal_empresa or canal_empresa == "indeterminado" or canal_ideia == "indeterminado":
        return None
    if canal_empresa == canal_ideia:
        return True
    return canal_empresa == "hibrido" and canal_ideia in ("presencial", "online")


def marcar_atendimento(recorte: dict, empresas: list[dict], vetorizar,
                       vetores: dict[str, dict[str, np.ndarray]] | None = None,
                       limiar_servico: float = config.ATENDE_MIN) -> dict[str, dict]:
    """Para cada empresa, se atende cada atributo da ideia: True, False ou None (site não diz).

    Público e serviço são texto livre: comparados por similaridade de embeddings (>= ATENDE_MIN).
    `vetores` ({"publico": {cnpj: vetor}, "produto_servico": {...}}, do embedding.parquet) evita
    vetorizar os textos das empresas ao vivo; quem não estiver lá é vetorizado na hora.
    `limiar_servico`: na base do mercado inteiro, "oferece o mesmo serviço" usa o corte de mesmo nicho
    (config.SERVICO_MIN), mais exigente que o ATENDE_MIN de dentro das parecidas.
    """
    attrs = recorte["atributos"]
    vetores = vetores or {}
    n = len(empresas)
    textos = [attrs["publico"], attrs["produto_servico"]]
    faltam = []  # (atributo, índice da empresa) a vetorizar agora
    for a, campo in (("publico", "publico_atendido"), ("produto_servico", "produto_servico")):
        for i, e in enumerate(empresas):
            if e["cnpj"] not in vetores.get(a, {}):
                faltam.append((a, i))
                textos.append(e.get(campo) or "")
    v = vetorizar(textos)
    v_pub, v_serv = v[0], v[1]
    emp = {a: [vetores.get(a, {}).get(e["cnpj"]) for e in empresas] for a in ("publico", "produto_servico")}
    for k, (a, i) in enumerate(faltam):
        emp[a][i] = v[2 + k]
    sim_pub = np.array([x @ v_pub for x in emp["publico"]]) if n else []
    sim_serv = np.array([x @ v_serv for x in emp["produto_servico"]]) if n else []
    marcas = {}
    for i, e in enumerate(empresas):
        def julgar(campo, sim, limiar=config.ATENDE_MIN):
            valor = (e.get(campo) or "").strip()
            return None if valor in ("", "indeterminado") else bool(sim >= limiar)
        marcas[e["cnpj"]] = {
            "publico": julgar("publico_atendido", sim_pub[i]),
            "produto_servico": julgar("produto_servico", sim_serv[i], limiar_servico),
            "canal": atende_canal(attrs["canal"], e.get("canal_atendimento")),
        }
    return marcas


def _titulo(attrs: dict, combo: tuple[str, ...]) -> str:
    partes = [ROTULO[a].format(attrs[a]) for a in ("produto_servico", "canal", "publico") if a in combo]
    t = " · ".join(partes)
    return t[:1].upper() + t[1:]


_VAGO = re.compile(r"n[aã]o (especificad|informad|definid)|indetermin|^geral$|^qualquer|^todos?$", re.I)
SOZINHOS = ("produto_servico", "publico")  # atributos que valem como lacuna sozinhos (canal sozinho não diz nada)


def calcular(recorte: dict, marcas: dict[str, dict], ativos: set[str], params: dict | None = None,
             origem: str = "ideia", titulo: str | None = None, so_completa: bool = False) -> tuple[list[dict], str | None]:
    """Lacunas da ideia, a mais forte primeiro.

    Args:
        marcas: saída de marcar_atendimento sobre a base (todas as escolas ativas com site do recorte).
        ativos: CNPJs em situação ativa (só elas contam como "oferecem hoje").
        params: max_abs, max_pct, minimo_nicho (padrão: config.parametros_lacuna()).
        origem: "ideia" ou "variacao" (variação proposta pelo LLM, ver motor/variacoes.py).
        titulo: título fixo (o da variação); sem ele, o título sai dos atributos.
        so_completa: só a combinação com todos os atributos (usado nas variações).

    Returns:
        (lacunas no formato do contrato 4, aviso ou None). O aviso explica quando não há dado
        suficiente para apontar lacunas.
    """
    p = params or config.parametros_lacuna()
    attrs = {a: recorte["atributos"][a] for a in ATRIBUTOS}
    # "público não especificado" não é um público: fica de fora como "indeterminado"
    usados = [a for a in ATRIBUTOS if attrs[a] and not _VAGO.search(str(attrs[a]).strip())]
    combos = [c for k in range(len(usados), 1, -1) for c in combinations(usados, k)]
    combos += [(a,) for a in usados if a in SOZINHOS]
    minimo = p.get("minimo_lacuna", p["minimo_nicho"])
    if so_completa:
        combos = combos[:1] if usados else []
    lacunas, maior_base = [], 0
    for combo in combos:
        base = [c for c, m in marcas.items() if c in ativos and all(m[a] is not None for a in combo)]
        maior_base = max(maior_base, len(base))
        if len(base) < minimo:
            continue
        oferecem = [c for c in base if all(marcas[c][a] for a in combo)]
        limite = max(p["max_abs"], p["max_pct"] * len(base))
        if len(oferecem) <= limite:
            lacunas.append({
                "titulo": titulo or _titulo(attrs, combo),
                "origem": origem,
                "atributos": {a: attrs[a] for a in combo},
                "n_empresas_que_oferecem": len(oferecem),
                "n_empresas_analisadas": len(base),
                "base_pequena": len(base) < p["minimo_nicho"],  # aponta, mas avisa na tela
                "cnpjs_base": base,
                "atendimento": {c: {a: marcas[c][a] for a in combo} for c in base},
            })
    lacunas.sort(key=lambda l: (l["n_empresas_que_oferecem"] / l["n_empresas_analisadas"], -len(l["atributos"])))
    aviso = None
    if maior_base < minimo:
        aviso = (f"Dados insuficientes para apontar lacunas: só {maior_base} escolas ativas do setor têm "
                 f"site com essas informações (mínimo {minimo}).")
    return lacunas, aviso
