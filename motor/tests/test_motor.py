"""Testes do motor sem rede, sem cota e sem banco: LLM, vetorizador e banco são falsos.

    python -m pytest motor/tests -v
"""
from __future__ import annotations

import hashlib
import json
import re

import httpx
import numpy as np
import openai
import pandas as pd
import pytest

from motor import analisar as mod_analisar
from motor import classificar, confianca, config, diferencial, embeddings, lacunas, llm, nicho

PARAMS = {"max_abs": 2, "max_pct": 0.05, "minimo_nicho": 50}


def vetorizar_falso(textos):
    """Saco de palavras com hash: textos com palavras em comum ficam parecidos."""
    m = np.zeros((len(textos), 64), dtype=np.float32)
    for i, t in enumerate(textos):
        for w in re.findall(r"\w+", (t or "").lower()):
            m[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
    n = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(n == 0, 1, n)


def classificacao_falsa(**kw):
    base = {"publico_atendido": "adultos", "produto_servico": "aulas de inglês", "canal_atendimento": "online",
            "problema_resolvido": "aprender inglês", "modelo_receita": "pacote_ou_mensalidade",
            "posicionamento": "indeterminado", "descricao_nicho": "inglês online para adultos", "confianca": "alta"}
    base.update(kw)
    return base


# --- classificação ----------------------------------------------------------------------------
def _textos():
    return pd.DataFrame([
        {"cnpj": "11111111000101", "site": "a.com.br", "metodo": "email", "url": "https://a.com.br/sobre", "tipo": "sobre",
         "texto": "Somos uma escola.", "status_http": 200, "bloqueado": False, "coletado_em": "2026-11-03"},
        {"cnpj": "11111111000101", "site": "a.com.br", "metodo": "email", "url": "https://a.com.br", "tipo": "home",
         "texto": "Inglês para adultos.", "status_http": 200, "bloqueado": False, "coletado_em": "2026-11-03"},
        {"cnpj": "22222222000102", "site": "b.com.br", "metodo": "email", "url": "https://b.com.br", "tipo": "home",
         "texto": "Bloqueado", "status_http": 403, "bloqueado": True, "coletado_em": "2026-11-03"},
        {"cnpj": None, "site": "c.com.br", "metodo": None, "url": "https://c.com.br", "tipo": "home",
         "texto": "Sem CNPJ", "status_http": 200, "bloqueado": False, "coletado_em": "2026-11-03"},
        {"cnpj": "33333333000103", "site": "d.com.br", "metodo": "manual", "url": "https://web.archive.org/d", "tipo": "arquivada",
         "texto": "Curso preparatório.", "status_http": 200, "bloqueado": False, "coletado_em": "2026-11-03"},
    ])


def test_textos_por_empresa_filtra_e_ordena():
    e = classificar.textos_por_empresa(_textos()).set_index("cnpj")
    assert list(e.index) == ["11111111000101", "33333333000103"]  # bloqueado e sem CNPJ saem
    assert e.loc["11111111000101", "texto"].startswith("[home] Inglês")  # home antes de sobre
    assert e.loc["11111111000101", "fonte"] == "site"
    assert e.loc["33333333000103", "fonte"] == "site_arquivado"


def test_textos_por_empresa_um_site_por_cnpj():
    linha = {"cnpj": "44444444000104", "tipo": "home", "status_http": 200, "bloqueado": False, "coletado_em": "2026-11-03"}
    t = pd.DataFrame([
        {**linha, "site": "contador.com.br", "metodo": "email", "url": "https://contador.com.br",
         "texto": "Escritório de contabilidade com muito texto " * 20},
        {**linha, "site": "escola.com.br", "metodo": "rodape_cnpj", "url": "https://escola.com.br", "texto": "Escola de inglês."},
        {**linha, "site": "outro.com.br", "metodo": "nome_titulo", "url": "https://outro.com.br", "texto": "Consultoria."},
    ])
    e = classificar.textos_por_empresa(t)
    assert len(e) == 1
    assert e.iloc[0]["site"] == "escola.com.br" and e.iloc[0]["metodo"] == "rodape_cnpj"
    assert "contabilidade" not in e.iloc[0]["texto"] and "Consultoria" not in e.iloc[0]["texto"]


def test_site_fora_de_ensino_vira_indeterminado_e_sai_dos_embeddings():
    def gerar(prompt, schema, modelos, **kw):
        return classificacao_falsa(site_de_ensino=False, canal_atendimento="presencial"), "modelo-falso"

    empresa = {"cnpj": "55555555000105", "fonte": "site", "texto": "Contabilidade.", "hash_texto": "x", "site": "c.com.br"}
    r = classificar.classificar_um(empresa, gerar=gerar)
    assert r["confianca"] == "baixa"
    assert all(r[c] == "indeterminado" for c in classificar.CAMPOS_TEXTO + ["canal_atendimento", "modelo_receita"])
    assert embeddings.texto_origem(r) == ""


def test_classificacao_retomavel_e_reclassifica_se_texto_mudar(tmp_path, monkeypatch):
    chamadas = []

    def gerar(prompt, schema, modelos, **kw):
        chamadas.append(prompt)
        return classificacao_falsa(publico_atendido=""), "modelo-falso"

    monkeypatch.setattr(classificar.llm, "gerar_json", gerar)
    monkeypatch.setattr(classificar, "_cnaes", lambda cnpjs: {})
    monkeypatch.setattr(config, "MODELO_CLASSIFICACAO", "modelo-falso")
    csv, saida = tmp_path / "t.csv", tmp_path / "c.jsonl"
    _textos().to_csv(csv, index=False)

    assert classificar.rodar(csv, workers=2, saida=saida) == 0
    assert len(chamadas) == 2
    classificar.rodar(csv, saida=saida)
    assert len(chamadas) == 2  # nada novo

    t = _textos()
    t.loc[1, "texto"] = "Inglês para adultos 40+."
    t.to_csv(csv, index=False)
    classificar.rodar(csv, saida=saida)
    assert len(chamadas) == 3  # só a empresa cujo texto mudou

    df = classificar.carregar(saida)
    assert len(df) == 2
    linha = df.set_index("cnpj").loc["11111111000101"]
    assert linha["publico_atendido"] == "indeterminado"  # vazio vira indeterminado
    assert linha["prompt_versao"] == classificar.PROMPT_VERSAO and linha["modelo_llm"] == "modelo-falso"
    assert not any("CNPJ" in p and "11111111000101" in p for p in chamadas)  # CNPJ não vai ao LLM


def test_trocar_de_modelo_reclassifica(tmp_path, monkeypatch):
    usados = []

    def gerar(prompt, schema, modelos, **kw):
        usados.append(modelos[0])
        return classificacao_falsa(), modelos[0]

    monkeypatch.setattr(classificar.llm, "gerar_json", gerar)
    monkeypatch.setattr(classificar, "_cnaes", lambda cnpjs: {})
    csv, saida = tmp_path / "t.csv", tmp_path / "c.jsonl"
    _textos().to_csv(csv, index=False)
    monkeypatch.setattr(config, "MODELO_CLASSIFICACAO", "modelo-a")
    classificar.rodar(csv, saida=saida)
    monkeypatch.setattr(config, "MODELO_CLASSIFICACAO", "modelo-b")
    classificar.rodar(csv, saida=saida)
    classificar.rodar(csv, saida=saida)
    assert usados == ["modelo-a"] * 2 + ["modelo-b"] * 2
    assert set(classificar.carregar(saida)["modelo_llm"]) == {"modelo-b"}  # vale a última
    assert set(classificar.carregar(saida, modelo="modelo-a")["modelo_llm"]) == {"modelo-a"}


def test_texto_origem_ignora_indeterminado():
    t = embeddings.texto_origem(classificacao_falsa(publico_atendido="indeterminado", canal_atendimento="indeterminado"))
    assert "indeterminado" not in t and "inglês" in t


# --- lacunas e concorrentes -------------------------------------------------------------------
def test_atende_canal():
    assert lacunas.atende_canal("online", "online") is True
    assert lacunas.atende_canal("online", "hibrido") is True
    assert lacunas.atende_canal("hibrido", "online") is False
    assert lacunas.atende_canal("online", "presencial") is False
    assert lacunas.atende_canal("online", "indeterminado") is None


def test_filtrar_por_servico_tira_outro_nicho_e_servico_desconhecido():
    v = vetorizar_falso(["aulas de inglês", "aulas de inglês em grupo", "pilates"])
    ranking = [("a", 0.9), ("b", 0.8), ("c", 0.7)]
    r = lacunas.filtrar_por_servico(v[0], ranking, {"a": v[1], "b": v[2]}, minimo=0.6)
    assert r == [("a", 0.9)]  # b é de outro nicho; c não tem serviço conhecido


def test_embeddings_guarda_vetor_do_servico(tmp_path, monkeypatch):
    monkeypatch.setattr(embeddings, "vetorizar", vetorizar_falso)
    classif = pd.DataFrame([{"cnpj": "1", **classificacao_falsa()},
                            {"cnpj": "2", **classificacao_falsa(produto_servico="indeterminado")}])
    destino = tmp_path / "e.parquet"
    embeddings.gerar(classif, destino)
    s = embeddings.carregar_servico(destino)
    assert set(s) == {"1"} and s["1"].shape == (64,)


def test_ranquear_ordena_e_corta():
    v = vetorizar_falso(["inglês online adultos", "inglês online adultos", "pilates", "inglês adultos"])
    r = lacunas.ranquear(v[0], ["a", "b", "c"], v[1:], minimo=0.3)
    assert [c for c, _ in r] == ["a", "c"]
    assert r[0][1] == pytest.approx(1.0, abs=1e-3)


RECORTE = {"descricao": "inglês · aulas em grupo · 40+ · online",
           "atributos": {"publico": "adultos 40+", "produto_servico": "aulas de inglês em grupo", "canal": "online"},
           "cnaes": ["8593700"]}


def _marcas(n, oferecem_tudo):
    m = {}
    for i in range(n):
        tudo = i < oferecem_tudo
        m[f"{i:014d}"] = {"publico": tudo or i % 2 == 0, "produto_servico": True, "canal": tudo or i % 2 == 1}
    return m


def test_lacuna_aponta_combinacao_rara_com_base():
    marcas = _marcas(60, oferecem_tudo=1)
    lac, aviso = lacunas.calcular(RECORTE, marcas, set(marcas), PARAMS)
    assert aviso is None
    tripla = [l for l in lac if len(l["atributos"]) == 3]
    assert len(tripla) == 1 and tripla[0]["n_empresas_que_oferecem"] <= 3
    assert tripla[0]["n_empresas_analisadas"] == 60 and len(tripla[0]["cnpjs_base"]) == 60
    assert all(set(l["atendimento"]) == set(l["cnpjs_base"]) for l in lac)


def test_lacuna_dados_insuficientes():
    marcas = _marcas(60, oferecem_tudo=1)
    ativos = set(list(marcas)[:10])  # só 10 ativas: abaixo do mínimo de 50
    lac, aviso = lacunas.calcular(RECORTE, marcas, ativos, PARAMS)
    assert lac == [] and "insuficientes" in aviso


def test_lacuna_ignora_quem_o_site_nao_diz():
    marcas = _marcas(60, oferecem_tudo=0)
    for c in list(marcas)[:20]:
        marcas[c]["canal"] = None
    lac, _ = lacunas.calcular(RECORTE, marcas, set(marcas), PARAMS)
    assert all(l["n_empresas_analisadas"] == 40 for l in lac if "canal" in l["atributos"])


def test_marcar_atendimento():
    empresas = [{"cnpj": "1", **classificacao_falsa(publico_atendido="adultos 40+", produto_servico="aulas de inglês em grupo")},
                {"cnpj": "2", **classificacao_falsa(publico_atendido="crianças pequenas", produto_servico="balé infantil",
                                                     canal_atendimento="presencial")},
                {"cnpj": "3", **classificacao_falsa(publico_atendido="indeterminado")}]
    m = lacunas.marcar_atendimento(RECORTE, empresas, vetorizar_falso)
    assert m["1"] == {"publico": True, "produto_servico": True, "canal": True}
    assert m["2"] == {"publico": False, "produto_servico": False, "canal": False}
    assert m["3"]["publico"] is None


# --- confiança --------------------------------------------------------------------------------
def test_confianca_niveis():
    assert confianca.avaliar(1000, ["alta"] * 60, True)["nivel"] == "alta"
    assert confianca.avaliar(1000, ["alta"] * 25, True)["nivel"] == "media"
    assert confianca.avaliar(1000, ["alta"] * 5, True)["nivel"] == "baixa"
    assert confianca.avaliar(1000, ["baixa"] * 40 + ["alta"] * 20, True)["nivel"] == "baixa"  # cai um nível
    c = confianca.avaliar(20881, ["alta"] * 5, True, "Dados insuficientes para apontar lacunas.")
    assert "20.881" in c["texto"] and "setor inteiro" in c["texto"] and "insuficientes" in c["texto"]
    assert "ideia, de 20.881 estabelecimentos" in c["texto"]  # a vírgula da frase não vira ponto
    assert c["n_empresas"] == 20881 and c["n_com_site_classificado"] == 5


# --- LLM ao vivo (com resposta falsa) ---------------------------------------------------------
def test_propor_recorte():
    def gerar(prompt, schema, modelos, **kw):
        assert "inglês" in prompt and modelos == config.MODELOS_AO_VIVO
        return {"descricao": "x", "atributos": RECORTE["atributos"], "cnaes": ["9999999", "8593700"],
                "perguntas": [{"pergunta": f"p{i}", "opcoes": ["a", "Não sei ainda"]} for i in range(5)]}, "m"
    r = nicho.propor_recorte("escola de inglês", gerar=gerar)
    assert r["uf"] == "RJ" and r["cnaes"] == ["8593700"] and len(r["perguntas"]) == 3
    r = nicho.propor_recorte("escola de inglês", respostas={"p0": "a", "p1": "a", "p2": "a"}, gerar=gerar)
    assert r["perguntas"] == []


def test_diferencial_sem_llm_quando_falha():
    def falha(*a, **kw):
        raise diferencial.llm.LLMIndisponivel("fora")
    conc = [{"o_que_oferece": "x", "publico": "y", "canal": "online", "situacao": "ativa", "semelhanca": 0.8}]
    d = diferencial.gerar("ideia", RECORTE, conc, [], gerar_json=falha)
    assert set(d) == set(diferencial.CAMPOS) and "não respondeu" in d["nao_verificado"]


# --- adaptador do LLM (sem rede) --------------------------------------------------------------
def test_schema_estrito_da_openai_sem_mudar_o_original():
    original = json.dumps(nicho.SCHEMA, sort_keys=True)
    s = llm.schema_estrito(nicho.SCHEMA)
    assert json.dumps(nicho.SCHEMA, sort_keys=True) == original  # o Gemini recebe o schema original
    objetos = [s, s["properties"]["atributos"], s["properties"]["perguntas"]["items"]]
    for o in objetos:
        assert o["additionalProperties"] is False and o["required"] == list(o["properties"])
    for schema in (classificar.SCHEMA, diferencial.SCHEMA):
        e = llm.schema_estrito(schema)
        assert e["additionalProperties"] is False and set(e["required"]) == set(schema["properties"])


def test_erro_temporario_da_openai():
    req = httpx.Request("POST", "https://api.openai.com/v1/responses")

    def status(codigo, classe=openai.APIStatusError):
        return classe("x", response=httpx.Response(codigo, request=req), body=None)

    assert llm._temporario(status(429, openai.RateLimitError))
    assert llm._temporario(status(500, openai.InternalServerError))
    assert llm._temporario(status(503, openai.InternalServerError))
    assert llm._temporario(openai.APITimeoutError(request=req))
    assert llm._temporario(openai.APIConnectionError(request=req))
    assert not llm._temporario(status(400, openai.BadRequestError))
    assert not llm._temporario(status(401, openai.AuthenticationError))
    assert not llm._temporario(ValueError("schema"))


def test_gerar_json_usa_o_provedor_e_troca_de_modelo(monkeypatch):
    req = httpx.Request("POST", "https://api.openai.com/v1/responses")
    chamadas = []

    def openai_falso(prompt, schema, modelo, *a):
        chamadas.append(modelo)
        if modelo == "a":
            raise openai.RateLimitError("x", response=httpx.Response(429, request=req), body=None)
        return '{"ok": true}'

    monkeypatch.setattr(config, "LLM_PROVEDOR", "openai")
    monkeypatch.setattr(llm, "_gerar_openai", openai_falso)
    monkeypatch.setattr(llm, "_gerar_gemini", lambda *a: pytest.fail("chamou o Gemini"))
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    assert llm.gerar_json("p", {}, ["a", "b"], tentativas=2) == ({"ok": True}, "b")
    assert chamadas == ["a", "a", "b"]


# --- ponta a ponta ----------------------------------------------------------------------------
def test_analisar_ponta_a_ponta_no_formato_do_contrato_4(monkeypatch):
    n = 60
    cnpjs = [f"{i:014d}" for i in range(n)]
    classif = pd.DataFrame([{"cnpj": c, "prompt_versao": "v1", "fonte": "site", "site": f"s{i}.com.br",
                             **classificacao_falsa(publico_atendido="adultos 40+" if i == 0 else "crianças",
                                                   produto_servico="aulas de inglês em grupo",
                                                   descricao_nicho="aulas de inglês em grupo online")}
                            for i, c in enumerate(cnpjs)])
    textos = [embeddings.texto_origem(r) for r in classif.to_dict("records")]
    monkeypatch.setattr(embeddings, "vetorizar", vetorizar_falso)
    monkeypatch.setattr(classificar, "carregar", lambda: classif)
    monkeypatch.setattr(embeddings, "carregar", lambda: (cnpjs, vetorizar_falso(textos)))
    servicos = dict(zip(cnpjs, vetorizar_falso(classif["produto_servico"].tolist())))
    servicos.pop(cnpjs[2])  # serviço indeterminado: fica fora
    monkeypatch.setattr(embeddings, "carregar_servico", lambda: servicos)
    monkeypatch.setattr(config, "parametros_lacuna", lambda: PARAMS)
    publicos = pd.DataFrame({"cnpj": cnpjs, "nome_exibicao": [f"Escola {i}" for i in range(n)],
                             "situacao": ["08" if i == 1 else "02" for i in range(n)],
                             "data_situacao": [pd.Timestamp("2024-05-01")] * n})
    monkeypatch.setattr(mod_analisar, "_publicos", lambda cs: publicos[publicos["cnpj"].isin(cs)])
    monkeypatch.setattr(mod_analisar, "_ativos_setor", lambda cnaes: 98)
    monkeypatch.setattr(mod_analisar, "_saturacao", lambda cnaes: pd.DataFrame(
        {"ano": [2024, 2025], "aberturas": [10, 12], "baixas": [5, 6], "baixas_oficio": [1, 1],
         "saldo": [6, 7], "ativos_fim_ano": [100, 105]}))
    monkeypatch.setattr(diferencial.llm, "gerar_json", lambda *a, **kw: (
        {"em_comum": "a", "possiveis_diferenciais": "b", "nao_verificado": "c"}, "m"))

    r = mod_analisar.analisar("escola de inglês online em grupo para 40+", recorte=RECORTE)

    assert set(r) == {"ideia", "recorte", "confianca", "concorrentes", "saturacao", "lacunas", "diferencial", "gerado_em"}
    assert set(r["recorte"]) == {"descricao", "atributos", "uf"} and r["recorte"]["uf"] == "RJ"
    assert set(r["confianca"]) == {"nivel", "n_empresas", "n_com_site_classificado", "usou_setor_amplo", "texto"}
    assert r["confianca"]["n_empresas"] == 98 and r["confianca"]["usou_setor_amplo"] is True  # só ativas, não ativos_fim_ano
    assert 0 < len(r["concorrentes"]) <= config.MAX_CONCORRENTES
    c0 = r["concorrentes"][0]
    assert set(c0) == {"cnpj", "nome_exibicao", "o_que_oferece", "publico", "canal", "situacao", "ano_baixa", "semelhanca", "site"}
    sems = [c["semelhanca"] for c in r["concorrentes"]]
    assert sems == sorted(sems, reverse=True) and all(0 <= s <= 1 for s in sems)
    assert cnpjs[2] not in {c["cnpj"] for c in r["concorrentes"]}
    baixada = [c for c in r["concorrentes"] if c["cnpj"] == cnpjs[1]]
    assert not baixada or (baixada[0]["situacao"] == "baixada" and baixada[0]["ano_baixa"] == 2024)
    assert r["saturacao"]["baixas"] == [4, 5] and r["saturacao"]["total_aberturas"] == 22  # sem baixas de ofício
    assert r["lacunas"], "esperava ao menos uma lacuna (só 1 de 59 ativas atende 40+)"
    for l in r["lacunas"]:
        assert {"titulo", "atributos", "n_empresas_que_oferecem", "n_empresas_analisadas", "cnpjs_base"} <= set(l)
        assert l["cnpjs_base"] and cnpjs[1] not in l["cnpjs_base"]  # baixada não conta
    assert r["diferencial"] == {"em_comum": "a", "possiveis_diferenciais": "b", "nao_verificado": "c"}
    json.dumps(r)  # serializável para o app


def test_analisar_sem_nenhum_concorrente(monkeypatch):
    classif = pd.DataFrame([{"cnpj": "1", "prompt_versao": "v3", "fonte": "site", "site": "a.com.br",
                             **classificacao_falsa(produto_servico="pilates")}])
    monkeypatch.setattr(embeddings, "vetorizar", vetorizar_falso)
    monkeypatch.setattr(classificar, "carregar", lambda: classif)
    monkeypatch.setattr(embeddings, "carregar", lambda: (["1"], vetorizar_falso(["pilates"])))
    monkeypatch.setattr(embeddings, "carregar_servico", lambda: {"1": vetorizar_falso(["pilates"])[0]})
    monkeypatch.setattr(config, "parametros_lacuna", lambda: PARAMS)
    monkeypatch.setattr(mod_analisar, "_publicos", lambda cs: pytest.fail("não devia consultar o banco"))
    monkeypatch.setattr(mod_analisar, "_ativos_setor", lambda cnaes: 4199)
    monkeypatch.setattr(mod_analisar, "_saturacao", lambda cnaes: pd.DataFrame(
        {"ano": [2025], "aberturas": [10], "baixas": [5], "baixas_oficio": [1], "saldo": [5], "ativos_fim_ano": [100]}))
    monkeypatch.setattr(diferencial.llm, "gerar_json", lambda *a, **kw: pytest.fail("sem concorrentes não chama o LLM"))

    r = mod_analisar.analisar("escola de inglês", recorte=RECORTE)

    assert r["concorrentes"] == [] and r["lacunas"] == []
    assert r["confianca"]["nivel"] == "baixa" and r["confianca"]["n_com_site_classificado"] == 0
    assert "insuficientes" in r["confianca"]["texto"]
    assert "Não encontramos empresas parecidas" in r["diferencial"]["em_comum"]
    json.dumps(r)


def test_erro_temporario_do_gemini():
    req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    assert llm._temporario(httpx.ConnectError("recusada", request=req))
    assert llm._temporario(httpx.ReadTimeout("lento", request=req))
    assert llm._temporario(llm.errors.ServerError(503, {"error": {"message": "x"}}))
    assert llm._temporario(llm.errors.ClientError(429, {"error": {"message": "cota"}}))
    assert llm._temporario(llm.errors.ClientError(408, {"error": {"message": "tempo"}}))
    assert not llm._temporario(llm.errors.ClientError(400, {"error": {"message": "schema"}}))


def test_texto_do_site_vai_ao_llm_sem_contatos():
    prompts = []

    def gerar(prompt, schema, modelos, **kw):
        prompts.append(prompt)
        return classificacao_falsa(), "m"

    texto = ("Escola de inglês desde 2010. Fale com ana.souza@gmail.com, (21) 98765-4321 ou +55 21 2233-4455. "
             "CNPJ 12.345.678/0001-90. CPF 123.456.789-09. CEP 22041-001, R$ 1.299,00.")
    empresa = {"cnpj": "1", "fonte": "site", "texto": texto, "hash_texto": "h", "site": "e.com.br"}
    classificar.classificar_um(empresa, gerar=gerar)
    p = prompts[0]
    assert "ana.souza" not in p and "98765" not in p and "2233-4455" not in p
    assert "12.345.678" not in p and "123.456.789" not in p
    assert "[e-mail]" in p and "[telefone]" in p and "desde 2010" in p and "22041-001" in p and "1.299,00" in p
