"""Geno — as 6 telas do produto (dono: Christian).

    streamlit run app/app.py

Fala com o motor só pelo contrato 4 (`motor.analisar`) e, quando existir, por
`motor.nicho.propor_recorte` (tela 2). Empresas vêm do motor, que lê da `vw_publico` (LGPD).
Tema e textos são da Mariana (`app/geno/tema.py` e `app/geno/textos.py`).
"""
from __future__ import annotations

import html
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP = Path(__file__).resolve().parent
RAIZ = APP.parent
sys.path[:0] = [str(RAIZ), str(APP)]  # motor/ está na raiz; geno/ (tema e textos) em app/

from geno.tema import CORES, aplicar_tema, caixa_confianca, card_lacuna, logo  # noqa: E402
from geno.textos import T  # noqa: E402
from motor.analisar import analisar  # noqa: E402

try:
    from motor.nicho import propor_recorte
except ImportError:  # motor sem a parte da tela 2: recorte do arquivo de exemplo
    propor_recorte = None

EXEMPLO = RAIZ / "contratos" / "exemplos" / "resultado_analise.exemplo.json"
TELAS = ["Descrever ideia", "Confirmar nicho", "Processamento", "Concorrentes", "Saturação", "Lacunas"]
CANAIS = {"online": "Online", "presencial": "Presencial", "hibrido": "Híbrido",
          "delivery": "Vai até o cliente", "indeterminado": "Não sei / tanto faz"}
SITUACAO = {"ativa": "Ativa", "baixada": "Baixada", "inapta": "Inapta", "suspensa": "Suspensa", "nula": "Nula"}
ATRIBUTO = {"produto_servico": "Serviço", "publico": "Público", "canal": "Canal"}
MARCA = {True: "✅", False: "❌", None: "❔"}
NAO_SEI = "Não sei ainda"

st.set_page_config(page_title="Geno", page_icon="🌱", layout="wide")
aplicar_tema()
s = st.session_state
for chave, valor in {"tela": 1, "ideia": "", "recorte": None, "respostas": {}, "resultado": None, "erro": None}.items():
    s.setdefault(chave, valor)


def ir(tela: int):
    s.tela = tela
    st.rerun()


def num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def exemplo() -> dict:
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


def sugerir_recorte(ideia: str, respostas: dict | None = None) -> dict:
    if propor_recorte is None:
        pergunta = {"pergunta": "As aulas seriam principalmente:",
                    "opcoes": ["Conversação para o dia a dia", "Inglês para viagem", "Inglês para o trabalho", NAO_SEI]}
        return exemplo()["recorte"] | {"perguntas": [] if respostas else [pergunta]}
    try:
        return propor_recorte(ideia, respostas=respostas or None)
    except Exception:  # LLM fora do ar: a pessoa preenche o recorte à mão na tela 2
        return {"descricao": "", "atributos": {"publico": "", "produto_servico": "", "canal": "indeterminado"},
                "perguntas": [], "falhou": True}


# --- barra lateral -------------------------------------------------------------------------------
with st.sidebar:
    logo(130)
    st.caption("O mercado da sua ideia")
    for i, nome in enumerate(TELAS, 1):
        liberada = i == 1 or (i == 2 and s.recorte) or (i >= 4 and s.resultado)
        if st.button(f"{i} · {nome}", key=f"nav{i}", disabled=not liberada, width="stretch",
                     type="primary" if i == s.tela else "secondary"):
            ir(i)
    st.divider()
    st.caption(T.RODAPE)


def limite():
    st.markdown(f'<div class="geno-limite">{T.LIMITE_DEMANDA}</div>', unsafe_allow_html=True)


# --- telas ---------------------------------------------------------------------------------------
def tela_1():
    st.title(T.TITULO)
    st.write(T.SUBTITULO)
    ideia = st.text_area(T.CAMPO_IDEIA_LABEL, s.ideia, height=140, placeholder=T.CAMPO_IDEIA_PLACEHOLDER)
    st.caption(f"{T.SEM_CADASTRO} {T.AVISO_PILOTO}")
    if st.button(T.BOTAO_ANALISAR, type="primary"):
        if not ideia.strip():
            st.error(T.ERRO_IDEIA_VAZIA)
            return
        if len(ideia.strip()) < 10:
            st.error(T.ERRO_IDEIA_CURTA)
            return
        with st.spinner("Entendendo sua ideia…"):
            s.ideia, s.respostas, s.resultado = ideia.strip(), {}, None
            s.recorte = sugerir_recorte(s.ideia)
        ir(2)


def tela_2():
    r, a = s.recorte, s.recorte["atributos"]
    st.title(T.RECORTE_TITULO)
    st.markdown(f"**Sua ideia:** _{s.ideia}_")
    if r.get("falhou"):
        st.warning("Não conseguimos sugerir o nicho agora. Preencha os campos abaixo com suas palavras.")
    elif r.get("descricao"):
        with st.container(border=True):
            st.markdown(f"**{r['descricao']}**")

    st.caption(T.RECORTE_AJUDA)
    c1, c2, c3 = st.columns(3)
    canais = list(CANAIS)
    editado = {
        "produto_servico": c1.text_input(T.RECORTE_PRODUTO, a.get("produto_servico", "")).strip(),
        "publico": c2.text_input(T.RECORTE_PUBLICO, a.get("publico", "")).strip(),
        "canal": c3.selectbox(T.RECORTE_CANAL, canais, format_func=CANAIS.get,
                              index=canais.index(a["canal"]) if a.get("canal") in CANAIS else canais.index("indeterminado")),
    }
    st.caption(f"**{T.RECORTE_GEOGRAFIA}:** {T.RECORTE_GEOGRAFIA_PADRAO}")

    respostas = {}
    if r.get("perguntas"):
        st.markdown(f"**{T.AFUNILAR_INTRO}**")
        total = len(r["perguntas"])
        for atual_i, p in enumerate(r["perguntas"], 1):
            if total > 1:
                st.caption(T.AFUNILAR_RODADA.format(atual=atual_i, total=total))
            atual = s.respostas.get(p["pergunta"])
            escolha = st.radio(p["pergunta"], p["opcoes"], index=p["opcoes"].index(atual) if atual in p["opcoes"] else None)
            if escolha and escolha != NAO_SEI:
                respostas[p["pergunta"]] = escolha

    c1, c2 = st.columns(2)
    if c1.button(T.BOTAO_CONFIRMAR_RECORTE, type="primary", width="stretch"):
        confirmar(editado, respostas)
    if c2.button(T.BOTAO_ANALISAR_ASSIM_MESMO, width="stretch",
                 help="Analisa com o recorte de cima, sem responder às perguntas."):
        confirmar(editado, {})


def confirmar(editado: dict, respostas: dict):
    if not editado["produto_servico"]:
        st.error("Diga o que você vai oferecer.")
        return
    r = s.recorte
    mudou = {k: v for k, v in editado.items() if v != r["atributos"].get(k)}
    if respostas:
        s.respostas = s.respostas | respostas
        with st.spinner("Afinando o recorte com suas respostas…"):
            novo = sugerir_recorte(s.ideia, s.respostas)
        if not novo.get("falhou"):
            r = novo
    r = r | {"atributos": r["atributos"] | mudou}
    if mudou or not r.get("descricao"):
        at = r["atributos"]
        canal = "" if at["canal"] == "indeterminado" else CANAIS[at["canal"]]
        r["descricao"] = " · ".join(x for x in (at["produto_servico"], at["publico"], canal) if x)
    s.recorte, s.resultado, s.erro = r, None, None
    s.pop("tarefa", None)  # análise de um recorte antigo, se a pessoa saiu da tela 3 no meio
    ir(3)


def tela_3():
    st.title(T.PROGRESSO_TITULO)
    st.caption(s.recorte["descricao"])
    if s.erro:
        st.error(T.ERRO_SERVICO)
        with st.expander("Detalhe do erro"):
            st.code(s.erro)
        c1, c2, c3 = st.columns(3)
        if c1.button(T.BOTAO_TENTAR_NOVAMENTE, type="primary", width="stretch"):
            s.erro = None
            st.rerun()
        if c2.button("Voltar e ajustar", width="stretch"):
            ir(2)
        if c3.button("Ver com dados de exemplo", width="stretch", help="Empresas e números fictícios."):
            s.resultado, s.erro = exemplo() | {"ideia": s.ideia}, None
            ir(4)
        return

    # A análise roda numa thread e só a barra (um fragment) se redesenha: se o script ficasse
    # esperando, o Streamlit manteria os campos da tela 2 embaixo da barra.
    if "tarefa" not in s:
        s.tarefa, s.inicio = ThreadPoolExecutor(1).submit(analisar, s.ideia, s.recorte), time.monotonic()
    progresso()
    st.caption(T.PROGRESSO_DEMORA)


@st.fragment(run_every=0.3)
def progresso():
    if not s.tarefa.done():
        # shortcut: progresso estimado pelo tempo, porque analisar() não informa as etapas; trocar se o motor passar a informar
        t = time.monotonic() - s.inicio
        etapas = T.PROGRESSO_ETAPAS
        st.progress(min(0.95, t / (t + 8)), text=etapas[min(int(t // 5), len(etapas) - 1)])
        return
    tarefa = s.pop("tarefa")
    try:
        s.resultado = tarefa.result()
    except Exception as e:
        s.erro = f"{type(e).__name__}: {e}"
        st.rerun()
    ir(4)


def cabecalho():
    r = s.resultado
    if "_aviso" in r:
        st.error("**Dados de exemplo:** empresas e números fictícios, só para ver as telas.", icon="🧪")
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"**Sua ideia:** _{r['ideia']}_  \n**Recorte:** {r['recorte']['descricao']}")
    if c2.button(f"✏️ {T.BOTAO_AJUSTAR_IDEIA}", width="stretch"):
        ir(2)
    conf = r["confianca"]
    # o texto vem do motor (contrato 4): escapado porque o tema o põe dentro de HTML
    caixa_confianca(conf["nivel"] if conf["nivel"] in ("alta", "media", "baixa") else "baixa", html.escape(conf["texto"]))


def tela_4():
    cabecalho()
    st.title(T.CONCORRENTES_TITULO)
    cs = s.resultado["concorrentes"]
    if not cs:
        st.info(T.CONCORRENTES_VAZIO)
        limite()
        return
    ativas = sum(c["situacao"] == "ativa" for c in cs)
    m1, m2, m3 = st.columns(3)
    m1.metric("Mais parecidas", len(cs))
    m2.metric("Ativas", ativas)
    m3.metric("Não ativas na Receita", len(cs) - ativas)
    df = pd.DataFrame({
        "Empresa": [c["nome_exibicao"] or "Nome não exibido" for c in cs],
        "O que oferece": [c["o_que_oferece"] for c in cs],
        "Público": [c["publico"] for c in cs],
        "Canal": [CANAIS.get(c["canal"], c["canal"]) for c in cs],
        "Situação": [SITUACAO.get(c["situacao"], c["situacao"]) + (f" em {c['ano_baixa']}" if c.get("ano_baixa") else "")
                     for c in cs],
        "Semelhança": [c["semelhanca"] for c in cs],
        # o motor manda o domínio sem esquema (ex.: "escola.com.br"); sem https:// o link vira relativo
        "Site": [s if not s or "://" in s else f"https://{s}" for s in (c.get("site") for c in cs)],
    })
    if not df["Site"].any():
        df = df.drop(columns="Site")
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "Semelhança": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
        "Site": st.column_config.LinkColumn(display_text=r"https?://(.*)")})
    st.caption(f"{T.BAIXA_CNPJ_CURTO}. {T.SEM_SITE_AVISO}")
    d = s.resultado.get("diferencial") or {}
    partes = [(t, d.get(k)) for t, k in (("Em comum com eles", "em_comum"),
                                          ("Possíveis diferenciais", "possiveis_diferenciais"),
                                          ("Não deu para verificar", "nao_verificado")) if d.get(k)]
    if partes:
        with st.expander("Em comum com eles e possíveis diferenciais", expanded=True):
            st.markdown("\n\n".join(f"**{t}:** {v}" for t, v in partes))
    limite()


def tela_5():
    cabecalho()
    st.title(T.SATURACAO_TITULO)
    sat = s.resultado["saturacao"]
    if not sat.get("anos"):
        st.info("Não há dados de aberturas e baixas para este recorte.")
        limite()
        return
    saldo = sat["total_aberturas"] - sat["total_baixas"]
    if saldo:
        frase = T.SATURACAO_FRASE_ABRIRAM_MAIS if saldo > 0 else T.SATURACAO_FRASE_FECHARAM_MAIS
        st.write(frase.format(anos=len(sat["anos"])))
    fig = go.Figure([go.Bar(name="Aberturas", x=sat["anos"], y=sat["aberturas"], marker_color=CORES["floresta"]),
                     go.Bar(name="Baixas", x=sat["anos"], y=sat["baixas"], marker_color=CORES["coral"])])
    fig.update_layout(barmode="group", height=380, margin=dict(t=20, b=20), legend=dict(orientation="h"),
                      xaxis=dict(type="category"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Manrope, sans-serif", color=CORES["tinta"]))
    st.plotly_chart(fig, width="stretch")
    periodo = f"{sat['anos'][0]}–{sat['anos'][-1]}"
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Aberturas ({periodo})", num(sat["total_aberturas"]))
    c2.metric(f"Baixas ({periodo})", num(sat["total_baixas"]))
    c3.metric("Saldo no período", num(saldo))
    if s.resultado["confianca"].get("usou_setor_amplo"):
        st.info("Estes números são do setor inteiro (CNAE), não só do seu nicho.")
    st.caption(f"{T.BAIXA_CNPJ_AVISO} Fonte: {sat['fonte']}")
    limite()


def empresas_base(lacuna: dict, nomes: dict) -> pd.DataFrame:
    atendimento = lacuna.get("atendimento") or {}
    linhas = []
    for c in lacuna["cnpjs_base"]:
        nome = (nomes[c] or "Nome não exibido") if c in nomes else f"CNPJ {c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
        linha = {"Empresa": nome}
        if atendimento:
            linha |= {ATRIBUTO[a]: MARCA[atendimento.get(c, {}).get(a)] for a in lacuna["atributos"]}
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tela_6():
    cabecalho()
    st.title(T.LACUNA_TITULO)
    lacunas = s.resultado["lacunas"]
    if not lacunas:
        st.info(T.LACUNA_NENHUMA)
        limite()
        return
    nomes = {c["cnpj"]: c["nome_exibicao"] for c in s.resultado["concorrentes"]}
    for i, l in enumerate(lacunas):
        k, combinacao = l["n_empresas_que_oferecem"], l["titulo"][:1].lower() + l["titulo"][1:]
        frase = (T.LACUNA_FRASE if k == 0 else T.LACUNA_FRASE_POUCAS).format(
            n=l["n_empresas_analisadas"], k=k, combinacao=combinacao)
        if k == 1:
            frase = frase.replace("oferecem", "oferece")
        if i == 0:  # o título vem do LLM: escapado porque o card é HTML
            card_lacuna(html.escape(l["titulo"]), html.escape(frase))
        else:
            st.markdown(f"**{l['titulo']}**: {frase}")
        n_base = len(l["cnpjs_base"])
        rotulo = "Ver a empresa analisada" if n_base == 1 else T.LACUNA_VER_EMPRESAS.format(n=n_base)
        with st.expander(rotulo):
            st.caption(T.LACUNA_EMPRESAS_AJUDA + "  \n" + " · ".join(f"{ATRIBUTO[a]}: {v}" for a, v in l["atributos"].items())
                       + ("  \n✅ atende · ❌ não atende · ❔ o site não diz" if l.get("atendimento") else ""))
            st.dataframe(empresas_base(l, nomes), hide_index=True, width="stretch")
    limite()


if (s.tela >= 4 and not s.resultado) or (s.tela in (2, 3) and not s.recorte):
    s.tela = 1
[tela_1, tela_2, tela_3, tela_4, tela_5, tela_6][s.tela - 1]()
