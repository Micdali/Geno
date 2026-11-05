-- =====================================================================
-- CONTRATO 1 — Schema do banco do GENO (DuckDB, arquivo único geno.duckdb)
-- Versão: v0.1 (03/11/2026: visões ampliadas pelo bloco de dados) — baseado na seção 8 do relatório técnico
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
--
-- v0.1 (03/11/2026): este bloco passa a ser a ESPECIFICAÇÃO das colunas das visões.
-- A implementação fica com o Lucas em dados/sql/02_views.sql e dados/sql/03_views_publicas.sql,
-- aplicados DEPOIS deste arquivo, porque dependem de tabelas de dados/sql/01_schema_extra.sql
-- (motivo_classe, simples, situacao_cadastral). Quem só lê as colunas da v0 não percebe a mudança:
-- as colunas da v0 continuam, com o mesmo nome e na mesma ordem; as novas vêm depois.
-- ---------------------------------------------------------------------

-- vw_eventos — um estabelecimento por linha, base das séries de saturação
--   cnpj            VARCHAR   (v0)
--   ano_abertura    INTEGER   (v0) ano de data_inicio
--   ano_baixa       INTEGER   (v0) ano de data_situacao quando situacao = '08'; senão NULL
--   situacao        VARCHAR   (v0) '01' nula, '02' ativa, '03' suspensa, '04' inapta, '08' baixada
--   motivo          VARCHAR   (v0) motivo_situacao
--   classe_baixa    VARCHAR   (v0.1) 'voluntaria' | 'oficio' | 'outra'; NULL se não está baixada
--                             (classe de cada motivo: dados/sql/seeds/motivo_classe.csv)
--   baixa_em_massa  BOOLEAN   (v0.1) true quando a baixa é de ofício (inclui as baixas em massa
--                             da Receita); false nos demais casos. Séries de mortalidade excluem.

-- vw_eventos_longo — um EVENTO por linha (abertura ou baixa), sem filtro de período   (v0.1)
--   cnpj, tipo_evento ('abertura' | 'baixa'), data_evento, ano, motivo,
--   cnae_fiscal_principal, municipio (código da Receita), identificador_matriz_filial,
--   opcao_mei, natureza_juridica, baixa_em_massa (só nas baixas; NULL nas aberturas)

-- vw_publico — dados exibíveis. ÚNICA fonte que o app pode usar para mostrar empresas (LGPD).
--   cnpj               VARCHAR  (v0)
--   nome_exibicao      VARCHAR  (v0) nome fantasia; senão razão social; em MEI e empresário
--                               individual nunca o nome do titular ('Empresa individual (nome oculto)')
--   situacao           VARCHAR  (v0)
--   data_inicio        DATE     (v0)
--   data_situacao      DATE     (v0)
--   bairro             VARCHAR  (v0)
--   municipio          VARCHAR  (v0) nome do município
--   uf                 VARCHAR  (v0)
--   nome_fantasia      VARCHAR  (v0.1) NULL quando contém '@' ou, em MEI/EI, repete o nome do titular
--   razao_social       VARCHAR  (v0.1) NULL em MEI e natureza 2135 (empresário individual)
--   cnae_principal     VARCHAR  (v0.1)
--   cnae_descricao     VARCHAR  (v0.1)
--   situacao_descricao VARCHAR  (v0.1)
--   porte              VARCHAR  (v0.1)
--   opcao_simples      VARCHAR  (v0.1) 'S' | 'N' | NULL
--   opcao_mei          VARCHAR  (v0.1) 'S' | 'N' | NULL
--
-- Regras de LGPD da vw_publico (testadas em tests/test_lgpd.py):
--   * nunca expõe e-mail, domínio de e-mail, telefone, logradouro, número, complemento, CEP nem sócios;
--   * limite aceito pelo grupo: nome fantasia de MEI/EI com só parte do nome do titular
--     (ex.: o primeiro nome) continua visível, para não esconder nomes comerciais legítimos.
