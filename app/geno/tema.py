"""Identidade visual do Geno para Streamlit: floresta à noite (dono: Micael; paleta da Mariana).

Todas as telas usam o fundo verde-escuro com brilho e campo de pontos (um por empresa). A linha do
tempo fica num cabeçalho fixo de vidro bege (app.linha_do_tempo). Texto claro, campos translúcidos e
seções separadas por linhas finas (divisor()).

Uso, logo no começo do app (depois de st.set_page_config):

    from geno.tema import aplicar_tema
    aplicar_tema()
"""
from pathlib import Path

import streamlit as st

# Paleta (mesma do config.toml e da apresentação do pitch)
CORES = {
    "floresta": "#1F6F5C",
    "floresta_escura": "#134A3D",
    "noite": "#0F3D33",   # fundo das telas
    "menta": "#8FD3BD",   # verde claro, legível sobre o fundo escuro
    "coral": "#E8613C",   # destaque: botões e a lacuna, o que ninguém atende
    "creme": "#FAF3E7",
    "areia": "#F0E3C8",
    "tinta": "#17261F",
}

# Os 3 níveis do indicador de confiança, sobre o fundo escuro: faixa translúcida e borda na cor do nível
CONFIANCA = {
    "alta": {"fundo": "rgba(143,211,189,.12)", "borda": "#8FD3BD", "texto": "#FAF3E7"},
    "media": {"fundo": "rgba(240,190,90,.12)", "borda": "#F0BE5A", "texto": "#FAF3E7"},
    "baixa": {"fundo": "rgba(232,97,60,.14)", "borda": "#E8613C", "texto": "#FAF3E7"},
}

_LINHA = "rgba(250,243,231,.16)"   # divisórias e bordas
_CAMPO = "rgba(250,243,231,.06)"   # fundo dos campos

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&display=swap');

/* Fundo: floresta à noite, em todas as telas */
.stApp {{
    background-color: {CORES["noite"]};
    background-image: radial-gradient(circle at 50% 20%, rgba(31,111,92,.35) 0, rgba(15,61,51,0) 60%),
                      radial-gradient(rgba(250,243,231,.09) 1.2px, transparent 1.5px);
    background-size: 100% 100%, 18px 18px;
    background-attachment: fixed;
    color: {CORES["creme"]};
}}
header[data-testid="stHeader"] {{ background: transparent; }}
.stMainBlockContainer {{ max-width: 1080px; padding-top: 8rem; padding-bottom: 5rem; }}

/* Texto maior */
html, body, [class*="css"], .stMarkdown, .stTextInput, .stTextArea, .stButton, .stRadio, .stSelectbox {{
    font-family: 'Manrope', sans-serif;
}}
.stApp p, .stApp li, .stMarkdown {{ font-size: 1.12rem; line-height: 1.65; }}
h1, h2, h3 {{
    font-family: 'Fraunces', Georgia, serif !important;
    letter-spacing: -0.02em;
    color: {CORES["creme"]} !important;
}}
.stApp h1 {{ font-size: clamp(2.3rem, 4.6vw, 3.4rem) !important; font-weight: 700 !important; line-height: 1.08;
    margin: .2rem 0 1.4rem; }}
.stApp h3 {{ font-size: 1.5rem !important; font-weight: 600 !important; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
    color: rgba(250,243,231,.7) !important; font-size: 1rem !important; }}

/* Seções separadas por linhas finas */
.geno-divisor {{ height: 1px; background: {_LINHA}; margin: 2.4rem 0 2rem; border: none; }}
.geno-secao {{ font-family: 'Fraunces', Georgia, serif; font-size: 1.35rem; font-weight: 600;
    color: {CORES["creme"]}; margin: 0 0 1rem; }}

/* Botão principal (componente botao_principal): contorno menta que vira coral cheio no hover, com seta */
[class*="st-key-bp_"] .stButton button {{
    min-height: 3.25rem; padding: 0 1.4rem; border-radius: 16px; gap: .7rem;
    background: rgba(15,61,51,.45); color: {CORES["creme"]}; border: none;
    box-shadow: 0 0 0 1.5px rgba(143,211,189,.75); font-weight: 800; font-size: 1.05rem; letter-spacing: .01em;
    transition: background .18s, box-shadow .18s, transform .18s cubic-bezier(.2,.8,.2,1);
}}
[class*="st-key-bp_"] .stButton button::after {{
    content: ""; width: 1.15rem; height: 1.15rem; flex: none; background: {CORES["menta"]};
    -webkit-mask: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12h14M13 6l6 6-6 6'/%3E%3C/svg%3E\") center / contain no-repeat; mask: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12h14M13 6l6 6-6 6'/%3E%3C/svg%3E\") center / contain no-repeat;
    transition: transform .25s cubic-bezier(.2,.8,.2,1), background .18s;
}}
[class*="st-key-bp_"] .stButton button:hover {{
    background: {CORES["coral"]}; color: #fff; box-shadow: 0 0 0 1.5px {CORES["coral"]}, 0 12px 26px rgba(232,97,60,.35);
}}
[class*="st-key-bp_"] .stButton button:hover::after {{ background: #fff; transform: translateX(4px); }}
[class*="st-key-bp_"] .stButton button:active {{ transform: scale(.97); }}
[class*="st-key-bp_"] .stButton button:focus-visible {{ outline: 2px solid {CORES["menta"]}; outline-offset: 4px; }}
@media (prefers-reduced-motion: reduce) {{ [class*="st-key-bp_"] .stButton button, [class*="st-key-bp_"] .stButton button::after {{ transition: none; }} }}

/* Botões */
.stButton button {{ font-size: 1.05rem; min-height: 3rem; border-radius: 999px; font-weight: 700; }}
.stButton button[kind="primary"] {{ background: {CORES["coral"]}; border: none; color: #fff; padding: 0 1.6rem; }}
.stButton button[kind="primary"]:hover {{ background: #CF4F2B; color: #fff; }}
.stButton button[kind="secondary"] {{
    background: transparent; border: 1.5px solid rgba(250,243,231,.45); color: {CORES["creme"]}; }}
.stButton button[kind="secondary"]:hover {{ border-color: {CORES["creme"]}; background: rgba(250,243,231,.06);
    color: {CORES["creme"]}; }}
.stButton button:focus-visible {{ outline: 2px solid {CORES["menta"]}; outline-offset: 3px; }}

/* Campos: translúcidos, com borda fina que acende ao focar */
.stTextInput label p, .stSelectbox label p, .stTextArea label p, .stRadio > label p {{
    font-size: 1rem !important; font-weight: 600; color: rgba(250,243,231,.78) !important; }}
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"], [data-testid="stSelectbox"] [role="group"] {{
    background: {_CAMPO} !important; border: 1px solid {_LINHA} !important; border-radius: 14px !important;
    min-height: 3.1rem; transition: border-color .15s, box-shadow .15s; }}
[data-testid="stTextInputRootElement"]:hover, [data-testid="stSelectbox"] [role="group"]:hover {{
    border-color: rgba(250,243,231,.32) !important; }}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stSelectbox"] [role="group"]:focus-within {{
    border-color: {CORES["menta"]} !important; box-shadow: 0 0 0 3px rgba(143,211,189,.18) !important; }}
[data-testid="stTextInputRootElement"] input, [data-testid="stTextAreaRootElement"] textarea,
[data-testid="stSelectbox"] [role="group"] * {{
    color: {CORES["creme"]} !important; font-size: 1.1rem !important; background: transparent !important; }}
[data-testid="stTextInputRootElement"] input {{ padding-left: 1rem; }}
.stRadio [role="radiogroup"] label p {{ font-size: 1.08rem !important; color: {CORES["creme"]} !important; }}
.stRadio [role="radiogroup"] {{ gap: .35rem; }}

.st-key-campos_recorte {{ max-width: 680px; gap: 1.1rem; }}

/* Caixas com borda (recorte da ideia) */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
    border-color: {_LINHA} !important; border-radius: 18px !important; background: rgba(250,243,231,.04); }}

/* Números grandes */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ font-family: 'Fraunces', Georgia, serif !important;
    font-size: 2.6rem !important; font-weight: 700 !important; line-height: 1.1; color: {CORES["creme"]} !important; }}

/* Títulos sem o ícone de link do Streamlit */
[data-testid="stHeaderActionElements"] {{ display: none !important; }}

/* Avisos (info, alerta, erro): faixa translúcida com a borda na cor do tipo, no lugar do azul padrão */
[data-testid="stAlertContainer"] {{ background: rgba(250,243,231,.06) !important; border-radius: 0 14px 14px 0;
    border-left: 4px solid {CORES["menta"]}; }}
[data-testid="stAlertContainer"] * {{ color: {CORES["creme"]} !important; font-size: 1.05rem; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {{ border-left-color: #F0BE5A; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{ border-left-color: {CORES["coral"]};
    background: rgba(232,97,60,.12) !important; }}

/* Opções das perguntas: círculo visível sobre o fundo escuro */
[data-testid="stRadioOption"] > div > div:first-child {{ border: 1.5px solid rgba(250,243,231,.6) !important;
    width: 1.15rem !important; height: 1.15rem !important; }}
[data-testid="stRadioOption"] p {{ font-size: 1.08rem !important; }}
.stCheckbox label p {{ font-size: 1.08rem !important; color: {CORES["creme"]} !important; }}
[data-testid="stCheckbox"] label > div:not([data-testid]) {{ border: 1.5px solid rgba(250,243,231,.6) !important;
    width: 1.15rem !important; height: 1.15rem !important; border-radius: 5px !important; }}
[data-testid="stCheckbox"] label {{ align-items: center; }}
.geno-pergunta {{ font-size: 1rem !important; font-weight: 600; color: rgba(250,243,231,.78); margin: 0; }}
.geno-pergunta-ajuda {{ font-size: .92rem !important; color: rgba(250,243,231,.55); margin: 0 0 .3rem; }}
.st-key-bp_confirmar {{ max-width: 340px; }}
[data-testid="stMetricLabel"] p {{ font-size: 1rem !important; color: rgba(250,243,231,.72) !important; }}
[data-testid="stColumn"]:has(> div > div > [data-testid="stMetric"]) + [data-testid="stColumn"] {{
    border-left: 1px solid {_LINHA}; padding-left: 1.4rem; }}

/* Expansores e tabelas */
[data-testid="stExpander"] details {{ border: 1px solid {_LINHA}; border-radius: 16px; background: rgba(250,243,231,.03); }}
[data-testid="stExpander"] summary p {{ font-size: 1.1rem !important; font-weight: 700; }}
[data-testid="stDataFrame"] {{ border: 1px solid {_LINHA}; border-radius: 14px; overflow: hidden; }}

/* Barra de progresso */
.stProgress > div > div > div > div {{ background-color: {CORES["coral"]}; }}
.stProgress p {{ font-size: 1.1rem !important; }}
.stApp [data-testid="stSpinner"], .stApp [data-testid="stSpinner"] p {{ color: {CORES["creme"]}; }}

/* Card da lacuna: o herói da tela de resultado, claro sobre o fundo escuro */
.geno-lacuna {{
    background: {CORES["creme"]}; color: {CORES["tinta"]};
    border-left: 6px solid {CORES["coral"]}; border-radius: 0 18px 18px 0;
    padding: 1.4rem 1.6rem; box-shadow: 0 18px 44px rgba(4,20,16,.4); margin: 1rem 0 1.4rem;
    font-size: 1.12rem;
}}
.geno-lacuna h3 {{ margin: 0 0 .5rem 0; color: {CORES["coral"]} !important; }}

/* Indicador de confiança */
.geno-confianca {{
    border-radius: 0 14px 14px 0; padding: 1rem 1.3rem; border-left: 4px solid;
    margin: 1rem 0 0; font-size: 1.08rem; line-height: 1.55;
}}

/* Linha fixa de limite (oferta, não demanda) */
.geno-limite {{ font-size: .98rem; color: rgba(250,243,231,.62); margin-top: 3rem; text-align: center;
    padding-top: 1.6rem; border-top: 1px solid {_LINHA}; }}
</style>
"""

# Cabeçalho fixo de vidro bege com o logo e a linha do tempo (telas 2 a 6)
_CSS_CABECALHO = f"""
<style>
/* Pílula de vidro que flutua sem encostar no topo; o conteúdo rola por baixo */
.st-key-cabecalho {{
    position: fixed; top: 14px; left: 50%; transform: translateX(-50%); z-index: 999991;
    width: min(1080px, calc(100% - 32px)); padding: .45rem 1.6rem .3rem 1rem; border-radius: 999px;
    background: rgba(250,243,231,.80);
    backdrop-filter: blur(18px) saturate(170%); -webkit-backdrop-filter: blur(18px) saturate(170%);
    border: 1px solid rgba(255,255,255,.7);
    box-shadow: 0 14px 34px rgba(4,20,16,.35), inset 0 1px 0 rgba(255,255,255,.9), inset 0 -1px 0 rgba(23,38,31,.08);
}}
.st-key-cabecalho .geno-slogan {{ display: none; }}
@media (max-width: 640px) {{ .st-key-cabecalho {{ border-radius: 28px; padding: .5rem .8rem; }} }}
.st-key-cabecalho, .st-key-cabecalho p, .st-key-cabecalho .geno-slogan {{ color: {CORES["tinta"]}; }}
.st-key-cabecalho p {{ font-size: .95rem; }}
header[data-testid="stHeader"] {{ display: none; }}
</style>
"""

# Página inicial: sem cabeçalho, conteúdo centralizado e a caixa da ideia em destaque
_CSS_HOME = f"""
<style>
.stApp {{ background-image: radial-gradient(circle at 50% 38%, rgba(31,111,92,.95) 0, rgba(15,61,51,0) 62%),
                            radial-gradient(rgba(250,243,231,.16) 1.2px, transparent 1.5px); }}
.stMainBlockContainer {{ max-width: 760px; padding-top: 14vh; padding-bottom: 6rem; }}
.st-key-bp_analisar {{ max-width: 280px; margin: 1.4rem auto 0; }}
.geno-home-logo {{ display: flex; justify-content: center; align-items: center; gap: .8rem; margin-bottom: 1.6rem; }}
.geno-home-logo img {{ height: 4.2rem; width: auto; }}
.geno-home-logo span {{ font-family: 'Fraunces', Georgia, serif; font-weight: 700; font-size: 3rem;
    color: {CORES["creme"]}; letter-spacing: -0.02em; }}
.stApp h1 {{ text-align: center; font-size: clamp(2.1rem, 5.2vw, 3.3rem) !important; line-height: 1.1;
    margin-bottom: 2.2rem; }}
.st-key-caixa {{
    background: {CORES["creme"]}; border-radius: 26px; padding: .7rem .7rem .7rem 1.2rem;
    box-shadow: 0 24px 60px rgba(4,20,16,.45);
}}
.st-key-caixa [data-baseweb="textarea"], .st-key-caixa [data-testid="stTextArea"] * {{
    background: transparent !important; border-color: transparent !important; box-shadow: none !important; }}
/* A caixa cresce com o texto; a rolagem só aparece depois do tamanho máximo */
.st-key-caixa [data-testid="stTextAreaRootElement"], .st-key-caixa [data-baseweb="textarea"] {{
    height: auto !important; min-height: 0 !important; }}
.st-key-caixa textarea {{
    resize: none; border: none !important; font-size: 1.15rem !important; font-weight: 600;
    color: {CORES["tinta"]} !important; padding-left: 0;
    field-sizing: content; height: auto !important; min-height: 3.4rem; max-height: 14rem; overflow-y: auto;
    scrollbar-width: thin;
}}
.st-key-caixa textarea::placeholder {{ color: rgba(23,38,31,.5); font-weight: 500; }}
.st-key-caixa [data-testid="InputInstructions"] {{ display: none; }}  /* "Press Ctrl+Enter to apply", em inglês */

</style>
"""


def aplicar_tema() -> None:
    """Injeta fontes e o CSS da marca. Chamar uma vez por execução do app."""
    st.markdown(_CSS, unsafe_allow_html=True)


def aplicar_tema_home() -> None:
    """Ajustes da página inicial (conteúdo centralizado, caixa da ideia). Chamar só na tela 1."""
    st.markdown(_CSS_HOME, unsafe_allow_html=True)


def aplicar_cabecalho() -> None:
    """Prende o container key="cabecalho" no topo, em vidro bege. Chamar nas telas 2 a 6."""
    st.markdown(_CSS_CABECALHO, unsafe_allow_html=True)


def logo_claro() -> None:
    """Logotipo em cores claras, para o fundo escuro (mesmo desenho do logo.svg)."""
    svg = (Path(__file__).parent / "logo.svg").read_text(encoding="utf-8")
    svg = svg.replace('stroke="#1F6F5C"', f'stroke="{CORES["menta"]}"').replace('fill="#17261F"', f'fill="{CORES["creme"]}"')
    st.markdown(f'<div class="geno-home-logo">{svg}</div>', unsafe_allow_html=True)


def logo(largura: int = 150) -> None:
    """Mostra o logotipo (arquivo logo.svg ao lado deste módulo)."""
    svg = (Path(__file__).parent / "logo.svg").read_text(encoding="utf-8")
    st.markdown(f'<div style="width:{largura}px;margin-bottom:.5rem">{svg}</div>', unsafe_allow_html=True)


def botao_principal(rotulo: str, chave: str, **kwargs) -> bool:
    """Botão das ações importantes (analisar, confirmar, tentar de novo): contorno menta, seta, coral no hover.

    Usa st.button por baixo (mesmo retorno e mesmos kwargs); `chave` vira a classe do container que o estilo pega.
    """
    with st.container(key=f"bp_{chave}"):
        return st.button(rotulo, width="stretch", **kwargs)


def divisor(titulo: str | None = None) -> None:
    """Linha fina entre seções; com `titulo`, abre a seção seguinte com um subtítulo."""
    st.markdown('<hr class="geno-divisor">' + (f'<div class="geno-secao">{titulo}</div>' if titulo else ""),
                unsafe_allow_html=True)


def caixa_confianca(nivel: str, texto: str) -> None:
    """Renderiza o indicador de confiança. nivel: 'alta' | 'media' | 'baixa'."""
    c = CONFIANCA[nivel]
    st.markdown(
        f'<div class="geno-confianca" style="background:{c["fundo"]};'
        f'border-color:{c["borda"]};color:{c["texto"]}">{texto}</div>',
        unsafe_allow_html=True,
    )


def card_lacuna(titulo: str, corpo: str) -> None:
    """Card de destaque da lacuna (herói da tela de resultado)."""
    st.markdown(
        f'<div class="geno-lacuna"><h3>{titulo}</h3><div>{corpo}</div></div>',
        unsafe_allow_html=True,
    )
