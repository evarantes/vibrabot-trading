# CODEXIAAUDITOR

Sistema de **auditoria inteligente de enxoval hoteleiro** para identificar desfalques e falhas operacionais entre:

- compras de enxoval,
- estoque teórico x físico,
- envio/retorno de lavanderia,
- peças em uso na operação.

O objetivo é apontar rapidamente **onde está o erro** usando análise automática (IA baseada em regras de risco e detecção de anomalias).

---

## O que o sistema faz

1. **Cadastro de itens de enxoval** (lençol, toalha, fronha etc.)
2. **Lançamentos diários** de movimentação:
   - compra,
   - envio para lavanderia,
   - retorno da lavanderia,
   - alocação para uso,
   - retorno de uso,
   - perdas/baixas.
3. **Contagem física diária** (estoque, lavanderia e em uso).
4. **Dashboard operacional** com posição teórica consolidada.
5. **Auditoria IA** com:
   - score de risco geral,
   - divergências físico x teórico,
   - peças retidas na lavanderia por tempo anormal,
   - tendências de perda,
   - ações recomendadas de investigação.

---

## Arquitetura

- **Frontend/App:** Streamlit (`app.py`)
- **Persistência principal:** PostgreSQL
- **Núcleo de auditoria:** `src/codexiaauditor/audit_engine.py`
- **Camada de dados:** `src/codexiaauditor/repository.py`

---

## Como executar

### 1) Criar ambiente virtual (opcional, recomendado)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Instalar dependências

```bash
python3 -m pip install -r requirements.txt
```

### 3) Subir PostgreSQL

```bash
docker compose up -d postgres
```

### 4) Configurar variáveis de ambiente

```bash
cp .env.example .env
export CODEXIAAUDITOR_DB_ENGINE=postgres
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/codexiaauditor
```

### 5) Subir o sistema

```bash
streamlit run app.py
```

---

## Testes

```bash
export CODEXIAAUDITOR_DB_ENGINE=sqlite
pytest
```

> Observação: em produção/uso real, o sistema está configurado para PostgreSQL.

---

## Fluxo sugerido de operação diária

1. Registrar compras e movimentações de enxoval.
2. Registrar o que foi e voltou da lavanderia.
3. Registrar alocações e retornos de uso.
4. Fazer contagem física no fechamento.
5. Abrir aba **Auditoria IA** para investigar alertas e agir no mesmo dia.

---

## Deploy no Coolify (passo a passo)

### Pré-requisitos

- Repositório no GitHub com estes arquivos atualizados.
- Instância do Coolify funcionando.
- Domínio/subdomínio para o app (ex: `auditoria.seuhotel.com`).

### 1) Criar o banco PostgreSQL no Coolify

1. No Coolify, clique em **New Resource**.
2. Escolha **Database** > **PostgreSQL**.
3. Defina nome (ex: `codexiaauditor-db`) e crie o recurso.
4. Abra o recurso do banco e copie os dados de conexão:
   - host,
   - porta,
   - database,
   - user,
   - password.

### 2) Criar a aplicação no Coolify

1. No Coolify, clique em **New Resource**.
2. Escolha **Application** > **Public Repository** (ou conecte seu GitHub).
3. Selecione este repositório e a branch desejada.
4. Em **Build Pack**, escolha **Dockerfile**.
5. Defina a **Port** da aplicação como `8501`.
6. Clique em **Save**.

### 3) Configurar variáveis de ambiente da aplicação

Em **Environment Variables**, adicione:

- `CODEXIAAUDITOR_DB_ENGINE=postgres`
- `DATABASE_URL=postgresql://USUARIO:SENHA@HOST:PORTA/NOME_DO_BANCO`

> Use exatamente os dados do PostgreSQL criado no Coolify.

### 4) Configurar domínio e HTTPS

1. Em **Domains**, adicione seu domínio/subdomínio.
2. Ative **Generate SSL** (Let's Encrypt).
3. Salve.

### 5) Deploy

1. Clique em **Deploy**.
2. Aguarde o build e o start do container.
3. Abra o domínio configurado.
4. Na primeira carga, o sistema já cria automaticamente as tabelas no PostgreSQL.

### 6) Checklist de produção para hoje

- [ ] App abre no domínio.
- [ ] Consigo cadastrar item.
- [ ] Consigo registrar movimento.
- [ ] Consigo registrar contagem física.
- [ ] Aba **Auditoria IA** mostra score e alertas.
- [ ] Dados persistem após reinício do container.