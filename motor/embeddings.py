"""Embeddings locais (sentence-transformers, 384 dimensões) das empresas classificadas (dono: Micael).

Uso:
    python -m motor.embeddings      # gera motor/cache/embedding.parquet a partir da classificação

O vetor de cada empresa vem do texto da classificação (nicho, serviço, público, canal), não do site
bruto: assim a busca compara "o que a empresa faz" com "o que a ideia quer fazer". Um segundo vetor,
só do `produto_servico`, decide se a empresa é do mesmo nicho (config.SERVICO_MIN); ele e o vetor do
`publico_atendido` também servem às lacunas, para que a análise ao vivo só vetorize os textos da ideia.
Só recalcula quando o texto de origem muda.
"""
from __future__ import annotations

import sys
import threading

import numpy as np
import pandas as pd

from . import config


_MODELO = None
_TRAVA = threading.Lock()


def _modelo():
    """Carrega o modelo uma vez por processo (a trava evita carregar duas vezes em threads diferentes)."""
    global _MODELO
    with _TRAVA:
        if _MODELO is None:
            import torch
            from sentence_transformers import SentenceTransformer
            torch.set_num_threads(config.EMBEDDING_THREADS)
            _MODELO = SentenceTransformer(config.MODELO_EMBEDDING)
    return _MODELO


def aquecer() -> None:
    """Começa a carregar o modelo em segundo plano (leva de 15 a 30 s na primeira vez).

    O nicho.propor_recorte chama isto na tela 1: enquanto a pessoa confere o recorte na tela 2,
    o modelo carrega, e a análise da tela 3 não espera por ele.
    """
    if _MODELO is None:
        threading.Thread(target=_modelo, name="aquecer-embeddings", daemon=True).start()


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


# Vetores extras por atributo: sufixo da coluna -> campo da classificação
ATRIBUTOS = {"servico": "produto_servico", "publico": "publico_atendido"}


def gerar(classificacao: pd.DataFrame, destino=config.EMBEDDING_PARQUET) -> pd.DataFrame:
    """Calcula (ou reaproveita) os embeddings e grava em `destino`."""
    registros = classificacao.to_dict("records")
    novos = pd.DataFrame({"cnpj": classificacao["cnpj"].astype(str),
                          "texto_origem": [texto_origem(c) for c in registros],
                          **{f"texto_{s}": [_limpo(c.get(campo)) for c in registros] for s, campo in ATRIBUTOS.items()}})
    novos = novos[novos["texto_origem"] != ""]
    antigos = pd.read_parquet(destino) if destino.exists() else pd.DataFrame(columns=["cnpj", "texto_origem", "vetor"])
    antigos = antigos[antigos["modelo"] == config.MODELO_EMBEDDING] if "modelo" in antigos else antigos.iloc[0:0]
    junto = novos.merge(antigos[["cnpj", "texto_origem", "vetor"]], on=["cnpj", "texto_origem"], how="left")
    for s in ATRIBUTOS:
        if f"vetor_{s}" in antigos:
            junto = junto.merge(antigos[["cnpj", f"texto_{s}", f"vetor_{s}"]], on=["cnpj", f"texto_{s}"], how="left")
        else:
            junto[f"vetor_{s}"] = None
    faltam = junto["vetor"].isna()
    if faltam.any():
        vetores = vetorizar(junto.loc[faltam, "texto_origem"].tolist())
        junto.loc[faltam, "vetor"] = pd.Series(list(vetores), index=junto.index[faltam])
    for s in ATRIBUTOS:
        falta = junto[f"vetor_{s}"].isna() & (junto[f"texto_{s}"] != "")
        if falta.any():
            vetores = vetorizar(junto.loc[falta, f"texto_{s}"].tolist())
            junto.loc[falta, f"vetor_{s}"] = pd.Series(list(vetores), index=junto.index[falta])
    junto["modelo"] = config.MODELO_EMBEDDING
    destino.parent.mkdir(parents=True, exist_ok=True)
    colunas = ["cnpj", "modelo", "texto_origem", "vetor"] + [f"{t}_{s}" for s in ATRIBUTOS for t in ("texto", "vetor")]
    junto[colunas].to_parquet(destino, index=False)
    print(f"[embeddings] {len(junto)} empresas ({int(faltam.sum())} novas) -> {destino}")
    return junto


def carregar(caminho=config.EMBEDDING_PARQUET) -> tuple[list[str], np.ndarray]:
    """(cnpjs, matriz n x 384). Vazio se ainda não houver embeddings."""
    if not caminho.exists():
        return [], np.zeros((0, 384), dtype=np.float32)
    df = pd.read_parquet(caminho)
    return df["cnpj"].astype(str).tolist(), np.vstack(df["vetor"].to_numpy()).astype(np.float32)


def carregar_atributo(sufixo: str, caminho=config.EMBEDDING_PARQUET) -> dict[str, np.ndarray]:
    """{cnpj: vetor do atributo} ("servico" ou "publico"). Quem tem o campo "indeterminado" fica de fora."""
    if not caminho.exists():
        return {}
    df = pd.read_parquet(caminho)
    if f"vetor_{sufixo}" not in df:
        raise RuntimeError(f"embedding.parquet sem vetor_{sufixo}: rode python -m motor.embeddings")
    df = df[df[f"vetor_{sufixo}"].notna()]
    return {c: np.asarray(v, dtype=np.float32) for c, v in zip(df["cnpj"].astype(str), df[f"vetor_{sufixo}"])}


def carregar_servico(caminho=config.EMBEDDING_PARQUET) -> dict[str, np.ndarray]:
    """{cnpj: vetor do produto_servico}. Empresas com serviço "indeterminado" ficam de fora."""
    return carregar_atributo("servico", caminho)


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
