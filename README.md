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
   - com edição completa (nome, categoria, par level, ativo, valor unitário de lavagem)
2. **Lançamentos diários** de movimentação:
   - compra,
   - envio para lavanderia,
   - retorno da lavanderia,
   - relavagem (reenvio sem cobrança e retorno),
   - alocação para uso,
   - retorno de uso,
   - perdas/baixas.
3. **Contagem física diária** (estoque, lavanderia e em uso).
4. **Dashboard operacional** com posição teórica consolidada.
5. **Auditoria IA** com:
   - score de risco geral,
   - divergências físico x teórico,
   - peças retidas na lavanderia por tempo anormal,
   - taxa de relavagem por qualidade de lavagem,
   - tendências de perda,
   - ações recomendadas de investigação.
6. **Apuração de lavanderia estilo planilha**:
   - colunas diárias (quinzena/mês),
   - total de peças cobradas,
   - valor total por item (valor unitário x total),
   - relave enviado/retornado (sem cobrança),
   - perdas no período.
7. **Operação por unidade independente**:
   - **La Plage** e **Club** com catálogos próprios de itens,
   - preços de lavagem independentes,
   - idas/voltas da lavanderia, relave e perdas independentes.

---

## Arquitetura

- **Frontend/App:** Streamlit (`app.py`)
- **Persistência principal:** PostgreSQL
- **Núcleo de auditoria:** `src/codexiaauditor/audit_engine.py`
- **Camada de dados:** `src/codexiaauditor/repository.py`
- **Separação operacional:** unidade `HOTEL` e `CLUB`

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

1. Escolher unidade no menu lateral (`LA_PLAGE` ou `CLUB`).
2. Cadastrar/editar itens na tela **Cadastro de Itens** (catálogo por unidade).
3. Registrar envios/retornos da lavanderia na tela **Lançamentos Lavanderia**.
4. Usar **Relavagem** quando lote retorna mal lavado (sem cobrança extra).
5. Registrar compras, transferências central/uso e perdas em **Estoque Central e de Uso**.
6. Fazer contagem física diária em **Contagem Física**.
7. Acompanhar posições em **Painel de Controle** e investigar alertas em **Auditoria IA**.
8. Validar cobrança na tela **Apuração Lavanderia (Planilha)** para quinzena/mensalidade.

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