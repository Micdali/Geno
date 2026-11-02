-- =====================================================================
-- GENO — Camada 2 (enriquecimento / Roger) — subset do contrato 1
-- (contratos/01_schema.sql do repo). Idempotente: seguro rodar no banco
-- compartilhado geno.duckdb. NÃO redefinir tabelas de outras camadas aqui.
-- =====================================================================

-- Cada hipótese de site para um CNPJ, com a evidência que a sustenta
CREATE TABLE IF NOT EXISTS candidato_dominio (
    cnpj          VARCHAR,            -- -> estabelecimento.cnpj
    dominio       VARCHAR,
    metodo        VARCHAR,            -- 'email' | 'rodape_cnpj' | 'nome_titulo' | 'overture' | 'wayback' | 'manual'
    confianca     DOUBLE,             -- 0 a 1
    validado      BOOLEAN,            -- conferido à mão?
    verificado_em TIMESTAMP,
    PRIMARY KEY (cnpj, dominio, metodo)
);

-- Cache das páginas coletadas, inclusive tentativas bloqueadas
CREATE TABLE IF NOT EXISTS pagina (
    url         VARCHAR PRIMARY KEY,
    dominio     VARCHAR,
    tipo        VARCHAR,              -- 'home' | 'sobre' | 'precos' | 'arquivada'
    status_http INTEGER,
    bloqueado   BOOLEAN,              -- ex.: Cloudflare. Registrado, nunca contornado.
    texto       VARCHAR,              -- texto limpo, truncado
    hash_texto  VARCHAR,              -- evita reprocessar o mesmo texto
    coletado_em TIMESTAMP
);

-- 100 empresas anotadas à mão (Roger) para medir a precisão da classificação.
-- Mesmos campos da tabela classificacao (camada 3 / Micael).
CREATE TABLE IF NOT EXISTS gabarito (
    cnpj              VARCHAR PRIMARY KEY,
    publico_atendido  VARCHAR,
    produto_servico   VARCHAR,
    canal_atendimento VARCHAR,
    problema_resolvido VARCHAR,
    modelo_receita    VARCHAR,        -- lista fechada (ver contratos/03_classificacao.schema.json)
    anotador          VARCHAR,
    anotado_em        TIMESTAMP
);
