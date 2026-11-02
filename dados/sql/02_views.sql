-- =====================================================================
-- Visões do GENO (dono: Lucas). Aplicadas DEPOIS de contratos/01_schema.sql e 01_schema_extra.sql.
--
-- vw_eventos substitui a do contrato com as MESMAS colunas na mesma ordem, mais duas ao final
-- (classe_baixa, baixa_em_massa). Quem lê só as colunas antigas não percebe a mudança.
-- A classe do motivo vem de motivo_classe (seed dados/sql/seeds/motivo_classe.csv).
-- =====================================================================

-- Eventos de abertura e baixa, base das séries de saturação.
--   ano_baixa      : ano de qualquer baixa (situação 08), como no contrato
--   classe_baixa   : 'voluntaria' | 'oficio' | 'outra'; NULL se não está baixada
--   baixa_em_massa : true quando a baixa é de ofício (classe 'oficio'); false nos demais casos
CREATE OR REPLACE VIEW vw_eventos AS
SELECT
    e.cnpj,
    year(e.data_inicio)                                           AS ano_abertura,
    CASE WHEN e.situacao = '08' THEN year(e.data_situacao) END    AS ano_baixa,
    e.situacao,
    e.motivo_situacao                                             AS motivo,
    CASE WHEN e.situacao = '08' THEN mc.classe END                AS classe_baixa,
    coalesce(e.situacao = '08' AND mc.classe = 'oficio', false)   AS baixa_em_massa
FROM estabelecimento e
LEFT JOIN motivo_classe mc ON mc.codigo_motivo = e.motivo_situacao;
