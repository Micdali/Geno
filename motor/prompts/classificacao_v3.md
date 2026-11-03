Você classifica empresas do setor de educação livre (cursos de idiomas, treinamentos, cursos preparatórios, cursos livres em geral) a partir do texto público do site delas.

Regras:
- site_de_ensino: true se a empresa vende cursos, aulas ou treinamentos, mesmo que venda outros serviços junto (ex.: consultoria de segurança do trabalho que também dá cursos). false se o texto não mostra nenhum curso, aula ou treinamento vendido pela empresa: outro ramo (contabilidade, advocacia, provedor de internet, loja), site "em construção", página genérica ou site de uma entidade que não é a empresa (ex.: sede estrangeira de uma instituição). Quando houver serviços e cursos, descreva nos campos só a parte de ensino. Se for false, preencha todos os outros campos com "indeterminado" e confianca "baixa".
- Use SOMENTE o que está escrito no texto. Não complete com conhecimento próprio sobre a marca.
- Quando o texto não disser, responda exatamente "indeterminado". Isso é melhor que um palpite.
- Escreva em português, curto e concreto (no máximo 12 palavras por campo de texto).
- publico_atendido: para quem a empresa vende (ex.: "crianças de 4 a 12 anos", "adultos iniciantes", "empresas", "candidatos a concursos policiais").
- produto_servico: o que entrega, mais específico que o ramo (ex.: "aulas de inglês em grupo", "curso preparatório para o ENEM", "treinamento de liderança in company").
- canal_atendimento: "presencial", "online", "delivery" (vai até o cliente: aula em domicílio ou na empresa), "hibrido" (presencial e online) ou "indeterminado".
- problema_resolvido: a dor ou o objetivo do cliente que a empresa diz resolver.
- modelo_receita: como cobra, se o texto disser. "pacote_ou_mensalidade" para cursos com mensalidade ou pacote de aulas; "assinatura" para acesso recorrente a plataforma; "venda_avulsa" para cursos ou aulas vendidos um a um.
- posicionamento: como ela se diferencia, nas palavras do site (ex.: "método próprio", "preço acessível", "professores nativos").
- descricao_nicho: uma frase que junta público, serviço e canal (ex.: "inglês online em grupo para adultos iniciantes").
- confianca: "alta" se o texto descreve claramente público e serviço; "media" se só parte está clara; "baixa" se o texto é vago, genérico ou parece não ser da empresa.

Atividade principal registrada (CNAE): {cnae}

Texto do site:
"""
{texto}
"""
