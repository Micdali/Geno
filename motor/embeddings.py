"""Embeddings locais (sentence-transformers, 384 dimensões) das empresas classificadas (dono: Micael).

Uso:
    python -m motor.embeddings      # gera motor/cache/embedding.parquet a partir da classificação

O vetor de cada empresa vem do texto da classificação (nicho, serviço, público, canal), não do site
bruto: assim a busca compara "o que a empresa faz" com "o que a ideia quer fazer".
Só recalcula quando o texto de origem muda.
"""
from __future__ import annotations

import sys
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config


@lru_cache(maxsize=1)
def _modelo():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.MODELO_EMBEDDING)


def vetorizar(textos: list[str]) -> np.ndarray:
    """Vetores normalizados (norma 1), shape (n, 384)."""
    if not textos:
        return np.zeros((0, 384), dtype=np.float32)
    return _modelo().encode(textos, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)


def _limpo(valor) -> str:
    v = "" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else str(valor).strip()
    return "" if v == "indeterminado" else v


def texto_origem(c: dict) -> str:
    """Texto que representa a empresa na busca. Campos 'indeterminado' ficam de fora."""
    partes = [_limpo(c.get("descricao_nicho")), _limpo(c.get("produto_servico"))]
    if p := _limpo(c.get("publico_atendido")):
        partes.append(f"para {p}")
    if canal := _limpo(c.get("canal_atendimento")):
        partes.append(f"atendimento {canal}")
    return "; ".join(p for p in partes if p)


def gerar(classificacao: pd.DataFrame, destino=config.EMBEDDING_PARQUET) -> pd.DataFrame:
    """Calcula (ou reaproveita) os embeddings e grava em `destino`."""
    novos = pd.DataFrame({"cnpj": classificacao["cnpj"].astype(str),
                          "texto_origem": [texto_origem(c) for c in classificacao.to_dict("records")]})
    novos = novos[novos["texto_origem"] != ""]
    antigos = pd.read_parquet(destino) if destino.exists() else pd.DataFrame(columns=["cnpj", "texto_origem", "vetor"])
    antigos = antigos[antigos["modelo"] == config.MODELO_EMBEDDING] if "modelo" in antigos else antigos.iloc[0:0]
    junto = novos.merge(antigos[["cnpj", "texto_origem", "vetor"]], on=["cnpj", "texto_origem"], how="left")
    faltam = junto["vetor"].isna()
    if faltam.any():
        vetores = vetorizar(junto.loc[faltam, "texto_origem"].tolist())
        junto.loc[faltam, "vetor"] = pd.Series(list(vetores), index=junto.index[faltam])
    junto["modelo"] = config.MODELO_EMBEDDING
    destino.parent.mkdir(parents=True, exist_ok=True)
    junto[["cnpj", "modelo", "texto_origem", "vetor"]].to_parquet(destino, index=False)
    print(f"[embeddings] {len(junto)} empresas ({int(faltam.sum())} novas) -> {destino}")
    return junto


def carregar(caminho=config.EMBEDDING_PARQUET) -> tuple[list[str], np.ndarray]:
    """(cnpjs, matriz n x 384). Vazio se ainda não houver embeddings."""
    if not caminho.exists():
        return [], np.zeros((0, 384), dtype=np.float32)
    df = pd.read_parquet(caminho)
    return df["cnpj"].astype(str).tolist(), np.vstack(df["vetor"].to_numpy()).astype(np.float32)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from . import classificar
    c = classificar.carregar()
    if c.empty:
        print("[embeddings] nenhuma classificação ainda. Rode: python -m motor.classificar")
        return 1
    gerar(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
