"""Geno — as 6 telas do produto (dono: Christian).

    streamlit run app/app.py

Fala com o motor só pelo contrato 4 (`motor.analisar`) e, quando existir, por
`motor.nicho.propor_recorte` (tela 2). Empresas vêm do motor, que lê da `vw_publico` (LGPD).
Tema e textos são da Mariana (`app/geno/tema.py` e `app/geno/textos.py`).
"""
from __future__ import annotations

import base64
import html
import inspect
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import streamlit as st

APP = Path(__file__).resolve().parent
RAIZ = APP.parent
sys.path[:0] = [str(RAIZ), str(APP)]  # motor/ está na raiz; geno/ (tema e textos) em app/

from geno.tema import (CORES, aplicar_cabecalho, aplicar_tema, aplicar_tema_home, botao_principal,  # noqa: E402
                       caixa_confianca, card_lacuna, divisor)
from geno import graficos  # noqa: E402
from geno.carregamento import animacao  # noqa: E402
from geno.textos import T  # noqa: E402
from motor import embeddings  # noqa: E402
from motor.analisar import analisar, interpretar_saturacao  # noqa: E402

try:
    from motor.nicho import propor_recorte
except ImportError:  # motor sem a parte da tela 2: recorte do arquivo de exemplo
    propor_recorte = None

EXEMPLO = RAIZ / "contratos" / "exemplos" / "resultado_analise.exemplo.json"
LOGO = APP / "geno" / "logo.png"
LOGO_BRANCO = APP / "geno" / "logo_branco.png"
TELAS = ["Ideia", "Nicho", "Análise", "Concorrentes", "Saturação", "Lacunas"]
CANAIS = {"online": "Online", "presencial": "Presencial", "hibrido": "Híbrido",
          "delivery": "Vai até o cliente", "indeterminado": "Não sei / tanto faz"}
SITUACAO = {"ativa": "Ativa", "baixada": "Baixada", "inapta": "Inapta", "suspensa": "Suspensa", "nula": "Nula"}
ATRIBUTO = {"produto_servico": "Serviço", "publico": "Público", "canal": "Canal"}
MARCA = {True: "✅", False: "❌", None: "❔"}
NAO_SEI = "Não sei ainda"
OUTRO = "Outro"
SEPARADOR = "; "  # entre as opções marcadas numa pergunta de múltipla escolha

st.set_page_config(page_title="Geno", page_icon=str(LOGO), layout="wide")


@st.cache_resource(show_spinner=False)
def aquecer_motor() -> bool:
    """Carrega o modelo de embedding quando o app abre, uma vez por processo, de forma síncrona.

    Em segundo plano (thread), dentro do Streamlit, o carregamento levava de 50 a 80 s em vez de ~14 s e
    travava a primeira análise e a animação (04/11/2026). Síncrono, só a primeira visita espera.
    """
    inicio = time.monotonic()
    preparar = getattr(embeddings, "preparar", None)
    if preparar:
        preparar()
    print(f"[app] modelo de embedding pronto em {time.monotonic() - inicio:.1f} s", flush=True)
    return True


aplicar_tema()
# Linha do tempo no topo: as etapas são st.button (clicáveis e acessíveis por teclado) desenhadas
# como bolinhas; a barra verde anima da etapa anterior até a atual (ver linha_do_tempo).
st.markdown(f"""<style>
.geno-topo {{ display: flex; align-items: center; gap: .6rem; }}
.geno-topo img {{ height: 2.75rem; width: auto; }}
.geno-marca {{ font-family: 'Fraunces', Georgia, serif; font-weight: 700; font-size: 1.75rem; color: {CORES["tinta"]}; }}
.geno-slogan {{ font-size: .9rem; opacity: .7; margin-left: .25rem; }}
.st-key-linha {{ position: relative; gap: 0; margin: .2rem 0 0; }}
.st-key-linha [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap; gap: .25rem; }}
.st-key-linha [data-testid="stColumn"] {{ min-width: 0; counter-increment: passo; }}
.st-key-linha .stButton button, .st-key-linha .stButton button:hover, .st-key-linha .stButton button:disabled {{
    flex-direction: column; background: transparent; border: none; border-radius: 8px; padding: 0;
    min-height: 0; box-shadow: none; opacity: 1; color: {CORES["tinta"]}; font-weight: 600; }}
.st-key-linha .stButton button::before {{
    content: counter(passo); position: relative; z-index: 1; display: flex; align-items: center;
    justify-content: center; width: 2.25rem; height: 2.25rem; margin: 0 auto .4rem; border-radius: 50%;
    background: {CORES["creme"]}; border: 2px solid {CORES["floresta"]}; color: {CORES["floresta"]};
    font-weight: 700; transition: transform .2s; }}
.st-key-linha .stButton button:not(:disabled):hover::before {{ transform: scale(1.08); }}
.st-key-linha .stButton button[kind="tertiary"]::before {{ content: "✓"; background: {CORES["floresta"]}; color: #fff; }}
.st-key-linha .stButton button[kind="primary"]::before {{
    background: {CORES["floresta"]}; color: #fff; box-shadow: 0 0 0 5px rgba(31,111,92,.18);
    animation: geno-pulso .6s ease-out; }}
.st-key-linha .stButton button[kind="primary"] p {{ color: {CORES["floresta"]}; }}
.st-key-linha .stButton button:disabled {{ cursor: not-allowed; }}
.st-key-linha .stButton button:disabled:not([kind="tertiary"])::before {{ border-style: dashed; opacity: .5; }}
.st-key-linha .stButton button:disabled:not([kind="tertiary"]) p {{ opacity: .5; }}
.st-key-linha .stButton button:focus-visible {{ outline: 2px solid {CORES["floresta"]}; outline-offset: 4px; }}
.geno-trilho {{ position: absolute; top: 1.125rem; left: 8.33%; right: 8.33%; height: 3px;
    transform: translateY(-50%); background: {CORES["areia"]}; border-radius: 3px; }}
.geno-cheio {{ height: 100%; background: {CORES["floresta"]}; border-radius: 3px;
    animation-duration: .7s; animation-timing-function: ease-in-out; }}
@keyframes geno-pulso {{ 0% {{ transform: scale(.7); }} 60% {{ transform: scale(1.15); }} 100% {{ transform: scale(1); }} }}
@media (prefers-reduced-motion: reduce) {{ .geno-cheio, .st-key-linha .stButton button::before {{ animation: none; }} }}
@media (max-width: 640px) {{
    .geno-slogan {{ display: none; }}
    .stMainBlockContainer {{ padding-top: 11rem; }}
    /* some da tela, mas o leitor de tela continua lendo o nome da etapa */
    .st-key-linha .stButton button p {{ position: absolute; width: 1px; height: 1px; overflow: hidden;
        clip: rect(0 0 0 0); white-space: nowrap; }} }}
</style>""", unsafe_allow_html=True)

# Primeira abertura do servidor: o modelo de embedding leva ~20 s para carregar; a constelação aparece
# enquanto isso (as próximas visitas já encontram o modelo pronto e pulam este bloco)
if not getattr(embeddings, "pronto", lambda: True)():
    animacao()
    st.markdown(f'<div class="geno-carga"><div class="geno-carga-etapa">{T.CARGA_PREPARANDO}</div>'
                f'<div class="geno-carga-sub">{T.CARGA_PREPARANDO_SUB}</div></div>', unsafe_allow_html=True)
    aquecer_motor()
    st.rerun()
s = st.session_state
for chave, valor in {"tela": 1, "ideia": "", "recorte": None, "respostas": {}, "resultado": None, "erro": None}.items():
    s.setdefault(chave, valor)


def ir(tela: int):
    s.tela_anterior, s.tela = s.tela, tela
    s.rolar_topo = s.get("rolar_topo", 0) + 1  # a próxima tela abre do topo
    st.rerun()


def rolar_para_o_topo():
    """Leva a página ao topo depois de trocar de tela (o Streamlit mantém a rolagem da tela anterior).

    Um iframe minúsculo com um script que rola a página do app; o número muda a cada troca para o
    navegador recarregar o iframe e rodar o script de novo.
    """
    st.container(key="rolar_topo").iframe(f"""<script>/* {s.rolar_topo} */
      const d = window.parent.document;
      for (const el of [d.querySelector('[data-testid="stMain"]'), d.querySelector('.stMain'), d.scrollingElement])
        if (el) el.scrollTo({{top: 0}});
      window.parent.scrollTo(0, 0);
    </script>""", height=1)


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


# --- topo: logo e linha do tempo -----------------------------------------------------------------
def linha_do_tempo():
    logo = base64.b64encode(LOGO.read_bytes()).decode()
    cabecalho_fixo = st.container(key="cabecalho")
    c_logo, c_linha = cabecalho_fixo.columns([1, 3.4], vertical_alignment="center")
    c_logo.markdown(f'<div class="geno-topo"><img src="data:image/png;base64,{logo}" alt="">'
                f'<span class="geno-marca">Geno</span><span class="geno-slogan">O mercado da sua ideia</span></div>',
                unsafe_allow_html=True)
    aplicar_cabecalho()
    anterior = s.get("tela_anterior", s.tela)
    de, para = (100 * (t - 1) / (len(TELAS) - 1) for t in (anterior, s.tela))
    # O Streamlit reaproveita o elemento e só troca o estilo; um nome de animação novo a cada troca
    # de tela é o que faz o navegador reiniciá-la.
    nome = f"geno-enche-{anterior}-{s.tela}"
    with c_linha.container(key="linha"):
        st.markdown(f'<style>@keyframes {nome} {{ from {{ width: {de}%; }} to {{ width: {para}%; }} }}</style>'
                    f'<div class="geno-trilho"><div class="geno-cheio" style="width:{para}%;animation-name:{nome}">'
                    '</div></div>', unsafe_allow_html=True)
        for i, (coluna, nome) in enumerate(zip(st.columns(len(TELAS)), TELAS), 1):
            liberada = i == 1 or (i == 2 and s.recorte) or (i >= 4 and s.resultado)
            tipo = "primary" if i == s.tela else "tertiary" if i < s.tela else "secondary"
            if coluna.button(nome, key=f"nav{i}", disabled=not liberada, type=tipo, width="stretch"):
                ir(i)


def limite():
    st.markdown(f'<div class="geno-limite">{T.LIMITE_DEMANDA}</div>', unsafe_allow_html=True)


# --- telas ---------------------------------------------------------------------------------------
def tela_1():
    # Página inicial: só logo, slogan e a caixa da ideia, centralizados sobre o fundo escuro
    aplicar_tema_home()
    logo = base64.b64encode(LOGO_BRANCO.read_bytes()).decode()  # versão branca, com o foguete laranja
    st.markdown(f'<div class="geno-home-logo"><img src="data:image/png;base64,{logo}" alt="">'
                '<span>Geno</span></div>', unsafe_allow_html=True)
    st.title(T.TITULO)
    st.markdown(f'<p class="geno-home-explica">{T.HOME_EXPLICACAO}</p>', unsafe_allow_html=True)
    with st.container(key="caixa"):
        ideia = st.text_area(T.CAMPO_IDEIA_LABEL, s.ideia, height=76, placeholder=T.CAMPO_IDEIA_PLACEHOLDER,
                             label_visibility="collapsed")
    analisar_clicado = botao_principal(T.BOTAO_ANALISAR, "analisar")  # abaixo da caixa, centralizado
    if analisar_clicado:
        if not ideia.strip():
            st.error(T.ERRO_IDEIA_VAZIA)
            return
        if len(ideia.strip()) < 10:
            st.error(T.ERRO_IDEIA_CURTA)
            return
        s.ideia, s.respostas, s.resultado = ideia.strip(), {}, None
        texto = s.ideia
        iniciar_carga("recorte", lambda carga: sugerir_recorte(texto))


def tela_2():
    r, a = s.recorte, s.recorte["atributos"]
    if r.get("no_piloto") is False:  # ideia de outro ramo: avisa e não analisa
        st.title(T.FORA_DO_PILOTO_TITULO)
        st.markdown(f"**Sua ideia:** _{s.ideia}_")
        st.markdown(f'<div class="geno-leitura"><p>{T.FORA_DO_PILOTO}</p></div>', unsafe_allow_html=True)
        if navegacao(None, T.BOTAO_OUTRA_IDEIA, "fora_do_piloto"):
            nova_ideia()
        return
    st.title(T.RECORTE_TITULO)
    st.markdown(f"**Sua ideia:** _{s.ideia}_")
    if r.get("falhou"):
        st.warning("Não conseguimos sugerir o nicho agora. Preencha os campos abaixo com suas palavras.")
    elif r.get("descricao"):
        with st.container(border=True):
            st.markdown(f"### {r['descricao']}")

    divisor("Ajuste o recorte")
    st.caption(T.RECORTE_AJUDA)
    canais = list(CANAIS)
    with st.container(key="campos_recorte"):  # empilhados e alinhados à esquerda: o texto do serviço cabe inteiro
        editado = {
            "produto_servico": st.text_input(T.RECORTE_PRODUTO, a.get("produto_servico", "")).strip(),
            "publico": st.text_input(T.RECORTE_PUBLICO, a.get("publico", "")).strip(),
            "canal": st.selectbox(T.RECORTE_CANAL, canais, format_func=CANAIS.get,
                                  index=canais.index(a["canal"]) if a.get("canal") in CANAIS else canais.index("indeterminado")),
        }
    st.caption(f"**{T.RECORTE_GEOGRAFIA}:** {T.RECORTE_GEOGRAFIA_PADRAO}")

    respostas = {}
    if r.get("perguntas"):
        divisor(T.AFUNILAR_INTRO)
        st.caption(T.AFUNILAR_OPCIONAL)
        total = len(r["perguntas"])
        for atual_i, p in enumerate(r["perguntas"], 1):
            if total > 1:
                st.caption(T.AFUNILAR_RODADA.format(atual=atual_i, total=total))
            resposta = pergunta(p)
            if resposta:
                respostas[p["pergunta"]] = resposta

    # Um botão só: com respostas, o recorte é refinado antes de analisar; sem elas, analisa como está
    if navegacao(1, T.BOTAO_CONFIRMAR_RECORTE, "recorte"):
        confirmar(editado, respostas)


def pergunta(p: dict) -> str | None:
    """Uma pergunta da tela 2, como as do Claude: escolha única (rádio) ou várias (caixas), sempre com
    "Outro" e texto livre. Devolve a resposta em texto (várias separadas por "; ") ou None."""
    opcoes = [o for o in p["opcoes"] if o != NAO_SEI] + [OUTRO] + [NAO_SEI]
    conhecidas = set(opcoes) - {OUTRO}
    chave = f"perg_{abs(hash(p['pergunta']))}"  # muda quando o recorte traz outra pergunta
    anterior = s.respostas.get(p["pergunta"]) or ""
    if p.get("multipla"):
        marcadas_antes = [x for x in anterior.split(SEPARADOR) if x]
        livre_antes = SEPARADOR.join(x for x in marcadas_antes if x not in conhecidas)
        st.markdown(f'<p class="geno-pergunta">{html.escape(p["pergunta"])}</p>'
                    f'<p class="geno-pergunta-ajuda">{T.AFUNILAR_VARIAS}</p>', unsafe_allow_html=True)
        marcadas = [o for j, o in enumerate(opcoes)
                    if st.checkbox(o, value=(o in marcadas_antes) or (o == OUTRO and bool(livre_antes)), key=f"{chave}_{j}")]
        livre = ""
        if OUTRO in marcadas:
            livre = st.text_input(T.AFUNILAR_OUTRO, livre_antes, key=f"{chave}_outro",
                                  placeholder=T.AFUNILAR_OUTRO_EXEMPLO).strip()
        partes = [o for o in marcadas if o not in (OUTRO, NAO_SEI)] + ([livre] if livre else [])
        return SEPARADOR.join(partes) or None
    indice = opcoes.index(anterior) if anterior in conhecidas else (opcoes.index(OUTRO) if anterior else None)
    escolha = st.radio(p["pergunta"], opcoes, index=indice, key=chave)
    if escolha == OUTRO:
        livre = st.text_input(T.AFUNILAR_OUTRO, "" if anterior in conhecidas else anterior, key=f"{chave}_outro",
                              placeholder=T.AFUNILAR_OUTRO_EXEMPLO).strip()
        return livre or None
    return None if escolha in (None, NAO_SEI) else escolha


def confirmar(editado: dict, respostas: dict):
    if not editado["produto_servico"]:
        st.error("Diga o que você vai oferecer.")
        return
    mudou = {k: v for k, v in editado.items() if v != s.recorte["atributos"].get(k)}
    if respostas:
        s.respostas = s.respostas | respostas
        texto, todas = s.ideia, dict(s.respostas)
        iniciar_carga("refinar", lambda carga: sugerir_recorte(texto, todas), mudou=mudou)
    aplicar_recorte(s.recorte, mudou)


def aplicar_recorte(r: dict, mudou: dict):
    """Guarda o recorte (com o que a pessoa editou à mão por cima) e vai para a análise."""
    r = r | {"atributos": r["atributos"] | mudou}
    if mudou or not r.get("descricao"):
        at = r["atributos"]
        canal = "" if at["canal"] == "indeterminado" else CANAIS[at["canal"]]
        r["descricao"] = " · ".join(x for x in (at["produto_servico"], at["publico"], canal) if x)
    s.recorte, s.resultado, s.erro = r, None, None
    s.pop("carga", None)  # análise de um recorte antigo, se a pessoa saiu da tela 3 no meio
    ir(3)


def tela_3():
    if s.erro:
        st.title(T.PROGRESSO_TITULO)
        st.caption(s.recorte["descricao"])
        st.error(T.ERRO_SERVICO)
        with st.expander("Detalhe do erro"):
            st.code(s.erro)
        c1, c2, c3 = st.columns(3)
        with c1:
            tentar = botao_principal(T.BOTAO_TENTAR_NOVAMENTE, "tentar")
        if tentar:
            s.erro = None
            st.rerun()
        if c2.button("Voltar e ajustar", width="stretch"):
            ir(2)
        if c3.button("Ver com dados de exemplo", width="stretch", help="Empresas e números fictícios."):
            s.resultado, s.erro = exemplo() | {"ideia": s.ideia}, None
            ir(4)
        return

    if "carga" not in s:
        texto, recorte = s.ideia, s.recorte
        iniciar_carga("analise", lambda carga: _analisar(texto, recorte, carga))
    tela_carga()


# --- carregamento: a constelação no meio da página, com a etapa por baixo ------------------------
# A tarefa roda numa thread; só o texto (um fragment) se redesenha a cada 0,3 s, e a animação, que
# fica fora do fragment, não reinicia. A etapa vem do motor (análise) ou do relógio (recorte).
ETAPA_MIN_S = 0.9
SUBTITULO_CARGA = {"refinar": "Afinando o recorte com as suas respostas"}  # no recorte vai a própria ideia


def iniciar_carga(tipo: str, tarefa, **extra):
    carga = {"tipo": tipo, "etapas": [], "mostrada": (-1, 0.0), "inicio": time.monotonic(), **extra}
    carga["futuro"] = ThreadPoolExecutor(1).submit(tarefa, carga)
    s.carga = carga
    st.rerun()


def _analisar(ideia: str, recorte: dict, carga: dict) -> dict:
    """Chama o motor avisando as etapas reais, se ele souber avisar (o motor de exemplo dos testes não sabe)."""
    if "progresso" in inspect.signature(analisar).parameters:
        return analisar(ideia, recorte, progresso=carga["etapas"].append)
    return analisar(ideia, recorte)


def tela_carga():
    animacao()
    texto_da_carga()


@st.fragment(run_every=0.3)
def texto_da_carga():
    c = s.get("carga")
    if not c:
        return
    if not c["futuro"].done():
        # cada etapa real fica pelo menos ETAPA_MIN_S na tela, em ordem, para dar tempo de ler
        i, desde = c["mostrada"]
        agora = time.monotonic()
        if i < len(c["etapas"]) - 1 and (i < 0 or agora - desde >= ETAPA_MIN_S):
            c["mostrada"] = (i := i + 1, agora)
        if i >= 0:
            etapa = c["etapas"][i]
        elif c["tipo"] == "analise":
            etapa = "Preparando a análise"
        else:  # uma chamada só ao LLM: as frases são estimadas pelo tempo, não etapas reais
            frases = T.CARGA_RECORTE_ETAPAS
            etapa = frases[min(int((time.monotonic() - c["inicio"]) // 1.6), len(frases) - 1)]
        if c["tipo"] == "recorte":
            sub = f"“{s.ideia}”"
        else:
            sub = SUBTITULO_CARGA.get(c["tipo"]) or (s.recorte or {}).get("descricao", "")
        st.markdown(f'<div class="geno-carga"><div class="geno-carga-etapa">{html.escape(etapa)}</div>'
                    f'<div class="geno-carga-sub">{html.escape(sub)}</div></div>', unsafe_allow_html=True)
        return
    s.pop("carga")
    try:
        resultado = c["futuro"].result()
    except Exception as e:  # sugerir_recorte já trata as próprias falhas; isto é da análise
        s.erro = f"{type(e).__name__}: {e}"
        st.rerun()
    if c["tipo"] == "recorte":
        s.recorte = resultado
        ir(2)
    elif c["tipo"] == "refinar":
        aplicar_recorte(s.recorte if resultado.get("falhou") else resultado, c["mudou"])
    else:
        s.resultado = resultado
        ir(4)


# --- navegação no fim das telas: Voltar à esquerda, Seguir à direita, igual em todas -------------
def navegacao(voltar: int | None, rotulo_seguir: str | None, chave: str) -> bool:
    """Botões do fim da tela. Devolve True quando a pessoa clica em seguir."""
    divisor()
    with st.container(key="navegacao"):
        c1, c2 = st.columns(2, gap="medium")
        if voltar and c1.button(T.BOTAO_VOLTAR, key=f"voltar_{chave}", width="stretch", icon=":material/arrow_back:"):
            ir(voltar)
        with c2:
            return bool(rotulo_seguir) and botao_principal(rotulo_seguir, f"seguir_{chave}")


def nova_ideia():
    s.ideia, s.recorte, s.resultado, s.respostas, s.erro = "", None, None, {}, None
    ir(1)


def cabecalho():
    r = s.resultado
    if "_aviso" in r:
        st.error("**Dados de exemplo:** empresas e números fictícios, só para ver as telas.", icon="🧪")
    c1, c2 = st.columns([3, 1.2], vertical_alignment="center")
    c1.markdown(f"**Sua ideia:** _{r['ideia']}_  \n**Recorte:** {r['recorte']['descricao']}")
    if c2.button(f"✏️ {T.BOTAO_AJUSTAR_IDEIA}", width="stretch"):
        ir(2)
    conf = r["confianca"]
    # o texto vem do motor (contrato 4): escapado porque o tema o põe dentro de HTML
    caixa_confianca(conf["nivel"] if conf["nivel"] in ("alta", "media", "baixa") else "baixa", html.escape(conf["texto"]))
    divisor()


def tela_4():
    cabecalho()
    st.title(T.CONCORRENTES_TITULO)
    cs = s.resultado["concorrentes"]
    if not cs:
        st.info(T.CONCORRENTES_VAZIO)
        return
    ativas = sum(c["situacao"] == "ativa" for c in cs)
    m1, m2, m3 = st.columns(3)
    m1.metric("Mais parecidas", len(cs))
    m2.metric("Ativas", ativas)
    m3.metric("Não ativas na Receita", len(cs) - ativas)
    divisor("As mais parecidas com a sua ideia")
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
        divisor()
        with st.expander("Em comum com eles e possíveis diferenciais", expanded=True):
            st.markdown("\n\n".join(f"**{t}:** {v}" for t, v in partes))


def tela_5():
    cabecalho()
    st.title(T.SATURACAO_TITULO)
    sat = s.resultado["saturacao"]
    if not sat.get("anos"):
        st.info("Não há dados de aberturas e baixas para este recorte.")
        return
    saldo = sat["total_aberturas"] - sat["total_baixas"]
    leitura = sat.get("interpretacao") or interpretar_saturacao(sat, s.resultado["confianca"]["n_empresas"])
    if leitura.get("titulo"):  # o que os números querem dizer, antes dos números
        st.markdown(f'<div class="geno-leitura"><div class="geno-leitura-rotulo">{T.SATURACAO_LEITURA}</div>'
                    f'<h3>{html.escape(leitura["titulo"])}</h3>'
                    + "".join(f"<p>{html.escape(p)}</p>" for p in leitura["paragrafos"]) + "</div>",
                    unsafe_allow_html=True)
    cnaes_ideia = set(s.resultado["recorte"].get("cnaes") or s.recorte.get("cnaes") or [])
    if sat.get("comparativo"):  # o nicho da ideia contra os outros nichos de ensino do piloto
        divisor(T.SAT_COMPARATIVO)
        st.caption(T.SAT_COMPARATIVO_AJUDA)
        st.markdown(graficos.barras_horizontais(
            [{"nome": c["nome"] + (" (sua ideia)" if c["cnae"] in cnaes_ideia else ""), "valor": c["razao"] * 10,
              "destaque": c["cnae"] in cnaes_ideia} for c in sat["comparativo"]],
            formato=lambda v: f"{v:.1f}".replace(".", ","), rotulo=T.SAT_COMPARATIVO), unsafe_allow_html=True)
    divisor(T.SAT_ANO_A_ANO)
    st.markdown(graficos.barras_anuais(sat["anos"], sat["aberturas"], sat["baixas"]), unsafe_allow_html=True)
    periodo = f"{sat['anos'][0]}–{sat['anos'][-1]}"
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Aberturas ({periodo})", num(sat["total_aberturas"]))
    c2.metric(f"Baixas ({periodo})", num(sat["total_baixas"]))
    c3.metric("Saldo no período", ("+" if saldo > 0 else "") + num(saldo))
    if len(sat.get("sobrevivencia") or []) > 1:
        sob = sat["sobrevivencia"]
        divisor(T.SAT_SOBREVIVENCIA)
        st.caption(T.SAT_SOBREVIVENCIA_AJUDA.format(ano=sob[0]["ano"], pct=num(round(sob[0]["pct_ativos"]))))
        st.markdown(graficos.linha_sobrevivencia(sob), unsafe_allow_html=True)
    if sat.get("municipios") or (sat.get("porte") or {}).get("total"):
        divisor(T.SAT_ONDE_QUEM)
        c1, c2 = st.columns(2, gap="large")
        if sat.get("municipios"):
            c1.markdown(f'<div class="geno-secao-menor">{T.SAT_MUNICIPIOS}</div>' + graficos.barras_horizontais(
                [{"nome": m["municipio"], "valor": m["ativos"], "destaque": i == 0}
                 for i, m in enumerate(sat["municipios"])],
                rotulo=T.SAT_MUNICIPIOS, cor_destaque=CORES["menta"], cor_neutra="rgba(143,211,189,.45)",
                largura=380, x_barras=140),
                unsafe_allow_html=True)
        porte = sat.get("porte") or {}
        if porte.get("total"):
            outros = porte["total"] - porte["mei"]
            c2.markdown(f'<div class="geno-secao-menor">{T.SAT_PORTE}</div>' + graficos.rosca(
                porte["mei"], porte["total"], T.SAT_PORTE,
                [f"{num(porte['mei'])} MEIs", "profissionais autônomos",
                 f"{num(outros)} empresas", "fora do MEI"]), unsafe_allow_html=True)
    divisor()
    if s.resultado["confianca"].get("usou_setor_amplo"):
        st.info("Estes números são do setor inteiro (CNAE), não só do seu nicho.")
    st.caption(f"{T.BAIXA_CNPJ_AVISO} Fonte: {sat['fonte']}")


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
        return
    nomes = {c["cnpj"]: c["nome_exibicao"] for c in s.resultado["concorrentes"]} | (s.resultado.get("nomes_empresas") or {})
    da_ideia = [l for l in lacunas if l.get("origem", "ideia") == "ideia"]
    variacoes = sorted((l for l in lacunas if l.get("origem") == "variacao"),
                       key=lambda l: l["n_empresas_que_oferecem"] / max(1, l["n_empresas_analisadas"]))
    if da_ideia:
        lista_lacunas(da_ideia, nomes, primeira_em_card=True)
    else:
        st.info(T.LACUNA_IDEIA_COMUM)
    if variacoes:  # variações propostas pelo LLM; quem diz que são raras é a contagem
        divisor(T.LACUNA_VARIACOES)
        st.caption(T.LACUNA_VARIACOES_AJUDA)
        lista_lacunas(variacoes, nomes, primeira_em_card=False)


def lista_lacunas(lacunas: list[dict], nomes: dict, primeira_em_card: bool):
    for i, l in enumerate(lacunas):
        t = l["titulo"]
        # minúscula no começo só quando a segunda letra também é minúscula (não estraga siglas: "IA", "TI")
        combinacao = t[:1].lower() + t[1:] if len(t) > 1 and t[1].islower() else t
        k = l["n_empresas_que_oferecem"]
        frase = (T.LACUNA_FRASE if k == 0 else T.LACUNA_FRASE_POUCAS).format(
            n=l["n_empresas_analisadas"], k=k, combinacao=combinacao)
        if k == 1:
            frase = frase.replace("oferecem", "oferece")
        if l.get("base_pequena"):
            frase += " " + T.LACUNA_BASE_PEQUENA
        if i:
            divisor()
        if i == 0 and primeira_em_card:  # o título vem do LLM: escapado porque o card é HTML
            card_lacuna(html.escape(l["titulo"]), html.escape(frase))
        else:
            st.markdown(f'<div class="geno-lacuna-linha"><b>{html.escape(l["titulo"])}</b>'
                        f'<span>{html.escape(frase)}</span></div>', unsafe_allow_html=True)
        n_base = len(l["cnpjs_base"])
        rotulo = "Ver a empresa analisada" if n_base == 1 else T.LACUNA_VER_EMPRESAS.format(n=n_base)
        with st.expander(rotulo):
            st.caption(T.LACUNA_EMPRESAS_AJUDA + "  \n" + " · ".join(f"{ATRIBUTO[a]}: {v}" for a, v in l["atributos"].items())
                       + ("  \n✅ atende · ❌ não atende · ❔ o site não diz" if l.get("atendimento") else ""))
            st.dataframe(empresas_base(l, nomes), hide_index=True, width="stretch")


if (s.tela >= 4 and not s.resultado) or (s.tela in (2, 3) and not s.recorte):
    s.tela = 1
if s.get("rolar_topo"):
    rolar_para_o_topo()
if s.tela > 1:  # a página inicial não mostra o progresso
    linha_do_tempo()
if s.get("carga") and s.carga["tipo"] in ("recorte", "refinar"):
    tela_carga()  # a animação toma o lugar do conteúdo da tela 1 ou 2
else:
    [tela_1, tela_2, tela_3, tela_4, tela_5, tela_6][s.tela - 1]()
    # fim das telas de resultado: Voltar e Seguir na mesma posição em todas
    if s.tela == 4 and navegacao(2, T.BOTAO_VER_SATURACAO, "concorrentes"):
        ir(5)
    elif s.tela == 5 and navegacao(4, T.BOTAO_VER_LACUNAS, "saturacao"):
        ir(6)
    elif s.tela == 6 and navegacao(5, T.BOTAO_NOVA_IDEIA, "lacunas"):
        nova_ideia()
    if s.tela >= 4:
        limite()
    elif s.tela == 2:
        st.markdown(f'<div class="geno-limite">{T.RODAPE}</div>', unsafe_allow_html=True)
