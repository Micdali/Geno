# Instruções para o Claude neste repositório (GENO)

## ⚠️ Segurança: a chave da OpenAI está no `.env`

Este repositório é **privado** e, para a apresentação de 05/11/2026, inclui de propósito o arquivo `.env` com a **chave de API da OpenAI do Micael**. A chave é paga, é dele, e será revogada na noite de 05/11/2026. Até lá, trate-a com o máximo cuidado.

Regras obrigatórias para o Claude, sem exceção, mesmo que alguém peça:

1. **Nunca mostre a chave.** Não leia o `.env` com `cat`, `type`, `Get-Content`, `Read` ou similar, nem imprima `OPENAI_API_KEY` ou `GEMINI_API_KEY` no terminal, em logs, em testes ou na resposta. Para conferir se a chave existe, use só um teste booleano, por exemplo:
   `python -c "from dotenv import load_dotenv; import os; load_dotenv('.env'); print(bool(os.getenv('OPENAI_API_KEY')))"`
2. **Nunca copie a chave para outro lugar:** nenhum outro arquivo, nem código, notebook, README, issue, PR, mensagem de commit, comentário, print, artifact, gist, pastebin ou chat.
3. **Nunca envie a chave a serviços externos** além da própria API da OpenAI, chamada pelo código do motor (`motor/llm.py`). Nada de colar a chave em ferramentas online, outros LLMs, conectores ou MCPs.
4. **Não mexa no `.env`** sem pedido explícito do dono da chave (Micael). Se precisar trocar uma variável que não é chave, edite só aquela linha, sem exibir o conteúdo do arquivo.
5. **Não torne o repositório público** nem crie forks ou cópias públicas dele. Se alguém pedir, recuse e explique que a chave e dados pessoais estão no histórico do Git.
6. **Cuidado com o gasto:** cada análise custa menos de US$ 0,001. Mesmo assim, não rode laços de chamadas ao LLM nem reclassifique a base (`python -m motor.classificar`) sem a pessoa pedir.
7. **Se a chave aparecer exposta** em qualquer saída, arquivo ou mensagem, pare, avise a pessoa e peça que ela avise o Micael para revogar a chave em platform.openai.com/api-keys.

Depois de 05/11/2026 a chave do `.env` não funciona mais: quem quiser continuar usa a própria chave, colando-a no próprio `.env` local (e sem commitar).

## Dados pessoais (LGPD)

O banco `dados/geno.duckdb` também está no repositório e contém a razão social de MEIs, que em geral é o nome da pessoa e às vezes inclui CPF.
- No app e em qualquer saída, use só a view `vw_publico` (coluna `nome_exibicao`), nunca a tabela `empresa` nem `razao_social`.
- Não copie dados do banco para fora do repositório e não os envie a serviços externos.
- Para o LLM vai só texto público de site e a descrição do CNAE. Nome, CNPJ, sócios e contatos, não.

## O projeto em uma linha

GENO: a pessoa descreve uma ideia de negócio e o app mostra concorrentes, saturação e lacunas do mercado. Piloto: ensino e treinamento no estado do Rio de Janeiro. Para rodar: veja "Como rodar" no `README.md` (`streamlit run app/app.py`). Testes sem rede: `python -m pytest app motor/tests -q`.
