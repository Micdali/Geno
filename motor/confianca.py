"""Indicador de confiança da análise: alta, média ou baixa (dono: Micael).

Regra provisória (decisão do motor, calibrar com dado real):
  alta  = pelo menos `limiar_recuo` (50) empresas parecidas classificadas e >= 70% delas com confiança
          do LLM alta ou média;
  media = pelo menos 20 parecidas;
  baixa = o resto. Cai um nível se mais da metade das parecidas tiver confiança do LLM baixa.
"""
from __future__ import annotations

from . import config

NIVEIS = ["baixa", "media", "alta"]
MINIMO_MEDIA = 20


def avaliar(n_setor: int, confiancas_llm: list[str], usou_setor_amplo: bool, aviso_lacuna: str | None = None) -> dict:
    """Monta o bloco `confianca` do contrato 4.

    Args:
        n_setor: estabelecimentos ativos do setor (CNAE) no recorte geográfico.
        confiancas_llm: confiança da classificação de cada empresa parecida.
        usou_setor_amplo: a saturação foi calculada no setor (CNAE), não no nicho.
    """
    n = len(confiancas_llm)
    boas = sum(c in ("alta", "media") for c in confiancas_llm)
    baixas = n - boas
    if n >= config.parametros_lacuna()["minimo_nicho"] and boas >= 0.7 * n:
        nivel = "alta"
    elif n >= MINIMO_MEDIA:
        nivel = "media"
    else:
        nivel = "baixa"
    if n and baixas > n / 2 and nivel != "baixa":
        nivel = NIVEIS[NIVEIS.index(nivel) - 1]

    rotulo = {"alta": "Confiança alta", "media": "Confiança média", "baixa": "Confiança baixa"}[nivel]
    n_setor_txt = f"{n_setor:,}".replace(",", ".")  # 20.881, separador de milhar brasileiro
    texto = (f"{rotulo}: analisamos o site de {n} empresas parecidas com a sua ideia, de "
             f"{n_setor_txt} estabelecimentos ativos do setor no {config.UF_PILOTO}. "
             "Empresas sem site podem oferecer algo parecido.")
    if usou_setor_amplo:
        texto += " Aberturas e fechamentos são do setor inteiro (CNAE), não só do nicho."
    if aviso_lacuna:
        texto += " " + aviso_lacuna
    return {"nivel": nivel, "n_empresas": int(n_setor), "n_com_site_classificado": n,
            "usou_setor_amplo": bool(usou_setor_amplo), "texto": texto}
