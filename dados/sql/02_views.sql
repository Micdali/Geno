-- =====================================================================
-- Visões do GENO (dono: Lucas). Aplicadas DEPOIS de contratos/01_schema.sql.
--
-- vw_eventos substitui a do contrato com as MESMAS colunas na mesma ordem, mais duas ao final
-- (tipo_baixa, conta_mortalidade). Quem lê só as colunas antigas não percebe a mudança.
-- A classificação dos motivos vem da tabela motivo_tipo (preenchida a partir de
-- dados/config.yaml, seção `baixas`) e está A CONFIRMAR PELO GRUPO.
-- =====================================================================

-- Tipo de cada motivo de situação cadastral (não faz parte do contrato 1; é tabela auxiliar).
CREATE OR REPLACE TABLE motivo_tipo (
    codigo  VARCHAR PRIMARY KEY,   -- -> motivo.codigo
    tipo    VARCHAR                -- 'voluntaria' | 'judicial' | 'obito_mei' | 'oficio' | 'reorganizacao' | 'outro'
);

-- Eventos de abertura e baixa, base das séries de saturação.
--   ano_baixa      : ano de qualquer baixa (situação 08), como no contrato
--   tipo_baixa     : classificação do motivo; NULL se não está baixada
--   conta_mortalidade : true só para baixas que indicam fechamento do negócio; baixas de ofício
--                       (omissão, inaptidão) e reorganizações não contam
CREATE OR REPLACE VIEW vw_eventos AS
SELECT
    e.cnpj,
    year(e.data_inicio)                                           AS ano_abertura,
    CASE WHEN e.situacao = '08' THEN year(e.data_situacao) END    AS ano_baixa,
    e.situacao,
    e.motivo_situacao                                             AS motivo,
    CASE WHEN e.situacao = '08' THEN coalesce(t.tipo, 'outro') END AS tipo_baixa,
    coalesce(e.situacao = '08'
             AND coalesce(t.tipo, 'outro') IN ('voluntaria', 'judicial', 'obito_mei'), false)
                                                                  AS conta_mortalidade
FROM estabelecimento e
LEFT JOIN motivo_tipo t ON t.codigo = e.motivo_situacao;

