"""Decide por regra objetiva o recorte temporal, o limiar de recuo e a referência de lacuna (dono: Lucas).

Lê o geno.duckdb, aplica as três regras abaixo, grava os parâmetros em dados/config.yaml (seção
`consultas`) e escreve dados/decisoes/DECISOES.md com os números que sustentam cada escolha.
Roda uma vez por competência (ou quando alguém quiser rever); depois disso o config.yaml é a fonte.

Regras:
  1. Período: 5 anos completos (ano da competência - 5 a ano da competência - 1). Se as aberturas do
     primeiro ano ficarem mais de 30% acima ou abaixo da média dos 4 seguintes, o primeiro ano é
     atípico e o período começa um ano depois. O ano da competência fica de fora (incompleto).
  2. limiar_recuo: menor n em {20, 30, 50, 100} cuja meia-largura do IC de 95% (Wilson) da taxa média
     de mortalidade em 2 anos do setor seja <= 15 pontos percentuais; se nenhum, 100 (e avisa).
  3. Lacuna: lacuna_max_abs = 2 e lacuna_max_pct = 0.05 (máx(2, 5% dos ativos do nicho)); só se
     aponta lacuna com pelo menos limiar_recuo ativos no nicho.

Uso: python -m dados.etl.decidir_parametros
"""
from __future__ import annotations

import math
import re
import sys
from datetime import date

from dados.etl.baixar import CONFIG_PADRAO, RAIZ, carregar_config
from dados.etl.filtrar import cnaes_do_recorte
from dados.etl.formato import dec, nome_proprio, num, pct, tabela_md
from dados.geno_db import consultas

Z = 1.96
CANDIDATOS_N = (20, 30, 50, 100)
MAX_MEIA_LARGURA = 0.15
TOLERANCIA_ATIPICO = 0.30
LACUNA_ABS, LACUNA_PCT = 2, 0.05
DESTINO = RAIZ / "dados" / "decisoes" / "DECISOES.md"


def wilson(p: float, n: int, z: float = Z) -> tuple[float, float]:
    """Intervalo de Wilson para uma proporção p observada em n."""
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centro - meia, centro + meia


def decidir() -> dict:
    cfg = carregar_config(CONFIG_PADRAO)
    cnaes = cnaes_do_recorte(cfg)
    ano_comp = int(cfg["fonte"]["competencia"][:4])
    fim = ano_comp - 1
    con = consultas.conectar()
    um = lambda sql, p=None: con.execute(sql, p or []).fetchone()[0]  # noqa: E731
    try:
        # ---- 1. recorte temporal
        ab = dict(con.execute("SELECT year(data_inicio), count(*) FROM estabelecimento "
                              "WHERE year(data_inicio) BETWEEN ? AND ? GROUP BY 1 ORDER BY 1",
                              [fim - 6, fim]).fetchall())
        primeiro = fim - 4
        media = sum(ab[a] for a in range(primeiro + 1, fim + 1)) / 4
        desvio = ab[primeiro] / media - 1
        atipico = abs(desvio) > TOLERANCIA_ATIPICO
        ini = primeiro + 1 if atipico else primeiro
        periodo = [ini, fim]
        anos_atipicos = [primeiro] if atipico else []

        # ---- 2. limiar de recuo
        r = consultas.mortalidade_setor(cnaes, ano_ini=ini, ano_fim=fim, horizonte=2, min_estab=1,
                                        usar_secundario=True)
        d = r["dados"]
        abertos, baixados = int(d["abertos"].sum()), int(d["baixados"].sum())
        p = baixados / abertos
        wil = [(n, *wilson(p, n)) for n in CANDIDATOS_N]
        meias = {n: (hi - lo) / 2 for n, lo, hi in wil}
        ok = [n for n in CANDIDATOS_N if meias[n] <= MAX_MEIA_LARGURA]
        limiar = ok[0] if ok else 100
        limiar_sem_regra = not ok

        # combinações subclasse CNAE x município (principal, abertos no período)
        n_sub = con.execute("""
            WITH t AS (SELECT cnae_principal c, municipio_cod m FROM estabelecimento
                       WHERE year(data_inicio) BETWEEN ? AND ?),
            sub AS (SELECT c, m, count(*) n FROM t GROUP BY 1, 2)
            SELECT s.c, s.m, s.n,
                   (SELECT count(*) FROM t WHERE t.m = s.m AND left(t.c, 5) = left(s.c, 5)),
                   (SELECT count(*) FROM t WHERE t.m = s.m AND left(t.c, 3) = left(s.c, 3))
            FROM sub s WHERE s.c = ANY(?::VARCHAR[])""", [ini, fim, cnaes]).fetchall()
        niveis = {"subclasse": 0, "classe": 0, "grupo": 0, "grupo_abaixo": 0}
        amostra = []
        for c, m, n7, n5, n3 in n_sub:
            if n7 >= limiar:
                nv = "subclasse"
            elif n5 >= limiar:
                nv = "classe"
            else:
                nv = "grupo"
            niveis[nv] += 1
            if nv == "grupo" and n3 < limiar:
                niveis["grupo_abaixo"] += 1
            amostra.append((c, m, nv))
        # confere a regra contra a própria função em 12 combinações espalhadas
        for c, m, nv in amostra[:: max(1, len(amostra) // 12)]:
            got = consultas.mortalidade_setor([c], municipio=m, ano_ini=ini, ano_fim=fim, horizonte=2,
                                              min_estab=limiar)["nivel_usado"]
            assert got == nv, f"nível divergente em {c}/{m}: tabela {nv}, função {got}"

        # ---- 3. referência de tamanho para lacuna
        top = con.execute("""
            SELECT e.municipio_cod, m.descricao, count(*) AS total
            FROM estabelecimento e JOIN municipio m ON m.codigo = e.municipio_cod
            GROUP BY 1, 2 ORDER BY total DESC LIMIT 10""").fetchall()
        ativos = {(c, m): n for c, m, n in con.execute(
            "SELECT cnae_principal, municipio_cod, count(*) FROM estabelecimento WHERE situacao = '02' GROUP BY 1, 2").fetchall()}
        desc = dict(con.execute("SELECT codigo, descricao FROM cnae WHERE codigo = ANY(?::VARCHAR[])", [cnaes]).fetchall())
    finally:
        con.close()

    hoje = date.today().isoformat()
    obs = ("Decidido por regra objetiva; pode ser revisto alterando o `dados/config.yaml` e rodando "
           "`python -m dados.etl.construir_db`.")
    md = [f"# Decisões do bloco de banco de dados\n\nCompetência da Receita: **{cfg['fonte']['competencia']}**. "
          f"Gerado por `python -m dados.etl.decidir_parametros` em {hoje}. Os valores vigentes estão em "
          "`dados/config.yaml`, seção `consultas`.\n"]

    md.append(f"## 1. Recorte temporal\n\n**Regra:** usar os {fim - primeiro + 1} anos completos de {primeiro} a {fim}. Se as "
              f"aberturas de {primeiro} ficarem mais de 30% acima ou abaixo da média de {primeiro + 1} a {fim}, usar "
              f"{primeiro + 1} a {fim} e registrar {primeiro} como ano atípico. {ano_comp} (ano da competência) fica sempre de fora, por estar incompleto.\n")
    md.append(tabela_md(["Ano", "Aberturas (estabelecimentos)"], [[a, num(ab[a])] for a in sorted(ab)]))
    md.append(f"\nMédia de {primeiro + 1} a {fim}: **{num(round(media))}**. Aberturas de {primeiro}: **{num(ab[primeiro])}**, "
              f"{'+' if desvio >= 0 else '-'}{pct(abs(desvio))} em relação à média (limite: 30%).\n")
    md.append(f"**Valor escolhido:** período **{ini} a {fim}**. "
              + (f"{primeiro} registrado como ano atípico." if atipico else f"{primeiro} não é atípico.")
              + f"\n\n_{hoje}. {obs}_\n")

    md.append("## 2. Limiar de recuo (`limiar_recuo`)\n\n**Regra:** menor n em {20, 30, 50, 100} cuja meia-largura do "
              "intervalo de confiança de 95% (Wilson) da taxa média de mortalidade em 2 anos do setor seja de no máximo "
              "15 pontos percentuais; se nenhum atender, 100.\n")
    md.append(f"Taxa média de mortalidade em 2 anos do setor, coortes completas de {d['ano_coorte'].min()} a "
              f"{d['ano_coorte'].max()}, sem as baixas de ofício: **{pct(p)}** ({num(baixados)} baixados de {num(abertos)} abertos, "
              "coortes somadas).\n")
    md.append(tabela_md(["n (estabelecimentos no nicho)", "IC 95% de Wilson", "Meia-largura", "Atende (<= 15 p.p.)?"],
                        [[n, f"{pct(lo)} a {pct(hi)}", dec(100 * meias[n]) + " p.p.",
                          "sim" if meias[n] <= MAX_MEIA_LARGURA else "não"] for n, lo, hi in wil]))
    md.append(f"\n**Valor escolhido:** `limiar_recuo = {limiar}`."
              + (" Nenhum n atendeu a regra; usado 100 conforme a regra." if limiar_sem_regra else "") + "\n")
    tot = len(n_sub)
    md.append(f"Efeito do limiar escolhido, nas {tot} combinações subclasse CNAE x município do setor com pelo menos um "
              f"estabelecimento aberto de {ini} a {fim}:\n")
    md.append(tabela_md(["Nível usado", "Combinações", "%"],
                        [["subclasse", niveis["subclasse"], pct(niveis["subclasse"] / tot)],
                         ["classe (recua)", niveis["classe"], pct(niveis["classe"] / tot)],
                         ["grupo (recua)", niveis["grupo"], pct(niveis["grupo"] / tot)]]))
    md.append(f"\nDas que recuam para grupo, **{niveis['grupo_abaixo']}** nem no grupo atingem {limiar} estabelecimentos "
              "(a resposta sai com o grupo mesmo assim; `n_estab` mostra o tamanho). Conferido contra "
              "`consultas.mortalidade_setor` em 12 combinações.\n")
    md.append(f"_{hoje}. {obs}_\n")

    md.append(f"## 3. Limiar de lacuna\n\n**Regra:** uma combinação de atributos é lacuna quando tem no máximo "
              f"`max({LACUNA_ABS}, {pct(LACUNA_PCT)} dos estabelecimentos ativos do nicho no recorte geográfico)`. Só se aponta "
              f"lacuna quando o nicho tem pelo menos `limiar_recuo` ({limiar}) ativos; abaixo disso, a resposta é "
              "\"dados insuficientes\".\n")
    md.append(f"Parâmetros gravados: `lacuna_max_abs = {LACUNA_ABS}`, `lacuna_max_pct = {LACUNA_PCT}`.\n")
    md.append("Os dados de classificação por LLM ainda não existem; esta é só uma referência de tamanho: nos 10 municípios "
              "com mais estabelecimentos do recorte, ativos por CNAE principal e o limite de lacuna que resultaria. "
              f"`*` marca nicho com menos de {limiar} ativos (\"dados insuficientes\").\n")
    linhas = []
    for mun, nome, total in top:
        cel = []
        for c in cnaes:
            n = ativos.get((c, mun), 0)
            lim = max(LACUNA_ABS, LACUNA_PCT * n)
            cel.append(f"{num(n)} ({dec(lim)}){'*' if n < limiar else ''}")
        linhas.append([nome_proprio(nome), num(total)] + cel)
    md.append(tabela_md(["Município", "Estab. (total)"] + [f"{c}" for c in cnaes], linhas))
    md.append("\nCélula = ativos do CNAE principal no município (limite de lacuna). CNAEs: "
              + "; ".join(f"{c} {desc[c]}" for c in cnaes) + ".\n")
    md.append(f"_{hoje}. {obs}_\n")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text("\n".join(md), encoding="utf-8")

    # ---- grava no config.yaml (troca só o bloco `consultas`, preservando o resto e os comentários)
    bloco = (f"consultas:\n  periodo: [{ini}, {fim}]     # {ano_comp} fica de fora (incompleto); ver decisoes/DECISOES.md\n"
             f"  anos_atipicos: {anos_atipicos}\n"
             f"  limiar_recuo: {limiar}          # nº mínimo de estabelecimentos do nicho antes de ampliar o CNAE\n"
             f"  lacuna_max_abs: {LACUNA_ABS}      # lacuna: no máximo max(abs, pct x ativos do nicho) estabelecimentos\n"
             f"  lacuna_max_pct: {LACUNA_PCT}\n")
    cp = RAIZ / "dados" / "config.yaml"
    txt = cp.read_text(encoding="utf-8")
    novo = re.sub(r"consultas:\n(?:  .*\n)+", bloco, txt, count=1)
    assert novo != txt or bloco in txt, "bloco consultas não encontrado no config.yaml"
    cp.write_text(novo, encoding="utf-8")
    return {"periodo": periodo, "atipico": atipico, "limiar": limiar, "taxa": p, "niveis": niveis,
            "meias": meias, "ab": ab, "media": media, "desvio": desvio, "sem_regra": limiar_sem_regra}


if __name__ == "__main__":
    r = decidir()
    print(f"periodo={r['periodo']} atipico={r['atipico']} (2021 vs média: {100 * r['desvio']:+.1f}%)")
    print(f"taxa={100 * r['taxa']:.1f}% meias={ {n: round(100 * v, 1) for n, v in r['meias'].items()} } limiar={r['limiar']}")
    print(f"niveis={r['niveis']}")
    sys.exit(0)
