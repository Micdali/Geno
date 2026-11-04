"""Identidade visual do Geno para Streamlit.

Uso, logo no começo do app (depois de st.set_page_config):

    from geno.tema import aplicar_tema, logo
    st.set_page_config(page_title="Geno", page_icon="🌱", layout="centered")
    aplicar_tema()
    logo()
"""
from pathlib import Path

import streamlit as st

# Paleta (mesma do config.toml e da apresentação do pitch)
CORES = {
    "floresta": "#1F6F5C",
    "floresta_escura": "#134A3D",
    "coral": "#E8613C",   # destaque: a lacuna, o que ninguém atende
    "creme": "#FAF3E7",
    "areia": "#F0E3C8",
    "tinta": "#17261F",
}

# Cores dos 3 níveis do indicador de confiança (texto escuro sobre fundo claro)
CONFIANCA = {
    "alta": {"fundo": "#DCEFE7", "borda": "#1F6F5C", "texto": "#134A3D"},
    "media": {"fundo": "#FBEBC8", "borda": "#C98A12", "texto": "#6B4A06"},
    "baixa": {"fundo": "#FBDDD2", "borda": "#E8613C", "texto": "#7A2A12"},
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextInput, .stTextArea, .stButton {{
    font-family: 'Manrope', sans-serif;
}}
h1, h2, h3 {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    color: {CORES["tinta"]};
}}
h1 {{ font-size: 2.6rem !important; }}

/* Esconde o chrome padrão do Streamlit */
#MainMenu, footer {{ visibility: hidden; }}

/* Botão principal */
.stButton button[kind="primary"] {{
    background: {CORES["floresta"]};
    border: none;
    border-radius: 999px;
    padding: 0.6rem 1.6rem;
    font-weight: 700;
}}
.stButton button[kind="primary"]:hover {{ background: {CORES["floresta_escura"]}; }}

/* Botão secundário (ex.: "ajustar minha ideia", "analisar assim mesmo") */
.stButton button[kind="secondary"] {{
    border-radius: 999px;
    border: 1.5px solid {CORES["floresta"]};
    color: {CORES["floresta"]};
    background: transparent;
    font-weight: 600;
}}

/* Botão desabilitado (ex.: etapas ainda não liberadas na barra lateral) */
.stButton button:disabled {{
    border-style: dashed;
    opacity: .45;
    cursor: not-allowed;
}}

/* Campo da ideia */
.stTextArea textarea {{
    border-radius: 16px;
    border: 1.5px solid rgba(23,38,31,0.18);
    background: #FFFFFF;
    font-size: 1.05rem;
}}

/* Barra de progresso na cor da marca */
.stProgress > div > div > div > div {{ background-color: {CORES["floresta"]}; }}

/* Card da lacuna: o herói da tela de resultado */
.geno-lacuna {{
    background: #FFFFFF;
    border-left: 6px solid {CORES["coral"]};
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 10px 28px rgba(23,38,31,0.10);
    margin: 1rem 0;
}}
.geno-lacuna h3 {{ margin: 0 0 .4rem 0; color: {CORES["coral"]}; }}

/* Indicador de confiança */
.geno-confianca {{
    border-radius: 14px;
    padding: .8rem 1.1rem;
    border-left: 5px solid;
    margin: .8rem 0;
    font-size: .98rem;
    line-height: 1.45;
}}

/* Linha fixa de limite (oferta, não demanda) */
.geno-limite {{
    font-size: .88rem;
    opacity: .72;
    margin-top: 2rem;
    text-align: center;
}}
</style>
"""


def aplicar_tema() -> None:
    """Injeta fontes e CSS da marca. Chamar uma vez por execução do app."""
    st.markdown(_CSS, unsafe_allow_html=True)


def logo(largura: int = 150) -> None:
    """Mostra o logotipo (arquivo logo.svg ao lado deste módulo)."""
    svg = (Path(__file__).parent / "logo.svg").read_text(encoding="utf-8")
    st.markdown(
        f'<div style="width:{largura}px;margin-bottom:.5rem">{svg}</div>',
        unsafe_allow_html=True,
    )


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
