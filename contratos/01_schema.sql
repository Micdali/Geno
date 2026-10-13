-- =====================================================================
-- CONTRATO 1 — Schema do banco do GENO (DuckDB, arquivo único geno.duckdb)
-- Versão: v0 (rascunho) — baseado na seção 8 do relatório técnico
-- Status: AGUARDANDO APROVAÇÃO DO GRUPO
--
-- Quem escreve em cada tabela:
--   Camada 1 (identidade)      -> Lucas      (dados/)
--   Camada 2 (enriquecimento)  -> Roger      (enriquecimento/)
--   Camada 3/4 (estrutura/busca)-> Micael    (motor/)
-- O app (Christian) só LÊ — e só pelas visões vw_*.
-- Mudou algo aqui? Ver CONTRIBUTING.md antes do merge.
-- =====================================================================


-- ---------------------------------------------------------------------
-- CAMADA 1 — IDENTIDADE (base CNPJ da Receita)
-- ---------------------------------------------------------------------

-- Tabelas de domínio (carga integral dos arquivos pequenos da Receita)
CREATE TABLE IF NOT EXISTS cnae (
    codigo      VARCHAR PRIMARY KEY,   -- 7 dígitos, como texto
    descricao   VARCHAR
);

CREATE TABLE IF NOT EXISTS municipio (
    codigo      VARCHAR PRIMARY KEY,   -- código da RECEITA (≠ código IBGE)
    descricao   VARCHAR
);

CREATE TABLE IF NOT EXISTS motivo (
    codigo      VARCHAR PRIMARY KEY,   -- motivo da situação cadastral
    descricao   VARCHAR
);

CREATE TABLE IF NOT EXISTS natureza (
    codigo      VARCHAR PRIMARY KEY,   -- natureza jurídica
    descricao   VARCHAR
);

-- Uma linha por raiz de CNPJ (pessoa jurídica)
CREATE TABLE IF NOT EXISTS empresa (
    cnpj_basico        VARCHAR PRIMARY KEY,  -- 8 posições, TEXTO (CNPJ alfanumérico)
    razao_social       VARCHAR,              -- NUNCA exibida para MEI/empresário individual
    natureza_juridica  VARCHAR,              -- -> natureza.codigo
    porte              VARCHAR,
    capital_social     DECIMAL(18,2),        -- convertido de vírgula para ponto
    opcao_mei          BOOLEAN               -- vindo do arquivo Simples
);

-- Uma linha por estabelecimento (matriz ou filial). Núcleo do sistema.
CREATE TABLE IF NOT EXISTS estabelecimento (
    cnpj                 VARCHAR PRIMARY KEY, -- 14 posições, TEXTO
    cnpj_basico          VARCHAR,             -- -> empresa.cnpj_basico
    matriz               BOOLEAN,
    nome_fantasia        VARCHAR,             -- NULL quando vazio
    situacao             VARCHAR,             -- 01 nula, 02 ativa, 03 suspensa, 04 inapta, 08 baixada
    data_situacao        DATE,
    motivo_situacao      VARCHAR,             -- -> motivo.codigo (separa baixa voluntária de baixa de ofício/em massa)
    data_inicio          DATE,
    cnae_principal       VARCHAR,             -- -> cnae.codigo
    cnaes_secundarios    VARCHAR[],           -- lista nativa
    via_cnae_secundario  BOOLEAN,             -- entrou no recorte só pela atividade secundária
    uf                   VARCHAR,
    municipio_cod        VARCHAR,             -- -> municipio.codigo
    bairro               VARCHAR,
    cep                  VARCHAR,
    dominio_email        VARCHAR              -- SÓ o domínio; o e-mail não é guardado
);


-- ---------------------------------------------------------------------
-- CAMADA 2 — ENRIQUECIMENTO (sites)
-- ---------------------------------------------------------------------

-- Cada hipótese de site para um CNPJ, com a evidência que a sustenta
CREATE TABLE IF NOT EXISTS candidato_dominio (
    cnpj           VARCHAR,           -- -> estabelecimento.cnpj
    dominio        VARCHAR,
    metodo         VARCHAR,           -- 'email' | 'rodape_cnpj' | 'nome_titulo' | 'overture' | 'wayback' | 'manual'
    confianca      DOUBLE,            -- 0 a 1
    validado       BOOLEAN,           -- conferido à mão?
    verificado_em  TIMESTAMP,
    PRIMARY KEY (cnpj, dominio, metodo)
);

-- Cache das páginas coletadas, inclusive tentativas bloqueadas
CREATE TABLE IF NOT EXISTS pagina (
    url          VARCHAR PRIMARY KEY,
    dominio      VARCHAR,
    tipo         VARCHAR,             -- 'home' | 'sobre' | 'precos' | 'arquivada'
    status_http  INTEGER,
    bloqueado    BOOLEAN,             -- ex.: Cloudflare. Registrado, nunca contornado.
    texto        VARCHAR,             -- texto limpo, truncado
    hash_texto   VARCHAR,             -- evita reprocessar o mesmo texto
    coletado_em  TIMESTAMP
);


-- ---------------------------------------------------------------------
-- CAMADA 3 — ESTRUTURAÇÃO (LLM)
-- PENDENTE: o grupo decide o conjunto final de atributos (card "Decisões").
-- Hoje estão aqui os campos das duas propostas (definição de produto + relatório).
-- Ver contratos/03_classificacao.schema.json
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS classificacao (
    cnpj                VARCHAR,
    prompt_versao       VARCHAR,
    fonte               VARCHAR,      -- 'site' | 'site_arquivado' | 'so_nome'
    publico_atendido    VARCHAR,      -- para quem vende
    produto_servico     VARCHAR,      -- o que entrega, abaixo do CNAE
    canal_atendimento   VARCHAR,      -- 'presencial' | 'online' | 'delivery' | 'hibrido' | 'indeterminado'
    problema_resolvido  VARCHAR,
    modelo_receita      VARCHAR,      -- lista fechada (ver 03_classificacao.schema.json)
    posicionamento      VARCHAR,
    descricao_nicho     VARCHAR,
    confianca           VARCHAR,      -- 'alta' | 'media' | 'baixa'
    modelo_llm          VARCHAR,
    gerado_em           TIMESTAMP,
    PRIMARY KEY (cnpj, prompt_versao)
);

-- 100 empresas anotadas à mão (Roger) para medir a precisão da classificação
CREATE TABLE IF NOT EXISTS gabarito (
    cnpj                VARCHAR PRIMARY KEY,
    publico_atendido    VARCHAR,
    produto_servico     VARCHAR,
    canal_atendimento   VARCHAR,
    problema_resolvido  VARCHAR,
    modelo_receita      VARCHAR,
    anotador            VARCHAR,
    anotado_em          TIMESTAMP
);


-- ---------------------------------------------------------------------
-- CAMADA 4 — RECUPERAÇÃO
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS embedding (
    cnpj          VARCHAR PRIMARY KEY,
    modelo        VARCHAR,            -- ex.: modelo do sentence-transformers usado
    texto_origem  VARCHAR,            -- o texto que gerou o vetor
    vetor         FLOAT[384]
);


-- ---------------------------------------------------------------------
-- VISÕES — a única coisa que o app lê
-- ---------------------------------------------------------------------

-- Eventos de abertura e baixa, base das séries de saturação
CREATE OR REPLACE VIEW vw_eventos AS
SELECT
    cnpj,
    year(data_inicio)                                            AS ano_abertura,
    CASE WHEN situacao = '08' THEN year(data_situacao) END       AS ano_baixa,
    situacao,
    motivo_situacao                                              AS motivo
FROM estabelecimento;
-- TODO (Lucas): excluir/sinalizar baixas em massa pelo motivo_situacao.

-- Dados exibíveis. Esconde o nome do titular de MEI / empresário individual (LGPD).
CREATE OR REPLACE VIEW vw_publico AS
SELECT
    e.cnpj,
    COALESCE(
        e.nome_fantasia,
        CASE WHEN emp.opcao_mei OR emp.natureza_juridica = '2135'   -- conferir código de empresário individual
             THEN 'Empresa individual (nome oculto)'
             ELSE emp.razao_social END
    )                       AS nome_exibicao,
    e.situacao,
    e.data_inicio,
    e.data_situacao,
    e.bairro,
    m.descricao             AS municipio,
    e.uf
FROM estabelecimento e
LEFT JOIN empresa   emp ON emp.cnpj_basico = e.cnpj_basico
LEFT JOIN municipio m   ON m.codigo        = e.municipio_cod;
