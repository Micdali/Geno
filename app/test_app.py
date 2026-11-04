"""Percorre as 6 telas com o arquivo de exemplo do contrato 4 (sem banco, sem LLM).

    python -m pytest app -v
"""
import json
import sys
import time
import types
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import motor.analisar
import motor.embeddings

sys.path.insert(0, str(Path(__file__).parent))
from geno.textos import T  # noqa: E402

APP = str(Path(__file__).with_name("app.py"))
EXEMPLO = Path(__file__).resolve().parent.parent / "contratos" / "exemplos" / "resultado_analise.exemplo.json"


@pytest.fixture(autouse=True)
def sem_modelo(monkeypatch):
    monkeypatch.setattr(motor.embeddings, "aquecer", lambda: None, raising=False)  # nos testes, não carrega o modelo
    monkeypatch.setattr(motor.embeddings, "preparar", lambda: None, raising=False)
    monkeypatch.setattr(motor.embeddings, "pronto", lambda: True, raising=False)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setitem(sys.modules, "motor.nicho", None)  # força o recorte de exemplo, sem LLM
    monkeypatch.setattr(motor.analisar, "analisar",
                        lambda ideia, recorte=None: json.loads(EXEMPLO.read_text(encoding="utf-8")) | {"ideia": ideia})
    return AppTest.from_file(APP, default_timeout=30).run()


def clicar(at, rotulo):
    next(b for b in at.button if b.label.startswith(rotulo)).click().run()
    for _ in range(50):  # o AppTest não roda o fragment da tela 3 sozinho: simula os ciclos
        carregando = at.session_state.tela == 3 or "carga" in at.session_state  # a carga roda numa thread
        if not carregando or at.session_state.erro:
            break
        time.sleep(0.1)
        at.run()
    assert not at.exception, at.exception


def test_fluxo_completo(app):
    at = app
    at.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(at, T.BOTAO_ANALISAR)
    assert at.session_state.tela == 2
    at.radio[0].set_value("Inglês para viagem").run()
    clicar(at, T.BOTAO_CONFIRMAR_RECORTE)
    assert at.session_state.tela == 4
    assert at.session_state.respostas == {"As aulas seriam principalmente:": "Inglês para viagem"}
    for tela, etapa in ((5, "Saturação"), (6, "Lacunas")):
        clicar(at, etapa)
        assert at.session_state.tela == tela and at.session_state.tela_anterior == tela - 1
    assert any("nenhuma oferece" in m.value for m in at.markdown)
    clicar(at, f"✏️ {T.BOTAO_AJUSTAR_IDEIA}")
    assert at.session_state.tela == 2
    assert at.text_input[1].value == "adultos 40+ iniciantes"  # volta com o recorte carregado


def test_ideia_curta_nao_avanca(app):
    app.text_area[0].input("curso").run()
    clicar(app, T.BOTAO_ANALISAR)
    assert app.session_state.tela == 1
    assert app.error


def test_erro_do_motor_mostra_saida(app, monkeypatch):
    def quebra(ideia, recorte=None):
        raise RuntimeError("banco não encontrado")
    monkeypatch.setattr(motor.analisar, "analisar", quebra)
    app.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(app, T.BOTAO_ANALISAR)
    clicar(app, T.BOTAO_CONFIRMAR_RECORTE)
    assert app.session_state.tela == 3 and "banco não encontrado" in app.session_state.erro
    clicar(app, "Ver com dados de exemplo")
    assert app.session_state.tela == 4


def test_sem_perguntas_fica_so_o_botao_principal(monkeypatch):
    nicho = types.ModuleType("motor.nicho")
    nicho.propor_recorte = lambda ideia, respostas=None: json.loads(EXEMPLO.read_text(encoding="utf-8"))["recorte"] | {
        "perguntas": []}
    monkeypatch.setitem(sys.modules, "motor.nicho", nicho)
    monkeypatch.setattr(motor.analisar, "analisar",
                        lambda ideia, recorte=None: json.loads(EXEMPLO.read_text(encoding="utf-8")) | {"ideia": ideia})
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(at, T.BOTAO_ANALISAR)
    rotulos = [b.label for b in at.button]
    assert T.BOTAO_CONFIRMAR_RECORTE in rotulos and T.BOTAO_ANALISAR_ASSIM_MESMO not in rotulos


def test_saturacao_explica_o_que_os_numeros_querem_dizer(app):
    app.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(app, T.BOTAO_ANALISAR)
    clicar(app, T.BOTAO_CONFIRMAR_RECORTE)
    clicar(app, "Saturação")
    frases = " ".join(m.value for m in app.markdown)
    assert T.SATURACAO_LEITURA in frases and "Setor" in frases and "para cada 10 que abriram" in frases


def test_primeira_abertura_mostra_a_animacao_e_prepara_o_modelo(monkeypatch):
    st.cache_resource.clear()  # o preparo roda uma vez por processo; outros testes já rodaram
    estado = {"pronto": False, "chamadas": 0}

    def preparar():
        estado["chamadas"] += 1
        estado["pronto"] = True

    monkeypatch.setattr(motor.embeddings, "preparar", preparar, raising=False)
    monkeypatch.setattr(motor.embeddings, "pronto", lambda: estado["pronto"], raising=False)
    monkeypatch.setitem(sys.modules, "motor.nicho", None)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert estado["chamadas"] == 1 and not at.exception
    assert at.title[0].value == T.TITULO  # depois de preparar, a home aparece

def test_pagina_inicial_so_tem_logo_slogan_e_caixa(app):
    assert [b.label for b in app.button] == [T.BOTAO_ANALISAR]  # sem a linha do tempo
    assert app.title[0].value == T.TITULO and len(app.text_area) == 1
    assert not any(T.RODAPE in m.value for m in app.markdown)
    app.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(app, T.BOTAO_ANALISAR)
    assert app.session_state.tela == 2 and any(b.label == "Nicho" for b in app.button)  # a linha volta na tela 2


def _app_com_perguntas(monkeypatch, perguntas):
    recebidas = []

    def propor(ideia, respostas=None):
        recebidas.append(respostas)
        return json.loads(EXEMPLO.read_text(encoding="utf-8"))["recorte"] | {"perguntas": [] if respostas else perguntas}

    nicho = types.ModuleType("motor.nicho")
    nicho.propor_recorte = propor
    monkeypatch.setitem(sys.modules, "motor.nicho", nicho)
    monkeypatch.setattr(motor.analisar, "analisar",
                        lambda ideia, recorte=None: json.loads(EXEMPLO.read_text(encoding="utf-8")) | {"ideia": ideia})
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(at, T.BOTAO_ANALISAR)
    return at, recebidas


def test_pergunta_de_varias_opcoes_com_outro(monkeypatch):
    at, recebidas = _app_com_perguntas(monkeypatch, [
        {"pergunta": "Quais formatos?", "opcoes": ["Aulas em grupo", "Aulas individuais", "Não sei ainda"], "multipla": True}])
    assert [c.label for c in at.checkbox] == ["Aulas em grupo", "Aulas individuais", "Outro", "Não sei ainda"]
    at.checkbox[0].check().run()
    at.checkbox[2].check().run()
    at.text_input(key=next(k for k in at.session_state if str(k).endswith("_outro"))).input("Imersão de fim de semana").run()
    clicar(at, T.BOTAO_CONFIRMAR_RECORTE)
    assert recebidas[-1] == {"Quais formatos?": "Aulas em grupo; Imersão de fim de semana"}


def test_pergunta_de_uma_opcao_com_outro_e_botao_unico(monkeypatch):
    at, recebidas = _app_com_perguntas(monkeypatch, [
        {"pergunta": "Onde?", "opcoes": ["Zona Sul", "Centro", "Não sei ainda"], "multipla": False}])
    assert T.BOTAO_ANALISAR_ASSIM_MESMO not in [b.label for b in at.button]
    assert at.radio[0].options == ["Zona Sul", "Centro", "Outro", "Não sei ainda"]
    at.radio[0].set_value("Outro").run()
    at.text_input(key=next(k for k in at.session_state if str(k).endswith("_outro"))).input("Niterói").run()
    clicar(at, T.BOTAO_CONFIRMAR_RECORTE)
    assert recebidas[-1] == {"Onde?": "Niterói"} and at.session_state.tela == 4
