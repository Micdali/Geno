# app/ — As 6 telas (dono: Christian)

**Objetivo até 05/11:** app rodando local com as 6 telas do storyboard e o laço "ajustar minha ideia", ligado ao motor real; e o vídeo tutorial gravado.

## Como trabalhar sem depender de ninguém

Chame `motor.analisar(ideia)`. Hoje ela devolve o [arquivo de exemplo](../contratos/exemplos/resultado_analise.exemplo.json), e as telas podem ser construídas inteiras em cima dele. Quando o motor real ficar pronto, nada muda do lado do app.

## As telas

1. Descrever a ideia (texto livre, sem login)
2. Confirmar nicho (escolher OU digitar; perguntas de afunilamento; "analisar assim mesmo")
3. Processamento, com barra de progresso
4. Concorrentes
5. Saturação: aberturas × baixas por ano
6. Lacunas, mostrando as empresas que embasam cada conclusão

O indicador de confiança aparece no cabeçalho das telas 4, 5 e 6. O botão "ajustar minha ideia" volta à tela 2 com o recorte carregado.

## Como rodar

```bash
streamlit run app/app.py
python -m pytest app -v      # percorre as 6 telas com o arquivo de exemplo (sem banco, sem LLM)
```

Stack: **Streamlit** (testado na 1.66; `pip install -r requirements.txt` instala a mais recente).

- **Tela 2** usa `motor.nicho.propor_recorte` quando ele existe (branch `micael/motor-llm`). Sem ele, usa o recorte do arquivo de exemplo. Se o LLM falhar, a pessoa preenche o recorte à mão.
- **Tela 3** chama `motor.analisar(ideia, recorte)`. A barra de progresso é estimada pelo tempo, porque o motor não informa as etapas. Se der erro, a tela oferece tentar de novo, voltar ou ver os dados de exemplo.
- Quando o resultado é o arquivo de exemplo (`_aviso` no JSON), o cabeçalho mostra uma faixa vermelha avisando que os dados são fictícios.
- **Tela 6** mostra a tabela ✅/❌ quando a lacuna traz `atendimento` (extra do motor real).
- **Tema e textos da Mariana** ficam em `app/geno/`: `tema.py` (CSS, caixa de confiança, card da lacuna), `textos.py` (todas as frases) e `logo.svg`. Cores e fontes (Manrope e Fraunces, do Google Fonts) estão em `.streamlit/config.toml`; mudar o `config.toml` exige reiniciar o app.
- O texto da confiança vem pronto do motor (`confianca.texto`, contrato 4), não dos modelos do `textos.py`.

## `prototipo/`

Rascunho visual em Streamlit, feito só para o grupo ver a cara da ferramenta antes de decidir a stack. Usa dados fictícios embutidos e **não** segue o contrato 4. Serve de referência, não de base de código.

```bash
streamlit run app/prototipo/app.py
# outras telas: http://localhost:8501/?tela=2  (1 a 6)
```

A stack final (Streamlit ou FastAPI + React) ainda está em decisão no grupo.
