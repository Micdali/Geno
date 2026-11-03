"""Testes de LGPD sobre dados/geno.duckdb.

O app só pode consultar vw_publico. Estes testes garantem que ela não vaza nome de pessoa física,
contato nem endereço detalhado, e que o banco não tem dados de sócios.

Rodar da raiz do repositório, depois de python -m dados.etl.construir_db:
    python -m pytest tests/test_lgpd.py -v
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pytest

DB = Path(__file__).resolve().parents[1] / "dados" / "geno.duckdb"

# Colunas que a vw_publico pode ter (lista fechada: qualquer coluna nova precisa ser aprovada aqui).
COLUNAS_PERMITIDAS = {
    "cnpj", "nome_exibicao", "situacao", "data_inicio", "data_situacao", "bairro", "municipio", "uf",
    "nome_fantasia", "razao_social", "cnae_principal", "cnae_descricao", "situacao_descricao",
    "porte", "opcao_simples", "opcao_mei",
}
# Fragmentos que nunca podem aparecer em nome de coluna da vw_publico.
PROIBIDOS = ("email", "mail", "correio", "telefone", "fone", "ddd", "fax", "logradouro", "numero",
             "complemento", "cep", "socio", "cpf", "dominio")
PESSOA_FISICA = ("(emp.opcao_mei OR s.opcao_mei = 'S' OR emp.natureza_juridica = '2135')")


@pytest.fixture(scope="module")
def con():
    if not DB.exists():
        pytest.fail(f"{DB} não existe. Rode: python -m dados.etl.construir_db")
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def test_pessoa_fisica_sem_razao_social(con):
    """Nenhuma linha de MEI ou natureza 2135 em vw_publico tem razao_social preenchida."""
    n_pf = con.execute(f"""
        SELECT count(*) FROM vw_publico p
        JOIN estabelecimento e USING (cnpj) JOIN empresa emp USING (cnpj_basico)
        LEFT JOIN simples s USING (cnpj_basico) WHERE {PESSOA_FISICA}""").fetchone()[0]
    vazando = con.execute(f"""
        SELECT count(*) FROM vw_publico p
        JOIN estabelecimento e USING (cnpj) JOIN empresa emp USING (cnpj_basico)
        LEFT JOIN simples s USING (cnpj_basico)
        WHERE {PESSOA_FISICA} AND p.razao_social IS NOT NULL""").fetchone()[0]
    assert n_pf > 100_000, f"teste sem força: só {n_pf} linhas de pessoa física encontradas"
    assert vazando == 0, f"{vazando} linhas de MEI/natureza 2135 com razao_social preenchida"


def test_nome_exibicao_nao_traz_cpf_de_pessoa_fisica(con):
    """Em MEI/EI, nem nome_exibicao nem nome_fantasia podem ter 11 dígitos (CPF) nem repetir o titular."""
    vazando = con.execute(f"""
        SELECT count(*) FROM vw_publico p
        JOIN estabelecimento e USING (cnpj) JOIN empresa emp USING (cnpj_basico)
        LEFT JOIN simples s USING (cnpj_basico)
        WHERE {PESSOA_FISICA}
          AND (regexp_matches(p.nome_exibicao, '[0-9]{{11}}') OR regexp_matches(coalesce(p.nome_fantasia, ''), '[0-9]{{11}}')
               OR upper(trim(p.nome_exibicao)) = upper(trim(regexp_replace(emp.razao_social, '\\s*[0-9]{{11}}\\s*$', ''))))
    """).fetchone()[0]
    assert vazando == 0, f"{vazando} linhas de MEI/EI expõem CPF ou o nome do titular"


def test_vw_publico_sem_contato_nem_endereco_detalhado(con):
    colunas = {r[0] for r in con.execute("DESCRIBE vw_publico").fetchall()}
    proibidas = {c for c in colunas if any(p in c.lower() for p in PROIBIDOS)}
    assert not proibidas, f"colunas proibidas em vw_publico: {sorted(proibidas)}"
    assert colunas == COLUNAS_PERMITIDAS, (
        f"colunas fora da lista aprovada: {sorted(colunas - COLUNAS_PERMITIDAS)}; "
        f"faltando: {sorted(COLUNAS_PERMITIDAS - colunas)}")


def test_vw_publico_nao_expoe_email_nos_valores(con):
    """Defesa extra: nenhum valor textual da view parece e-mail ou telefone."""
    textos = [r[0] for r in con.execute("DESCRIBE vw_publico").fetchall()
              if r[1] == "VARCHAR"]
    for coluna in textos:
        n = con.execute(f"SELECT count(*) FROM vw_publico WHERE regexp_matches({coluna}, '[^ ]+@[^ ]+\\.[a-z]{{2,}}')").fetchone()[0]
        assert n == 0, f"{n} valores com cara de e-mail em vw_publico.{coluna}"


def test_banco_sem_tabela_de_socios(con):
    achadas = con.execute("""
        SELECT table_name FROM information_schema.tables WHERE table_name ILIKE '%socio%'
        UNION SELECT table_name FROM information_schema.columns WHERE column_name ILIKE '%socio%'""").fetchall()
    assert not achadas, f"tabelas ou colunas de sócios no banco: {achadas}"


def test_banco_nao_guarda_email_completo_nem_telefone(con):
    """Relatório técnico, seção 12: do e-mail só o domínio; telefones descartados."""
    colunas = [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'main'").fetchall()]
    ruins = [c for c in colunas if re.search(r"telefone|fone|ddd|fax|correio|^email$", c, re.I)]
    assert not ruins, f"colunas de contato no banco: {ruins}"
    n = con.execute("SELECT count(*) FROM estabelecimento WHERE dominio_email LIKE '%@%'").fetchone()[0]
    assert n == 0, f"{n} registros com '@' em dominio_email (e-mail completo guardado)"
