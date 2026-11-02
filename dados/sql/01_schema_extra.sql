-- =====================================================================
-- Tabelas que a Camada 1 do relatório técnico (seção 3.2) prevê e o contrato 1 não traz.
-- Só acrescenta; não altera nenhuma tabela de contratos/01_schema.sql. Aplicada logo depois dele.
-- =====================================================================

-- Tabelas de domínio da Receita que faltavam (carga integral).
CREATE TABLE IF NOT EXISTS pais (
    codigo     VARCHAR PRIMARY KEY,
    descricao  VARCHAR
);

CREATE TABLE IF NOT EXISTS qualificacao (
    codigo     VARCHAR PRIMARY KEY,   -- qualificação de sócio/responsável (tabela da Receita)
    descricao  VARCHAR
);

-- Situação cadastral não tem arquivo de domínio na Receita: os códigos vêm do layout oficial
-- (cnpj-metadados.pdf) e ficam em dados/config.yaml.
CREATE TABLE IF NOT EXISTS situacao_cadastral (
    codigo     VARCHAR PRIMARY KEY,   -- 2 dígitos: 01, 02, 03, 04, 08
    descricao  VARCHAR
);

-- Dados do Simples/MEI como vêm da Receita (S, N ou NULL quando em branco).
-- Uma linha por raiz de CNPJ; nem toda empresa tem registro.
CREATE TABLE IF NOT EXISTS simples (
    cnpj_basico            VARCHAR PRIMARY KEY,   -- -> empresa.cnpj_basico
    opcao_simples          VARCHAR,
    data_opcao_simples     DATE,
    data_exclusao_simples  DATE,
    opcao_mei              VARCHAR,
    data_opcao_mei         DATE,
    data_exclusao_mei      DATE
);
