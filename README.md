# Bazar da Escola

App simples em Streamlit para os alunos cadastrarem roupas (nome + valor + quantidade),
acompanharem o estoque total e registrarem vendas. Os dados ficam salvos numa planilha
do Google, então nada se perde entre uma aula e outra.

## Passo 1 — Criar a planilha do Google

1. Acesse https://sheets.google.com e crie uma planilha nova (pode ficar com o nome "Bazar Escola").
2. Na URL da planilha, copie o ID — é o trecho entre `/d/` e `/edit`:
   `https://docs.google.com/spreadsheets/d/ESTE_TRECHO_AQUI/edit`
3. Deixe a planilha em branco. O app cria as abas `itens` e `vendas` sozinho.

## Passo 2 — Criar a credencial de acesso (Service Account)

1. Acesse https://console.cloud.google.com/ e crie um projeto novo (qualquer nome).
2. No menu, vá em **APIs e Serviços > Biblioteca** e ative:
   - **Google Sheets API**
   - **Google Drive API**
3. Vá em **APIs e Serviços > Credenciais > Criar Credenciais > Conta de serviço**.
   - Dê um nome (ex: `bazar-escola`) e conclua a criação.
4. Clique na conta de serviço criada > aba **Chaves** > **Adicionar chave > Criar nova chave > JSON**.
   Isso baixa um arquivo `.json` — guarde-o, você vai precisar dele no Passo 4.
5. Copie o e-mail da conta de serviço (algo como `bazar-escola@seu-projeto.iam.gserviceaccount.com`).

## Passo 3 — Compartilhar a planilha com a conta de serviço

Na planilha do Passo 1, clique em **Compartilhar** e adicione o e-mail da conta de
serviço (copiado no Passo 2) com permissão de **Editor**.

## Passo 4 — Configurar os "secrets" do app

1. Renomeie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
2. Preencha `planilha_id` com o ID copiado no Passo 1.
3. Abra o arquivo `.json` baixado no Passo 2 e copie cada campo para dentro de
   `[gcp_service_account]` no `secrets.toml` (os nomes dos campos são iguais).
   Atenção especial ao campo `private_key`: copie o valor inteiro, incluindo os `\n`.

Esse arquivo **nunca deve ir para o GitHub** (já está no `.gitignore`).

## Passo 5 (opcional) — Testar no seu computador

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Passo 6 — Subir para o GitHub

Crie um repositório novo no GitHub e suba esta pasta (`app.py`, `requirements.txt`,
`.gitignore`, `.streamlit/secrets.toml.example`). **Não suba o `secrets.toml` real.**

## Passo 7 — Deploy no Streamlit Community Cloud (grátis)

1. Acesse https://share.streamlit.io/ e faça login com sua conta GitHub.
2. Clique em **New app**, escolha o repositório e o arquivo `app.py`.
3. Antes de clicar em Deploy, vá em **Advanced settings > Secrets** e cole o
   conteúdo do seu `secrets.toml` real (o mesmo do Passo 4).
4. Clique em **Deploy**. Em cerca de 1 minuto o app estará no ar, com uma URL do tipo:
   `https://seu-app.streamlit.app`

## Passo 8 — Passar o link para os alunos

Envie a URL gerada no Passo 7. Todos os alunos vão cadastrar itens e registrar vendas
no mesmo estoque compartilhado, e os totais (quantidade e valor) são calculados
automaticamente nas abas "Estoque" e "Vendas" do app.
