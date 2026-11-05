# Pedido do motor (Micael) para o enriquecimento (Roger), parte 2

> Cole este arquivo no Claude que você estiver usando, aberto na raiz do repositório `Micdali/Geno`, junto com o seu script de coleta e exportação (`exportar_textos.py`).

## Situação

O `textos_sites_rj.csv` de 03/11 funcionou: o formato está certo, e o motor leu e classificou tudo.

- 425 páginas, 245 CNPJs, 204 com texto útil.
- **Só 94 dos 204 são sites de escola.** Os outros 110 são de contabilidade, advocacia, provedores, lojas, consultorias sem cursos ou páginas "em construção".
- Sites de ensino por método: CNPJ no rodapé 16 de 19, nome × título 38 de 58, **e-mail 40 de 127**.
- 12 CNPJs vieram com vários sites, um deles com 11.

Para apontar lacunas, o motor precisa de **pelo menos 50 escolas do mesmo nicho** (regra do `dados/config.yaml`). Com 94 escolas de todos os tipos, nenhum nicho chega lá.

## O que mudar na busca

### 1. Descartar domínios de contador antes de coletar

O domínio do e-mail cadastrado na Receita muitas vezes é o do contador, e o `enriquecimento/README.md` já manda descartar esses domínios. Descarte o domínio quando:

- ele aparece no `dominio_email` de **3 ou mais CNPJs diferentes** do `candidatos.parquet` (escola costuma ter um CNPJ; contador atende dezenas); **ou**
- o nome do domínio contém `contab`, `contador`, `contabil`, `fiscal`, `assessoria`, `advoga` ou `adv.`.

Registre quantos domínios caíram em cada regra. Esse número vai para o `METRICAS.md`.

### 2. Um site por CNPJ na saída

Hoje o exportador escolhe o melhor CNPJ para cada site. Precisa escolher **também o melhor site para cada CNPJ**:

- prioridade: `manual` > `rodape_cnpj` > `nome_titulo` > `email`;
- no empate, fica o site com mais texto;
- os outros sites daquele CNPJ saem do CSV.

Se um nome fantasia casar com muitos domínios no nome × título, o nome provavelmente é genérico. Nesse caso, prefira não ligar nenhum.

### 3. Priorizar quem tem mais chance de ser escola

Ordem da fila de coleta:

1. `situacao = 02` (ativa) **e** `cnae_principal` entre os 5 do piloto: 8593700, 8599604, 8599699, 8599603, 8599605. Metade do recorte entrou só pelo CNAE secundário, e essas empresas raramente são escolas.
2. Depois, ativas que entraram só pelo CNAE secundário.
3. Baixadas por último. Quase nunca têm site no ar.

### 4. Volume

- **Primeiro marco: 500 sites de ensino**, o que deve dar umas 1.000 a 1.300 empresas buscadas.
- **Se der tempo: 1.000 sites de ensino.**

Existem 27.296 empresas ativas com domínio de e-mail próprio, então há espaço de sobra.

### 5. Entregar em lotes

Mesmo formato e mesmas colunas do CSV de 03/11, um arquivo por lote: `textos_sites_rj_2.csv`, `textos_sites_rj_3.csv`… Pode ser a cada 200 ou 300 empresas. Eu classifico cada lote assim que chega, sem esperar o fim.

Não repita CNPJs que já vieram em lotes anteriores, a não ser que o site tenha mudado.

## Conferência rápida antes de mandar cada lote

Peça ao seu Claude para medir, no lote:

- quantos CNPJs aparecem com mais de um site (deve ser **0**);
- a porcentagem de páginas `home` com status 200 que contêm pelo menos uma destas palavras: curso, aula, escola, treinamento, ensino, idiomas, capacitação. No CSV de 03/11 foi 67%. **Abaixo de 80%, ainda tem contador ou site errado passando.**

Mande os dois números junto com o arquivo.

## O que não muda

- `robots.txt`, no máximo 1 requisição por segundo por domínio, User-Agent = `GENO_USER_AGENT`.
- Bloqueios (Cloudflare etc.) são registrados com `bloqueado = true`, nunca contornados.
- Só texto público do site. Nada de sócios, telefones ou e-mails pessoais.
- CNPJ sempre vindo do `candidatos.parquet` (RJ). O CSV fica fora do Git.

## Prazo

Apresentação na **quinta, 05/11**. O ideal é que o primeiro lote chegue ainda em **04/11 de manhã**, e o resto ao longo do dia 04/11.

## Para o artigo (quando der)

Atualize a sua parte do `METRICAS.md`:
- cobertura e precisão por método, numa amostra conferida à mão;
- a porcentagem de sites bloqueados;
- quantos domínios de contador foram descartados.

O gabarito de 100 empresas continua valendo. Ele mede a precisão do LLM e não trava a demo.
