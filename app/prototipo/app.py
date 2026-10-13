import streamlit as st, pandas as pd, plotly.graph_objects as go

st.set_page_config(page_title="GENO", page_icon="🌱", layout="wide")
tela = st.query_params.get("tela", "1")
IDEIA = "Quero abrir uma escola de inglês online para adultos acima de 40 anos que nunca estudaram o idioma, com aulas em grupo à noite."

with st.sidebar:
    st.markdown("## 🌱 GENO")
    st.caption("O mercado da sua ideia")
    st.radio("Etapas", ["1 · Descrever ideia", "2 · Confirmar nicho", "3 · Processamento",
                        "4 · Concorrentes", "5 · Saturação", "6 · Lacunas"], index=int(tela)-1)
    st.divider()
    st.caption("Mostramos o que já existe, não quanta gente compraria.")

def cabecalho():
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"**Sua ideia:** _{IDEIA}_")
    with c2:
        st.button("✏️ Ajustar minha ideia", use_container_width=True)
    st.warning("**Confiança média** — encontramos 47 empresas no recorte, 31 com site analisado. "
               "Empresas sem site podem oferecer algo parecido.", icon="⚠️")

if tela == "1":
    st.title("Qual é a sua ideia de negócio?")
    st.write("Descreva com suas palavras. Não precisa saber o nome do nicho — a gente ajuda a chegar lá.")
    st.text_area("Sua ideia", IDEIA, height=140)
    st.button("Analisar o mercado da minha ideia →", type="primary")
    st.caption("Sem cadastro. A primeira análise é gratuita.")

elif tela == "2":
    st.title("Entendemos assim. Está certo?")
    st.info("Escola de idiomas · **Inglês** · para **adultos 40+ iniciantes** · **online, ao vivo, em grupo**")
    st.subheader("Só mais uma pergunta para afinar o recorte")
    st.radio("As aulas seriam principalmente:", ["Conversação para o dia a dia", "Inglês para viagem",
             "Inglês para o trabalho", "Não sei ainda"], index=0)
    st.text_input("Quer corrigir algo? Escreva aqui", placeholder="ex.: na verdade é só para aposentados")
    c1, c2 = st.columns(2)
    c1.button("Confirmar e analisar →", type="primary", use_container_width=True)
    c2.button("Analisar assim mesmo", use_container_width=True)

elif tela == "3":
    st.title("Analisando o mercado da sua ideia…")
    st.progress(0.65, text="Comparando sua ideia com 1.284 escolas de idiomas na base da Receita Federal")
    st.status("Etapas", state="running", expanded=True).write(
        "✅ Recorte montado (1.284 empresas)\n\n✅ 47 parecidas com a sua ideia\n\n⏳ Lendo o que cada uma oferece…")

elif tela == "4":
    cabecalho()
    st.title("Quem já faz algo parecido")
    m1, m2, m3 = st.columns(3)
    m1.metric("Empresas parecidas", "47"); m2.metric("Ativas", "29"); m3.metric("Fecharam", "18", delta="38%", delta_color="inverse")
    df = pd.DataFrame({
        "Empresa (fictícia)": ["Fluency Club", "Inglês Sem Pressa", "Talk40 Idiomas", "English Corner Online", "Prime Speak"],
        "O que oferece": ["Aulas individuais online", "Curso gravado para iniciantes", "Grupos presenciais 40+",
                          "Conversação online em grupo", "Inglês corporativo"],
        "Público": ["Adultos em geral", "Adultos iniciantes", "Adultos 40+", "Jovens adultos", "Profissionais"],
        "Canal": ["Online", "Online (gravado)", "Presencial", "Online ao vivo", "Híbrido"],
        "Situação": ["Ativa", "Ativa", "Fechou em 2024", "Ativa", "Ativa"],
        "Semelhança": [0.82, 0.79, 0.77, 0.74, 0.61]})
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"Semelhança": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    with st.expander("Em comum com eles / possíveis diferenciais"):
        st.write("**Em comum:** aulas online para adultos iniciantes.\n\n**Possível diferencial:** ninguém combina *ao vivo + em grupo + 40+*.\n\n**Não verificado:** preços (poucos sites publicam).")

elif tela == "5":
    cabecalho()
    st.title("Quantos abriram e quantos fecharam")
    anos = list(range(2021, 2026))
    ab = [210, 265, 240, 198, 186]; bx = [95, 120, 168, 181, 175]
    fig = go.Figure([go.Bar(name="Abriram", x=anos, y=ab, marker_color="#0F766E"),
                     go.Bar(name="Fecharam", x=anos, y=bx, marker_color="#D97706")])
    fig.update_layout(barmode="group", height=380, margin=dict(t=20, b=20), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Abriram em 5 anos", "1.099"); c2.metric("Fecharam em 5 anos", "739"); c3.metric("Saldo 2025", "+11", delta="-90% vs 2021")
    st.caption("Baixa de CNPJ nem sempre significa que a empresa fechou de fato. Fonte: Receita Federal, competência 10/2026.")

elif tela == "6":
    cabecalho()
    st.title("O que ninguém está atendendo")
    st.success("### Inglês **ao vivo, em grupo**, para **40+ iniciantes**\nDas 47 empresas analisadas, **nenhuma** combina os três.", icon="💡")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Outras combinações pouco atendidas**")
        st.dataframe(pd.DataFrame({"Combinação": ["Presencial + aposentados", "Online + inglês para viagem 50+", "Híbrido + turmas de bairro"],
                                   "Empresas que oferecem": [1, 2, 0]}), hide_index=True, use_container_width=True)
    with c2:
        st.markdown("**Por que dizemos isso** — as empresas que embasam a conclusão")
        st.dataframe(pd.DataFrame({"Empresa (fictícia)": ["Fluency Club", "Inglês Sem Pressa", "Talk40 Idiomas", "English Corner Online"],
                                   "Online ao vivo": ["✅", "❌", "❌", "✅"], "Em grupo": ["❌", "❌", "✅", "✅"], "40+": ["❌", "✅", "✅", "❌"]}),
                     hide_index=True, use_container_width=True)
    st.button("👎 Alguma empresa não pertence a este recorte?")
