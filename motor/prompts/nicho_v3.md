Uma pessoa sem experiência em negócios descreveu uma ideia. Seu trabalho é dizer, em palavras simples, qual é o nicho dessa ideia dentro do setor de educação livre no estado do Rio de Janeiro.

Regras:
- Não avalie se a ideia é boa. Nunca diga para abrir ou não abrir o negócio, nem use a palavra "validar".
- atributos.publico: para quem é (ex.: "adultos 40+ iniciantes").
- atributos.produto_servico: o que entrega (ex.: "aulas de inglês ao vivo em grupo").
- atributos.canal: "presencial", "online", "delivery" (vai até o cliente), "hibrido" ou "indeterminado".
- descricao: uma linha curta no formato "ramo · serviço · público · canal".
- cnaes: os códigos da lista abaixo que melhor delimitam o ramo (1 ou 2, o mais provável primeiro).
- no_piloto: true se a ideia é de ensino, cursos, aulas, treinamento ou capacitação (o setor que o Geno analisa); false se for de outro ramo (ex.: café, loja de roupas, salão de beleza, restaurante). Quando for false, devolva perguntas vazia.
- perguntas: até {max_perguntas} perguntas curtas que mais mudariam o recorte. Só pergunte o que a ideia deixou em aberto. Se a ideia já está clara, devolva lista vazia.
  - opcoes: de 2 a 5 opções curtas; a última é sempre "Não sei ainda". Não inclua "Outro": a tela já oferece essa opção com texto livre.
  - multipla: true quando a pessoa pode marcar mais de uma opção ao mesmo tempo (ex.: públicos, formatos ou canais que podem coexistir); false quando as opções se excluem (ex.: faixa de preço, um único local).

Códigos de CNAE do setor:
{cnaes}

Ideia:
"""
{ideia}
"""
{respostas}
