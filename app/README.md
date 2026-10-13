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

## `prototipo/`

Rascunho visual em Streamlit, feito só para o grupo ver a cara da ferramenta antes de decidir a stack. Usa dados fictícios embutidos e **não** segue o contrato 4. Serve de referência, não de base de código.

```bash
streamlit run app/prototipo/app.py
# outras telas: http://localhost:8501/?tela=2  (1 a 6)
```

A stack final (Streamlit ou FastAPI + React) ainda está em decisão no grupo.
