"""Garante que o limiar de recuo vem do config.yaml e que nenhum texto ou código do bloco de dados
cita um valor diferente dele (o limiar já foi 30 provisório e virou 50 por regra; ver DECISOES.md).

Rodar da raiz do repositório:
    python -m pytest tests/test_limiar.py -v
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import yaml

from dados.geno_db import consultas

RAIZ = Path(__file__).resolve().parents[1]
# Arquivos que citam outros valores de propósito: a tabela de candidatos {20, 30, 50, 100} da decisão e este teste.
IGNORAR = {"dados/decisoes/DECISOES.md", "dados/etl/decidir_parametros.py", "tests/test_limiar.py"}
# Formas em que um valor de limiar costuma aparecer escrito: "limiar de recuo (50", "`limiar_recuo`: **50**",
# "`min_estab` (padrão 50", "mínimo de 50 estabelecimentos"/"50 estabelecimentos)".
PADROES = [
    r"limiar de recuo\s*\((\d+)",
    r"limiar_recuo`?\s*[:=]?\s*\**(\d+)\b",
    r"min_estab`?\s*\(padrão\s*(\d+)",
    r"(?<![\d.])(\d+)\s+estabelecimentos\)\.\s+O ano corrente",     # docstring de consultas.py
    r"limiar de recuo do config\.yaml\s*\((\d+)\)",
    r"padrão `limiar_recuo` do config\.yaml\s*\((\d+)\)",
]


def _limiar() -> int:
    with open(RAIZ / "dados" / "config.yaml", encoding="utf-8") as f:
        return int(yaml.safe_load(f)["consultas"]["limiar_recuo"])


def _arquivos():
    for pasta, sufixo in (("dados", ".py"), ("dados", ".md"), ("tests", ".py")):
        for p in (RAIZ / pasta).rglob(f"*{sufixo}"):
            rel = p.relative_to(RAIZ).as_posix()
            if rel not in IGNORAR and "/raw/" not in rel:
                yield rel, p


def test_nenhum_arquivo_cita_um_limiar_diferente_do_config():
    limiar = _limiar()
    erros, lidos = [], 0
    for rel, p in _arquivos():
        texto = p.read_text(encoding="utf-8")
        for padrao in PADROES:
            for m in re.finditer(padrao, texto):
                lidos += 1
                if int(m.group(1)) != limiar:
                    linha = texto[: m.start()].count("\n") + 1
                    erros.append(f"{rel}:{linha} cita {m.group(1)}, o config.yaml diz {limiar}")
    assert lidos >= 3, "teste sem força: nenhuma citação de limiar encontrada (os padrões envelheceram?)"
    assert not erros, "\n".join(erros)


def test_padrao_do_limiar_nao_esta_fixo_no_codigo():
    """O padrão de min_estab tem de ser None (resolvido a partir do config.yaml), nunca um número."""
    padrao = inspect.signature(consultas.mortalidade_setor).parameters["min_estab"].default
    assert padrao is None
    fonte = inspect.getsource(consultas)
    assert re.search(r"_config\(\)\[\"consultas\"\]\[\"limiar_recuo\"\]", fonte), "consultas.py não lê limiar_recuo do config"
    # nenhuma atribuição de limiar com número literal em consultas.py (min_estab=1 em outros scripts é intencional)
    assert not re.search(r"(limiar\w*|minimo)\s*=\s*\d+", fonte)


def test_mudar_o_config_muda_o_comportamento(monkeypatch):
    """O recuo obedece ao config: com limiar enorme vai para o grupo, com limiar 1 fica na subclasse."""
    base = yaml.safe_load((RAIZ / "dados" / "config.yaml").read_text(encoding="utf-8"))
    for valor, esperado in ((10**9, "grupo"), (1, "subclasse")):
        alterado = {**base, "consultas": {**base["consultas"], "limiar_recuo": valor}}
        monkeypatch.setattr(consultas, "_config", lambda a=alterado: a)
        assert consultas.mortalidade_setor(["8599699"])["nivel_usado"] == esperado
