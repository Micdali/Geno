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

# "openai" (chave paga, desde 03/11/2026) ou "gemini" (reserva; plano gratuito, 15 chamadas por minuto)
LLM_PROVEDOR = (os.getenv("LLM_PROVEDOR") or "openai").strip().lower()
# Padrões por provedor; LLM_MODELO_CLASSIFICACAO e LLM_MODELOS_AO_VIVO no .env têm prioridade.
_PADROES = {
    # gpt-6-luna: o modelo de alto volume da OpenAI ($0,10/$0,50 por 1M tokens em 03/11/2026).
    # Os dois de reserva também aceitam schema estrito e effort "none" (testado em 03/11/2026).
    "openai": ("gpt-6-luna", "gpt-6-luna,gpt-5.6-luna,gpt-5.4-nano"),
    # Em 03/11/2026: 3.8-flash deu 504 em 3 de 3 chamadas e 503 antes; 3.6-flash respondeu em 4 a 23 s;
    # os dois Flash-Lite, em menos de 2 s.
    "gemini": ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.6-flash"),
}
if LLM_PROVEDOR not in _PADROES:
    raise ValueError(f"LLM_PROVEDOR inválido: {LLM_PROVEDOR!r} (use 'openai' ou 'gemini')")
MODELO_CLASSIFICACAO = os.getenv("LLM_MODELO_CLASSIFICACAO") or _PADROES[LLM_PROVEDOR][0]
# Ordem tentada nas chamadas ao vivo (tela 2 e diferencial)
MODELOS_AO_VIVO = [m.strip() for m in (os.getenv("LLM_MODELOS_AO_VIVO") or _PADROES[LLM_PROVEDOR][1]).split(",")
                   if m.strip()]
# Esforço de raciocínio nos modelos da OpenAI: "none" é o mais rápido e o indicado para classificar.
OPENAI_ESFORCO = os.getenv("OPENAI_ESFORCO", "none").strip()
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
SEMELHANCA_MIN = 0.35           # texto inteiro (nicho, serviço, público, canal): primeiro corte e ordem
# Mesmo nicho = o serviço da empresa parecido com o da ideia. Calibrado em 04/11/2026 com 602 escolas e
# 8 ideias de teste (motor/README.md): com 0,35 no texto inteiro passavam de 34% a 94% das escolas para
# qualquer ideia; com o serviço >= 0,60 ficam as do nicho (inglês 71, espanhol 30, Excel 6).
SERVICO_MIN = 0.60
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
