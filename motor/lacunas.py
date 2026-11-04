"""Concorrentes por similaridade e lacunas determinísticas (dono: Micael).

Lacuna = combinação dos atributos da ideia (público × serviço × canal, ou pares deles) que quase
nenhuma empresa parecida oferece. Regra do dados/config.yaml (Lucas): é lacuna quando no máximo
max(lacuna_max_abs, lacuna_max_pct × ativos analisados) oferecem, e só se aponta com pelo menos
limiar_recuo ativos analisados. Cada lacuna traz os CNPJs que a embasam.
"""
from __future__ import annotations

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


def marcar_atendimento(recorte: dict, empresas: list[dict], vetorizar) -> dict[str, dict]:
    """Para cada empresa, se atende cada atributo da ideia: True, False ou None (site não diz).

    Público e serviço são texto livre: comparados por similaridade de embeddings (>= ATENDE_MIN).
    """
    attrs = recorte["atributos"]
    textos = [attrs["publico"], attrs["produto_servico"]]
    textos += [e.get("publico_atendido") or "" for e in empresas]
    textos += [e.get("produto_servico") or "" for e in empresas]
    v = vetorizar(textos)
    n = len(empresas)
    v_pub, v_serv = v[0], v[1]
    sim_pub = v[2:2 + n] @ v_pub if n else []
    sim_serv = v[2 + n:2 + 2 * n] @ v_serv if n else []
    marcas = {}
    for i, e in enumerate(empresas):
        def julgar(campo, sim):
            valor = (e.get(campo) or "").strip()
            return None if valor in ("", "indeterminado") else bool(sim >= config.ATENDE_MIN)
        marcas[e["cnpj"]] = {
            "publico": julgar("publico_atendido", sim_pub[i]),
            "produto_servico": julgar("produto_servico", sim_serv[i]),
            "canal": atende_canal(attrs["canal"], e.get("canal_atendimento")),
        }
    return marcas


def _titulo(attrs: dict, combo: tuple[str, ...]) -> str:
    partes = [ROTULO[a].format(attrs[a]) for a in ("produto_servico", "canal", "publico") if a in combo]
    t = " · ".join(partes)
    return t[:1].upper() + t[1:]


def calcular(recorte: dict, marcas: dict[str, dict], ativos: set[str], params: dict | None = None) -> tuple[list[dict], str | None]:
    """Lacunas da ideia, a mais forte primeiro.

    Args:
        marcas: saída de marcar_atendimento, na ordem de semelhança.
        ativos: CNPJs em situação ativa (só elas contam como "oferecem hoje").
        params: max_abs, max_pct, minimo_nicho (padrão: dados/config.yaml).

    Returns:
        (lacunas no formato do contrato 4, aviso ou None). O aviso explica quando não há dado
        suficiente para apontar lacunas.
    """
    p = params or config.parametros_lacuna()
    attrs = {a: recorte["atributos"][a] for a in ATRIBUTOS}
    usados = [a for a in ATRIBUTOS if attrs[a] and attrs[a] != "indeterminado"]
    combos = [c for k in range(len(usados), 1, -1) for c in combinations(usados, k)]
    lacunas, maior_base = [], 0
    for combo in combos:
        base = [c for c, m in marcas.items() if c in ativos and all(m[a] is not None for a in combo)]
        maior_base = max(maior_base, len(base))
        if len(base) < p["minimo_nicho"]:
            continue
        oferecem = [c for c in base if all(marcas[c][a] for a in combo)]
        limite = max(p["max_abs"], p["max_pct"] * len(base))
        if len(oferecem) <= limite:
            lacunas.append({
                "titulo": _titulo(attrs, combo),
                "atributos": {a: attrs[a] for a in combo},
                "n_empresas_que_oferecem": len(oferecem),
                "n_empresas_analisadas": len(base),
                "cnpjs_base": base,
                "atendimento": {c: {a: marcas[c][a] for a in combo} for c in base},
            })
    lacunas.sort(key=lambda l: (l["n_empresas_que_oferecem"] / l["n_empresas_analisadas"], -len(l["atributos"])))
    aviso = None
    if maior_base < p["minimo_nicho"]:
        aviso = (f"Dados insuficientes para apontar lacunas: só {maior_base} empresas ativas parecidas têm "
                 f"site com essas informações (mínimo {p['minimo_nicho']}).")
    return lacunas, aviso
