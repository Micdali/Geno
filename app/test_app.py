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


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setitem(sys.modules, "motor.nicho", None)  # força o recorte de exemplo, sem LLM
    monkeypatch.setattr(motor.analisar, "analisar",
                        lambda ideia, recorte=None: json.loads(EXEMPLO.read_text(encoding="utf-8")) | {"ideia": ideia})
    return AppTest.from_file(APP, default_timeout=30).run()


def clicar(at, rotulo):
    next(b for b in at.button if b.label.startswith(rotulo)).click().run()
    for _ in range(50):  # o AppTest não roda o fragment da tela 3 sozinho: simula os ciclos
        if at.session_state.tela != 3 or at.session_state.erro:
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
    clicar(app, T.BOTAO_ANALISAR_ASSIM_MESMO)
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


def test_saturacao_fala_do_setor(app):
    app.text_area[0].input("Escola de inglês online para adultos 40+").run()
    clicar(app, T.BOTAO_ANALISAR)
    clicar(app, T.BOTAO_ANALISAR_ASSIM_MESMO)  # com pergunta, o botão de pular aparece
    clicar(app, "Saturação")
    frases = [m.value for m in app.markdown]
    assert any("neste setor" in f for f in frases) and not any("neste recorte" in f for f in frases)


def test_app_pede_para_aquecer_o_modelo_ao_abrir(monkeypatch):
    st.cache_resource.clear()  # o aquecimento roda uma vez por processo; outros testes já rodaram
    chamadas = []
    monkeypatch.setattr(motor.embeddings, "aquecer", lambda: chamadas.append(1), raising=False)
    monkeypatch.setitem(sys.modules, "motor.nicho", None)
    AppTest.from_file(APP, default_timeout=30).run()
    assert chamadas == [1]
