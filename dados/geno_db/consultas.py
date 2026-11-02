"""Consultas do GENO sobre dados/geno.duckdb, para o app e o motor importarem (dono: Lucas).

    from dados.geno_db import consultas
    consultas.saturacao(["8593700"])                       # aberturas, baixas e ativos por ano
    consultas.mortalidade_setor(["8593700"], horizonte=2)  # taxa de mortalidade por coorte

Regras comuns:
  * Conexão somente leitura. O caminho do banco vem de `caminhos.db` do config.yaml (relativo à raiz
    do repositório) e pode ser trocado pela variável de ambiente GENO_DB.
  * Padrões de período e de recuo vêm de `consultas` no config.yaml (provisórios: 2021 a 2025 e
    30 estabelecimentos). O ano corrente é parcial, por isso o período padrão termina em 2025.
  * Toda consulta é parametrizada com `?`; nenhum valor vindo do chamador entra no texto do SQL.
    Os códigos de CNAE são validados (3 a 7 dígitos) antes de qualquer consulta.
  * A unidade é o ESTABELECIMENTO (matriz e filiais contam separadamente).
  * CNAE: por padrão só o principal; `usar_secundario=True` inclui quem tem o CNAE como secundário.
  * Município é o código da Receita (não o do IBGE), texto, como em `estabelecimento.municipio_cod`.
  * "De ofício" é a classe `oficio` de dados/sql/seeds/motivo_classe.csv (inaptidão, omissão,
    registro cancelado...), que inclui as baixas em massa da Receita.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import duckdb
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / "dados" / "config.yaml"
NIVEIS = (("subclasse", 7), ("classe", 5), ("grupo", 3))  # tamanho do prefixo do CNAE em cada nível
_CNAE = re.compile(r"^[0-9]{3,7}$")


def _config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def caminho_banco() -> Path:
    """Caminho do geno.duckdb: variável GENO_DB, senão `caminhos.db` do config.yaml."""
    destino = os.getenv("GENO_DB") or _config()["caminhos"]["db"]
    p = Path(destino)
    return p if p.is_absolute() else RAIZ / p


def conectar() -> duckdb.DuckDBPyConnection:
    """Abre o banco em modo somente leitura. Quem chama deve fechar a conexão."""
    return duckdb.connect(str(caminho_banco()), read_only=True)


def _periodo(ano_ini: int | None, ano_fim: int | None) -> tuple[int, int]:
    ini_padrao, fim_padrao = _config()["consultas"]["periodo"]
    ini = int(ano_ini if ano_ini is not None else ini_padrao)
    fim = int(ano_fim if ano_fim is not None else fim_padrao)
    if ini > fim:
        raise ValueError(f"ano_ini ({ini}) maior que ano_fim ({fim})")
    return ini, fim


def _prefixos(cnaes: list[str]) -> list[str]:
    """Valida e deduplica os códigos de CNAE (3 a 7 dígitos, como texto)."""
    if isinstance(cnaes, str) or not cnaes:
        raise ValueError("cnaes deve ser uma lista não vazia de códigos, ex.: ['8593700']")
    ruins = [c for c in cnaes if not isinstance(c, str) or not _CNAE.match(c)]
    if ruins:
        raise ValueError(f"CNAE inválido (use 3 a 7 dígitos, como texto): {ruins}")
    return sorted(set(cnaes))


# Trechos de SQL fixos (escolhidos por flag, nunca montados com entrada do usuário). Cada um é um
# EXISTS sobre a lista de prefixos recebida como parâmetro `?::VARCHAR[]`.
_FILTRO_PRINCIPAL = """EXISTS (SELECT 1 FROM unnest(?::VARCHAR[]) AS p(x) WHERE starts_with(e.cnae_principal, p.x))"""
_FILTRO_SECUNDARIO = """(EXISTS (SELECT 1 FROM unnest(?::VARCHAR[]) AS p(x) WHERE starts_with(e.cnae_principal, p.x))
        OR EXISTS (SELECT 1 FROM unnest(?::VARCHAR[]) AS p(x), unnest(e.cnaes_secundarios) AS s(y)
                   WHERE starts_with(s.y, p.x)))"""


def _alvo(usar_secundario: bool) -> str:
    """CTE `alvo`: estabelecimentos do nicho. Parâmetros, nesta ordem: prefixos (2x se secundário), município x2."""
    filtro = _FILTRO_SECUNDARIO if usar_secundario else _FILTRO_PRINCIPAL
    return f"""alvo AS (
        SELECT e.data_inicio, e.situacao, e.data_situacao,
               (e.situacao = '08' AND coalesce(mc.classe = 'oficio', false)) AS oficio
        FROM estabelecimento e
        LEFT JOIN motivo_classe mc ON mc.codigo_motivo = e.motivo_situacao
        WHERE {filtro} AND (?::VARCHAR IS NULL OR e.municipio_cod = ?::VARCHAR)
    )"""


def _params_alvo(prefixos: list[str], municipio: str | None, usar_secundario: bool) -> list:
    lista = [prefixos, prefixos] if usar_secundario else [prefixos]
    return lista + [municipio, municipio]


def saturacao(cnaes: list[str], municipio: str | None = None, ano_ini: int | None = None,
              ano_fim: int | None = None, excluir_oficio: bool = True,
              usar_secundario: bool = False) -> pd.DataFrame:
    """Aberturas, baixas e estabelecimentos ativos por ano em um nicho.

    Args:
        cnaes: códigos de CNAE de 3 a 7 dígitos, como texto. Um código casa por prefixo, então
            "8593700" é a subclasse e "859" é o grupo inteiro.
        municipio: código de município da Receita (texto), ou None para todos.
        ano_ini, ano_fim: período inclusivo; padrão do config.yaml (2021 a 2025).
        excluir_oficio: se True (padrão), `saldo` não desconta as baixas de ofício.
        usar_secundario: se True, também conta quem tem o CNAE só como atividade secundária.

    Returns:
        DataFrame com uma linha por ano e as colunas (todas inteiras):
        ano; aberturas (estabelecimentos com data de início no ano); baixas (TODAS as baixas do ano,
        pela data da situação cadastral, inclusive as de ofício); baixas_oficio (parte das baixas
        que é de ofício); saldo = aberturas - baixas, ou aberturas - (baixas - baixas_oficio) com
        excluir_oficio=True; ativos_fim_ano (abertos até 31/12 do ano e não baixados até essa data).
        Anos sem nenhum evento aparecem com zeros nas três primeiras contagens.
    """
    pref = _prefixos(cnaes)
    ini, fim = _periodo(ano_ini, ano_fim)
    sql = f"""
        WITH {_alvo(usar_secundario)},
        anos AS (SELECT unnest(range(?::INTEGER, ?::INTEGER + 1)) AS ano)
        SELECT y.ano::INTEGER AS ano,
               count(*) FILTER (WHERE year(a.data_inicio) = y.ano)::BIGINT AS aberturas,
               count(*) FILTER (WHERE a.situacao = '08' AND year(a.data_situacao) = y.ano)::BIGINT AS baixas,
               count(*) FILTER (WHERE a.oficio AND year(a.data_situacao) = y.ano)::BIGINT AS baixas_oficio,
               count(*) FILTER (WHERE a.data_inicio <= make_date(y.ano, 12, 31)
                                  AND NOT (a.situacao = '08' AND a.data_situacao <= make_date(y.ano, 12, 31))
                               )::BIGINT AS ativos_fim_ano
        FROM anos y CROSS JOIN alvo a
        GROUP BY y.ano ORDER BY y.ano"""
    con = conectar()
    try:
        df = con.execute(sql, _params_alvo(pref, municipio, usar_secundario) + [ini, fim]).df()
    finally:
        con.close()
    descontadas = df["baixas"] - df["baixas_oficio"] if excluir_oficio else df["baixas"]
    df["saldo"] = (df["aberturas"] - descontadas).astype("int64")
    return df[["ano", "aberturas", "baixas", "baixas_oficio", "saldo", "ativos_fim_ano"]]


def _contar_nicho(con: duckdb.DuckDBPyConnection, prefixos: list[str], municipio: str | None,
                  ini: int, fim: int, usar_secundario: bool) -> int:
    """Estabelecimentos do nicho abertos no período (os que alimentam as coortes)."""
    sql = f"""WITH {_alvo(usar_secundario)}
              SELECT count(*) FROM alvo WHERE year(data_inicio) BETWEEN ?::INTEGER AND ?::INTEGER"""
    return con.execute(sql, _params_alvo(prefixos, municipio, usar_secundario) + [ini, fim]).fetchone()[0]


def mortalidade_setor(cnaes: list[str], municipio: str | None = None, ano_ini: int | None = None,
                      ano_fim: int | None = None, horizonte: int = 2, min_estab: int | None = None,
                      usar_secundario: bool = False) -> dict:
    """Taxa de mortalidade por coorte de abertura, com recuo para um CNAE mais amplo.

    Cada coorte é o conjunto de estabelecimentos abertos num ano. A taxa é o número dos que foram
    baixados até `horizonte` anos depois (ano da baixa <= ano da abertura + horizonte), sem contar
    as baixas de ofício, dividido pelo total de abertos da coorte. Baixas de ofício NÃO saem do
    denominador: quem foi baixado de ofício conta como aberto que não morreu (e aparece em
    `baixados_oficio` para você ver o tamanho disso). Só entram coortes que completaram o horizonte
    dentro do período (ano da coorte + horizonte <= ano_fim); as outras não aparecem.

    Recuo: se o nicho tiver menos que `min_estab` estabelecimentos abertos no período, amplia o
    filtro pela hierarquia do CNAE (subclasse, 7 dígitos; classe, 5; grupo, 3) até atingir o
    mínimo. Se nem o grupo atingir, usa o grupo mesmo assim; confira `n_estab`.

    Args:
        cnaes: códigos de CNAE de 7 dígitos (subclasse) como texto. Para o recuo funcionar o
            ponto de partida tem de ser a subclasse; com 5 ou 3 dígitos, os níveis maiores que o
            informado são pulados.
        municipio: código de município da Receita (texto), ou None.
        ano_ini, ano_fim: período inclusivo; padrão do config.yaml (2021 a 2025).
        horizonte: anos de observação depois da abertura (inteiro >= 1).
        min_estab: limiar do recuo; padrão `limiar_recuo` do config.yaml (30).
        usar_secundario: se True, também conta quem tem o CNAE só como atividade secundária.

    Returns:
        dict com:
          "dados": DataFrame com ano_coorte, abertos, baixados, baixados_oficio, taxa (float de 0 a 1);
          "nivel_usado": "subclasse" | "classe" | "grupo";
          "cnaes_usados": prefixos de CNAE efetivamente usados no filtro (7, 5 ou 3 dígitos);
          "n_estab": estabelecimentos do nicho abertos no período no nível usado.
    """
    pref = _prefixos(cnaes)
    ini, fim = _periodo(ano_ini, ano_fim)
    if not isinstance(horizonte, int) or isinstance(horizonte, bool) or horizonte < 1:
        raise ValueError("horizonte deve ser um inteiro >= 1")
    minimo = int(min_estab if min_estab is not None else _config()["consultas"]["limiar_recuo"])
    menor = min(len(c) for c in pref)

    con = conectar()
    try:
        escolhido = None
        for nome, tamanho in NIVEIS:
            if tamanho > menor:        # nunca recua para um nível mais fino que o informado
                continue
            usados = sorted({c[:tamanho] for c in pref})
            n = _contar_nicho(con, usados, municipio, ini, fim, usar_secundario)
            escolhido = (nome, usados, n)
            if n >= minimo:
                break
        nivel, usados, n_estab = escolhido

        sql = f"""
            WITH {_alvo(usar_secundario)}
            SELECT year(data_inicio)::INTEGER AS ano_coorte,
                   count(*)::BIGINT AS abertos,
                   count(*) FILTER (WHERE situacao = '08' AND NOT oficio
                                      AND year(data_situacao) <= year(data_inicio) + ?::INTEGER)::BIGINT AS baixados,
                   count(*) FILTER (WHERE oficio
                                      AND year(data_situacao) <= year(data_inicio) + ?::INTEGER)::BIGINT AS baixados_oficio
            FROM alvo
            WHERE year(data_inicio) BETWEEN ?::INTEGER AND ?::INTEGER - ?::INTEGER
            GROUP BY 1 ORDER BY 1"""
        df = con.execute(sql, _params_alvo(usados, municipio, usar_secundario)
                         + [horizonte, horizonte, ini, fim, horizonte]).df()
    finally:
        con.close()
    df["taxa"] = (df["baixados"] / df["abertos"]).astype("float64")
    return {"dados": df, "nivel_usado": nivel, "cnaes_usados": usados, "n_estab": int(n_estab)}
