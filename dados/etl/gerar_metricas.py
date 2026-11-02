"""Gera dados/METRICAS.md e dados/metricas.json com os números oficiais do recorte (dono: Lucas).

TODOS os números vêm de consultas ao geno.duckdb (e do config.yaml para os parâmetros); nada é
digitado à mão. Roda sozinho no fim de `python -m dados.etl.construir_db`, ou à parte:

    python -m dados.etl.gerar_metricas

Antes de escrever, confere a coerência dos números (por exemplo, a soma das situações cadastrais
igual ao total, baixas não maiores que o estoque) e aborta se algo não fechar.
No METRICAS.md: porcentagens com 1 casa e vírgula. No metricas.json: números com ponto.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date

from dados.etl.baixar import CONFIG_PADRAO, RAIZ, carregar_config
from dados.etl.filtrar import cnaes_do_recorte
from dados.etl.formato import dec, nome_proprio, num, pct, tabela_md
from dados.geno_db import consultas

MD = RAIZ / "dados" / "METRICAS.md"
JSON = RAIZ / "dados" / "metricas.json"
ORDEM_SITUACAO = ["02", "03", "04", "08", "01"]   # ativa, suspensa, inapta, baixada, nula
HORIZONTE = 2


def _hash_git() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or "desconhecido"
    except Exception:  # git ausente ou fora de um repositório
        return "desconhecido"


def r1(x: float) -> float:
    return round(100 * x, 1)


def coletar() -> dict:
    cfg = carregar_config(CONFIG_PADRAO)
    cnaes = cnaes_do_recorte(cfg)
    c = cfg["consultas"]
    ini, fim = c["periodo"]
    con = consultas.conectar()
    um = lambda sql, p=None: con.execute(sql, p or []).fetchone()[0]  # noqa: E731
    try:
        total = um("SELECT count(*) FROM estabelecimento")
        desc_sit = dict(con.execute("SELECT codigo, descricao FROM situacao_cadastral").fetchall())
        sit = dict(con.execute("SELECT situacao, count(*) FROM estabelecimento GROUP BY 1").fetchall())
        situacoes = [{"codigo": k, "descricao": desc_sit[k], "n": sit.get(k, 0), "pct": r1(sit.get(k, 0) / total)}
                     for k in ORDEM_SITUACAO]
        desc_cnae = dict(con.execute("SELECT codigo, descricao FROM cnae WHERE codigo = ANY(?::VARCHAR[])", [cnaes]).fetchall())
        por_cnae = []
        for cod in cnaes:
            n, at = con.execute("SELECT count(*), count(*) FILTER (WHERE situacao = '02') FROM estabelecimento "
                                "WHERE cnae_principal = ?", [cod]).fetchone()
            por_cnae.append({"cnae": cod, "descricao": desc_cnae[cod], "total": n, "ativas": at, "pct_ativas": r1(at / n)})
        n, at = con.execute("SELECT count(*), count(*) FILTER (WHERE situacao = '02') FROM estabelecimento "
                            "WHERE cnae_principal <> ALL(?::VARCHAR[])", [cnaes]).fetchone()
        por_cnae.append({"cnae": "outros", "descricao": "CNAE principal fora do setor (entraram pelo CNAE secundário)",
                         "total": n, "ativas": at, "pct_ativas": r1(at / n)})
        municipios = [{"municipio": nome_proprio(nome), "ativos": a, "total": t, "pct_ativos": r1(a / t)}
                      for nome, a, t in con.execute("""
            SELECT m.descricao, count(*) FILTER (WHERE e.situacao = '02') a, count(*) t
            FROM estabelecimento e JOIN municipio m ON m.codigo = e.municipio_cod
            GROUP BY 1 ORDER BY a DESC, 1 LIMIT 10""").fetchall()]
        mei, simples, matriz = con.execute("""
            SELECT count(*) FILTER (WHERE s.opcao_mei = 'S'), count(*) FILTER (WHERE s.opcao_simples = 'S'),
                   count(*) FILTER (WHERE e.matriz)
            FROM estabelecimento e LEFT JOIN simples s USING (cnpj_basico)""").fetchone()
        perfil = {"n_mei": mei, "pct_mei": r1(mei / total), "n_simples": simples, "pct_simples": r1(simples / total),
                  "n_matriz": matriz, "pct_matriz": r1(matriz / total),
                  "n_filial": total - matriz, "pct_filial": r1((total - matriz) / total)}
        ativos = sit.get("02", 0)
        com_dom = um("SELECT count(*) FROM estabelecimento WHERE situacao = '02' AND dominio_email IS NOT NULL")
        cobertura = {"ativos": ativos, "ativos_com_dominio_proprio": com_dom, "pct": r1(com_dom / ativos)}
        diretas_ab = um("SELECT count(*) FROM estabelecimento WHERE year(data_inicio) BETWEEN ? AND ?", [ini, fim])
    finally:
        con.close()

    ev = consultas.saturacao(cnaes, ano_ini=ini, ano_fim=fim, usar_secundario=True)
    eventos = ev.astype("int64").to_dict("records")
    mort = consultas.mortalidade_setor(cnaes, ano_ini=ini, ano_fim=fim, horizonte=HORIZONTE, min_estab=1, usar_secundario=True)
    md_ = mort["dados"]
    coortes = [{"ano": int(r.ano_coorte), "abertos": int(r.abertos), "baixados": int(r.baixados),
                "baixados_oficio": int(r.baixados_oficio), "taxa_pct": r1(r.taxa)} for r in md_.itertuples()]
    ab_t, bx_t = sum(x["abertos"] for x in coortes), sum(x["baixados"] for x in coortes)

    # ---- coerência: se algo não fechar, aborta antes de escrever
    erros = []
    if sum(s["n"] for s in situacoes) != total:
        erros.append("a soma das situações cadastrais não bate com o total")
    if sum(x["total"] for x in por_cnae) != total:
        erros.append("a soma por CNAE não bate com o total")
    if sum(e["aberturas"] for e in eventos) != diretas_ab:
        erros.append("aberturas do período (saturacao) divergem da contagem direta")
    if any(e["baixas"] > total or e["baixas_oficio"] > e["baixas"] for e in eventos):
        erros.append("baixas maiores que o estoque, ou baixas de ofício maiores que as baixas")
    if any(not (0 <= x["taxa_pct"] <= 100) or x["baixados"] > x["abertos"] for x in coortes):
        erros.append("taxa de mortalidade fora de 0 a 100%")
    if sit.get("08", 0) < sum(e["baixas"] for e in eventos):
        erros.append("mais baixas no período do que estabelecimentos baixados")
    if erros:
        raise SystemExit("ERRO de coerência nas métricas: " + "; ".join(erros))

    return {
        "fonte": {"competencia": cfg["fonte"]["competencia"], "data_geracao": date.today().isoformat(),
                  "commit": _hash_git()},
        "recorte": {"uf": cfg["recorte"]["uf"], "unidade": "estabelecimento",
                    "cnaes": [{"codigo": k, "descricao": desc_cnae[k]} for k in cnaes],
                    "periodo": [ini, fim], "anos_atipicos": c.get("anos_atipicos", [])},
        "parametros": {"limiar_recuo": c["limiar_recuo"], "lacuna_max_abs": c["lacuna_max_abs"],
                       "lacuna_max_pct": c["lacuna_max_pct"]},
        "estoque": {"total": total, "situacoes": situacoes,
                    "pct_ativas": next(s["pct"] for s in situacoes if s["codigo"] == "02"),
                    "pct_baixadas": next(s["pct"] for s in situacoes if s["codigo"] == "08")},
        "por_cnae": por_cnae, "por_municipio": municipios, "perfil": perfil,
        "eventos": eventos,
        "mortalidade": {"horizonte_anos": HORIZONTE, "coortes": coortes, "abertos": ab_t, "baixados": bx_t,
                        "taxa_pct": r1(bx_t / ab_t), "excluindo": "baixas de ofício"},
        "cobertura_scraping": cobertura,
    }


def renderizar(d: dict) -> str:
    f, rc, p, e = d["fonte"], d["recorte"], d["parametros"], d["estoque"]
    ini, fim = rc["periodo"]
    L = ["# Métricas do recorte do GENO", "",
         "Gerado automaticamente por `python -m dados.etl.gerar_metricas` (roda ao fim do `construir_db`). "
         "Todos os números vêm de consultas ao `geno.duckdb`; não edite à mão. Os mesmos números, em formato "
         "estruturado, estão em `metricas.json`.", "",
         "## Fonte", "",
         f"- Base: Dados Abertos do CNPJ, Receita Federal do Brasil (licença CC-BY), competência **{f['competencia']}**.",
         f"- Data de geração: {f['data_geracao']}",
         f"- Commit: `{f['commit']}`", "",
         "## Recorte", "",
         f"- UF: **{rc['uf']}**. Unidade de análise: **{rc['unidade']}** (matriz e filiais contam separadamente).",
         f"- Período dos eventos: **{ini} a {fim}** (anos completos).",
         "- CNAEs (principal ou secundário):", ""]
    L += [f"  - {k['codigo']}: {k['descricao']}" for k in rc["cnaes"]]
    L += ["", "## Parâmetros", "",
          f"- `limiar_recuo`: **{p['limiar_recuo']}** estabelecimentos no nicho antes de ampliar o CNAE (subclasse, classe, grupo).",
          f"- Lacuna: no máximo `max({p['lacuna_max_abs']}, {pct(p['lacuna_max_pct'])} dos estabelecimentos ativos do nicho)`; "
          f"só se aponta com pelo menos {p['limiar_recuo']} ativos no nicho.",
          "- Regras e números que sustentam cada escolha: [decisoes/DECISOES.md](decisoes/DECISOES.md).", "",
          "## Estoque", "",
          f"Total de estabelecimentos no recorte: **{num(e['total'])}**. Ativas: **{dec(e['pct_ativas'])}%**. "
          f"Baixadas: **{dec(e['pct_baixadas'])}%**.", ""]
    L += [tabela_md(["Situação cadastral", "Estabelecimentos", "%"],
                    [[s["descricao"], num(s["n"]), dec(s["pct"]) + "%"] for s in e["situacoes"]]), "",
          "## Por CNAE (principal)", ""]
    L += [tabela_md(["CNAE", "Descrição", "Estabelecimentos", "Ativas", "% ativas"],
                    [[x["cnae"], x["descricao"], num(x["total"]), num(x["ativas"]), dec(x["pct_ativas"]) + "%"] for x in d["por_cnae"]]), "",
          "## Municípios com mais estabelecimentos ativos (10 maiores)", ""]
    L += [tabela_md(["Município", "Ativos", "Total", "% ativos"],
                    [[x["municipio"], num(x["ativos"]), num(x["total"]), dec(x["pct_ativos"]) + "%"] for x in d["por_municipio"]]), "",
          "## Perfil", "", f"Base: todos os {num(e['total'])} estabelecimentos do recorte.", ""]
    pf = d["perfil"]
    L += [tabela_md(["Característica", "Estabelecimentos", "%"],
                    [["Empresa optante pelo MEI", num(pf["n_mei"]), dec(pf["pct_mei"]) + "%"],
                     ["Empresa optante pelo Simples Nacional", num(pf["n_simples"]), dec(pf["pct_simples"]) + "%"],
                     ["Matriz", num(pf["n_matriz"]), dec(pf["pct_matriz"]) + "%"],
                     ["Filial", num(pf["n_filial"]), dec(pf["pct_filial"]) + "%"]]), "",
          f"## Eventos no período ({ini} a {fim})", "",
          "Aberturas pela data de início de atividade; baixas pela data da situação cadastral (situação 08). "
          "`Baixas de ofício` são parte das baixas, separadas pelo motivo (`motivo_classe.csv`). "
          "`Saldo` = aberturas - baixas que não são de ofício. `Ativos no fim do ano`: abertos até 31/12 e ainda não baixados nessa data, o que inclui estabelecimentos inaptos e suspensos (por isso é maior que a contagem de situação \"ativa\" do estoque).", ""]
    L += [tabela_md(["Ano", "Aberturas", "Baixas", "Baixas de ofício", "Saldo", "Ativos no fim do ano"],
                    [[x["ano"], num(x["aberturas"]), num(x["baixas"]), num(x["baixas_oficio"]), num(x["saldo"]),
                      num(x["ativos_fim_ano"])] for x in d["eventos"]]), "",
          f"## Mortalidade em {d['mortalidade']['horizonte_anos']} anos", "",
          "Por coorte de abertura: baixados até 2 anos depois (ano da baixa <= ano da abertura + 2), sem contar as baixas de "
          "ofício, sobre o total de abertos da coorte. Só entram coortes que completaram os 2 anos dentro do período.", ""]
    m = d["mortalidade"]
    L += [tabela_md(["Coorte (ano de abertura)", "Abertos", "Baixados", "Baixas de ofício até o horizonte", "Taxa"],
                    [[x["ano"], num(x["abertos"]), num(x["baixados"]), num(x["baixados_oficio"]), dec(x["taxa_pct"]) + "%"]
                     for x in m["coortes"]]), "",
          f"Coortes somadas: {num(m['baixados'])} baixados de {num(m['abertos'])} abertos, taxa de **{dec(m['taxa_pct'])}%**.", "",
          "## Cobertura para a coleta dos sites", ""]
    cb = d["cobertura_scraping"]
    L += [f"Dos **{num(cb['ativos'])}** estabelecimentos ativos, **{num(cb['ativos_com_dominio_proprio'])}** "
          f"(**{dec(cb['pct'])}%**) têm e-mail de domínio próprio (provedores genéricos, como gmail e hotmail, excluídos). "
          "É o ponto de partida para achar o site; domínios de contadores ainda não foram descartados.", "",
          "## Limitações", "",
          f"- A base é uma fotografia de uma única competência ({f['competencia']}); empresas e baixas posteriores não aparecem.",
          f"- O ano corrente ({fim + 1}) está excluído por estar incompleto; o período vai de {ini} a {fim}.",
          "- As baixas de ofício estão separadas pelo motivo da situação cadastral, conforme `dados/sql/seeds/motivo_classe.csv`; "
          "a data da baixa é um indicador ruidoso do fechamento real da empresa.",
          "- A unidade é o estabelecimento, não a empresa: matriz e filiais contam separadamente.",
          "- Os percentuais de MEI e Simples refletem a situação atual da empresa na competência, não a da data de abertura.",
          "- Os números de mortalidade não são comparáveis diretamente aos do IBGE e do Sebrae (a base inclui MEIs e empresas sem empregados)."]
    if rc["anos_atipicos"]:
        L.append(f"- Ano atípico identificado na decisão do recorte temporal: {', '.join(map(str, rc['anos_atipicos']))} (fora do período).")
    return "\n".join(L) + "\n"


def gerar() -> tuple[str, dict]:
    d = coletar()
    md = renderizar(d)
    MD.write_text(md, encoding="utf-8")
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, d


if __name__ == "__main__":
    gerar()
    print(f"OK: {MD.relative_to(RAIZ)} e {JSON.relative_to(RAIZ)}")
    sys.exit(0)
