"""Classificação das empresas pelo LLM a partir do texto dos sites (dono: Micael).

Uso:
    python -m motor.classificar                       # lê enriquecimento/cache/textos_sites.csv
    python -m motor.classificar caminho.csv --limite 10 --workers 4 --rpm 14

- Saída: motor/cache/classificacao.jsonl, uma linha por empresa no formato do contrato 3
  (mais `hash_texto`, para saber se o texto mudou).
- Retomável: rodar de novo pula quem já foi classificado com o mesmo prompt, o mesmo texto e o
  mesmo modelo (trocar de modelo reclassifica tudo).
- Só texto público de site vai para o LLM, mais a descrição do CNAE (nunca nome, sócio ou contato).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd

from . import config, llm

PROMPT_VERSAO = "v3"
ORDEM_TIPOS = {"home": 0, "sobre": 1, "precos": 2, "arquivada": 3}
# Quando um CNPJ tem vários sites, fica o do método mais confiável (o e-mail cadastrado
# na Receita muitas vezes é o domínio do contador). Métodos fora da lista vêm por último.
ORDEM_METODOS = {"manual": 0, "rodape_cnpj": 1, "nome_titulo": 2, "email": 3}
CANAIS = ["presencial", "online", "delivery", "hibrido", "indeterminado"]
RECEITAS = ["assinatura", "venda_avulsa", "pacote_ou_mensalidade", "comissao_ou_marketplace",
            "publicidade", "outro", "indeterminado"]
CAMPOS_TEXTO = ["publico_atendido", "produto_servico", "problema_resolvido", "posicionamento",
                "descricao_nicho"]

# Só os campos que o LLM preenche (contrato 3); cnpj, versão, fonte, modelo e data vêm do código.
SCHEMA = {
    "type": "object",
    "properties": {
        **{c: {"type": "string"} for c in CAMPOS_TEXTO},
        "canal_atendimento": {"type": "string", "enum": CANAIS},
        "modelo_receita": {"type": "string", "enum": RECEITAS},
        "confianca": {"type": "string", "enum": ["alta", "media", "baixa"]},
        "site_de_ensino": {"type": "boolean"},
    },
    "required": ["site_de_ensino"] + CAMPOS_TEXTO + ["canal_atendimento", "modelo_receita", "confianca"],
}


def _prompt_modelo() -> str:
    return (config.PASTA_PROMPTS / f"classificacao_{PROMPT_VERSAO}.md").read_text(encoding="utf-8")


def textos_por_empresa(textos: pd.DataFrame) -> pd.DataFrame:
    """Junta as páginas úteis de um único site por CNPJ num texto só.

    Descarta páginas bloqueadas, sem CNPJ, sem texto ou com status HTTP fora de 2xx.
    Com mais de um site, escolhe pelo método (ORDEM_METODOS) e, no empate, o de mais texto;
    textos de sites diferentes nunca se misturam.
    Retorna colunas: cnpj, site, metodo, fonte, texto, hash_texto.
    """
    t = textos.copy()
    t["cnpj"] = t["cnpj"].astype("string").str.strip()
    status = pd.to_numeric(t["status_http"], errors="coerce")
    bloqueado = t["bloqueado"].astype(str).str.lower().isin(["true", "1"])
    ok = t["cnpj"].notna() & (t["cnpj"] != "") & ~bloqueado & status.between(200, 299) \
        & t["texto"].fillna("").str.strip().ne("")
    t = t[ok].assign(_ordem=lambda d: d["tipo"].map(ORDEM_TIPOS).fillna(9))
    if "metodo" not in t:
        t["metodo"] = None
    sites = (t.assign(_n=t["texto"].str.len())
             .groupby(["cnpj", "site"], as_index=False).agg(metodo=("metodo", "first"), _n=("_n", "sum")))
    sites["_m"] = sites["metodo"].map(ORDEM_METODOS).fillna(9)
    escolhidos = sites.sort_values(["cnpj", "_m", "_n"], ascending=[True, True, False]).drop_duplicates("cnpj")
    t = t.merge(escolhidos[["cnpj", "site"]], on=["cnpj", "site"])
    linhas = []
    for cnpj, g in t.sort_values(["cnpj", "_ordem"]).groupby("cnpj", sort=True):
        partes = [f"[{r.tipo}] {r.texto.strip()}" for r in g.itertuples()]
        texto = "\n\n".join(partes)[: config.MAX_CHARS_TEXTO]
        fonte = "site_arquivado" if set(g["tipo"]) == {"arquivada"} else "site"
        h = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]
        linhas.append({"cnpj": cnpj, "site": g["site"].iloc[0], "metodo": g["metodo"].iloc[0], "fonte": fonte,
                       "texto": texto, "hash_texto": h})
    return pd.DataFrame(linhas, columns=["cnpj", "site", "metodo", "fonte", "texto", "hash_texto"])


def ja_classificados(caminho=config.CLASSIFICACAO_JSONL) -> set[tuple[str, str, str, str]]:
    """(cnpj, prompt_versao, hash_texto, modelo_llm) já gravados."""
    if not caminho.exists():
        return set()
    feitos = set()
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            if linha.strip():
                r = json.loads(linha)
                feitos.add((r["cnpj"], r["prompt_versao"], r["hash_texto"], r.get("modelo_llm")))
    return feitos


def classificar_um(empresa: dict, cnae: str | None = None, gerar=None) -> dict:
    """Classifica uma empresa. `gerar` é injetável para testes."""
    prompt = _prompt_modelo().format(cnae=cnae or "não informado", texto=empresa["texto"])
    saida, modelo = (gerar or llm.gerar_json)(prompt, SCHEMA, [config.MODELO_CLASSIFICACAO], temperatura=0.0,
                                                   timeout_s=config.TIMEOUT_LOTE_S)
    for c in CAMPOS_TEXTO:
        saida[c] = (saida.get(c) or "indeterminado").strip() or "indeterminado"
    if saida.get("site_de_ensino") is False:  # contador, advogado, provedor, "em construção"...
        saida.update({c: "indeterminado" for c in CAMPOS_TEXTO + ["canal_atendimento", "modelo_receita"]},
                     confianca="baixa")
    return {
        "cnpj": empresa["cnpj"],
        "prompt_versao": PROMPT_VERSAO,
        "fonte": empresa["fonte"],
        **{k: saida.get(k) for k in SCHEMA["properties"]},
        "modelo_llm": modelo,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hash_texto": empresa["hash_texto"],
        "site": empresa["site"],
        "metodo": empresa.get("metodo"),
    }


def carregar(caminho=config.CLASSIFICACAO_JSONL, prompt_versao: str = PROMPT_VERSAO,
             modelo: str | None = None) -> pd.DataFrame:
    """Classificação vigente: a última linha de cada CNPJ na versão de prompt pedida (e no modelo, se dado)."""
    if not caminho.exists():
        return pd.DataFrame(columns=["cnpj", *SCHEMA["properties"], "fonte", "site"])
    df = pd.read_json(caminho, lines=True, dtype={"cnpj": str})
    df = df[df["prompt_versao"] == prompt_versao]
    if modelo:
        df = df[df["modelo_llm"] == modelo]
    return df.drop_duplicates("cnpj", keep="last").reset_index(drop=True)


def _cnaes(cnpjs: list[str]) -> dict[str, str]:
    """Descrição do CNAE principal pela vw_publico; vazio se o banco não existir."""
    try:
        from dados import consultas
        df = consultas.dados_publicos(cnpjs)
    except Exception:
        return {}
    return {r.cnpj: r.cnae_descricao for r in df.itertuples() if getattr(r, "cnae_descricao", None)}


class _Ritmo:
    """No máximo `rpm` chamadas por minuto, somando todas as threads (None = sem limite)."""

    def __init__(self, rpm: int | None):
        self.intervalo = 60.0 / rpm if rpm else 0.0
        self.proxima = 0.0
        self.trava = threading.Lock()

    def esperar(self) -> None:
        with self.trava:
            agora = time.monotonic()
            vez, self.proxima = max(agora, self.proxima), max(agora, self.proxima) + self.intervalo
        time.sleep(max(0.0, vez - agora))


def rodar(caminho_textos=config.TEXTOS_SITES, limite: int | None = None, workers: int = 4,
          saida=config.CLASSIFICACAO_JSONL, rpm: int | None = None) -> int:
    textos = pd.read_csv(caminho_textos, dtype={"cnpj": str})
    empresas = textos_por_empresa(textos)
    feitos = ja_classificados(saida)
    pendentes = [e for e in empresas.to_dict("records")
                 if (e["cnpj"], PROMPT_VERSAO, e["hash_texto"], config.MODELO_CLASSIFICACAO) not in feitos]
    if limite:
        pendentes = pendentes[:limite]
    print(f"[classificar] {len(empresas)} empresas com texto útil; {len(pendentes)} a classificar "
          f"(prompt {PROMPT_VERSAO}, modelo {config.MODELO_CLASSIFICACAO})")
    if not pendentes:
        return 0
    cnaes = _cnaes([e["cnpj"] for e in pendentes])
    saida.parent.mkdir(parents=True, exist_ok=True)
    trava = threading.Lock()
    ritmo = _Ritmo(rpm)

    def um(e):
        ritmo.esperar()
        return classificar_um(e, cnaes.get(e["cnpj"]))

    ok = falhas = 0
    with ThreadPoolExecutor(max_workers=workers) as pool, open(saida, "a", encoding="utf-8") as f:
        futuros = {pool.submit(um, e): e for e in pendentes}
        for fut in as_completed(futuros):
            e = futuros[fut]
            try:
                r = fut.result()
            except Exception as erro:
                falhas += 1
                print(f"[classificar] {e['cnpj']}: ERRO {type(erro).__name__}: {str(erro)[:200]}")
                continue
            with trava:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
            ok += 1
            if ok % 25 == 0:
                print(f"[classificar] {ok}/{len(pendentes)}")
    print(f"[classificar] fim: {ok} classificadas, {falhas} com erro (rode de novo para tentar as que falharam)")
    for modelo, (entrada, saida_t) in llm.USO.items():
        print(f"[classificar] tokens {modelo}: {entrada} de entrada, {saida_t} de saída")
    return 1 if falhas else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("textos", nargs="?", default=str(config.TEXTOS_SITES))
    p.add_argument("--limite", type=int, default=None)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--rpm", type=int, default=None, help="limite de chamadas por minuto (Gemini gratuito: 15; OpenAI Build: 5.000)")
    a = p.parse_args()
    return rodar(a.textos, a.limite, a.workers, rpm=a.rpm)


if __name__ == "__main__":
    sys.exit(main())
