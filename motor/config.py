"""Caminhos e parâmetros do motor (dono: Micael).

Parâmetros de lacuna e de recuo vêm do dados/config.yaml (decididos pelo Lucas, ver
dados/decisoes/DECISOES.md). Os demais são do motor e estão marcados como provisórios.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

PASTA_MOTOR = RAIZ / "motor"
PASTA_PROMPTS = PASTA_MOTOR / "prompts"
CACHE = PASTA_MOTOR / "cache"  # fora do Git (.gitignore). construir_db apaga as tabelas do banco, isto não.

# Entrada: CSV exportado pelo Roger (enriquecimento/exportar_textos.py)
TEXTOS_SITES = RAIZ / "enriquecimento" / "cache" / "textos_sites.csv"
# Saídas do motor
CLASSIFICACAO_JSONL = CACHE / "classificacao.jsonl"  # uma linha por chamada, retomável
EMBEDDING_PARQUET = CACHE / "embedding.parquet"

MODELO_CLASSIFICACAO = os.getenv("LLM_MODELO_CLASSIFICACAO", "gemini-3.5-flash-lite")
# Ordem tentada nas chamadas ao vivo (tela 2 e diferencial). Em 03/11/2026: 3.8-flash deu 504 em 3 de 3
# chamadas e 503 antes; 3.6-flash respondeu em 4 a 23 s; os dois Flash-Lite, em menos de 2 s.
MODELOS_AO_VIVO = [m.strip() for m in os.getenv(
    "LLM_MODELOS_AO_VIVO", "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.6-flash").split(",") if m.strip()]
TENTATIVAS_AO_VIVO = 2   # por modelo: o usuário está esperando na tela
TIMEOUT_AO_VIVO_S = 15   # desiste da chamada e passa para o próximo modelo
TIMEOUT_LOTE_S = 60      # classificação em massa (antes da demo)

# Multilíngue, 384 dimensões (contrato 1: FLOAT[384]); roda local, não gasta cota
MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

UF_PILOTO = "RJ"
CNAES_PILOTO = {
    "8593700": "Ensino de idiomas",
    "8599604": "Treinamento em desenvolvimento profissional e gerencial",
    "8599699": "Outras atividades de ensino não especificadas anteriormente",
    "8599603": "Treinamento em informática",
    "8599605": "Cursos preparatórios para concursos",
}

# Provisórios do motor (calibrar com dado real)
MAX_CHARS_TEXTO = 8000          # texto do site enviado ao LLM por empresa
SEMELHANCA_MIN = 0.35           # abaixo disso a empresa não entra como "parecida"
MAX_CONCORRENTES = 10
ATENDE_MIN = 0.45               # similaridade mínima para dizer que uma empresa atende um atributo


def _config_dados() -> dict:
    with open(RAIZ / "dados" / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["consultas"]


def parametros_lacuna() -> dict:
    """lacuna_max_abs, lacuna_max_pct e limiar_recuo, do dados/config.yaml."""
    c = _config_dados()
    return {"max_abs": int(c["lacuna_max_abs"]), "max_pct": float(c["lacuna_max_pct"]),
            "minimo_nicho": int(c["limiar_recuo"])}


def periodo() -> tuple[int, int]:
    ini, fim = _config_dados()["periodo"]
    return int(ini), int(fim)
