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
   - no módulo **Cadastro de Itens (Central)**,
   - categoria escolhida por lista (com botão para criar categoria),
   - edição completa (nome, categoria, nível mínimo, ativo/inativo).
2. **Lançamento de estoque central logo abaixo do cadastro**
   - data da compra/movimento,
   - item,
   - tipo de movimentação,
   - quantidade,
   - número da NF,
   - valor unitário de compra,
   - valor total,
   - observação.
3. **Lançamentos diários** de movimentação:
   - compra,
   - envio para lavanderia,
   - retorno da lavanderia,
   - relavagem (reenvio sem cobrança e retorno),
   - alocação para uso,
   - retorno de uso,
   - perdas/baixas.
4. **Contagem física diária** (estoque, lavanderia e em uso).
5. **Dashboard operacional** com posição teórica consolidada.
   - alerta crítico automático quando estoque atinge nível mínimo.
6. **Auditoria IA** com:
   - score de risco geral,
   - divergências físico x teórico,
   - peças retidas na lavanderia por tempo anormal,
   - taxa de relavagem por qualidade de lavagem,
   - tendências de perda,
   - ações recomendadas de investigação.
7. **Apuração de lavanderia estilo planilha**:
   - colunas diárias (quinzena/mês),
   - total de peças cobradas,
   - valor total por item (valor unitário x total),
   - relave enviado/retornado (sem cobrança),
   - perdas no período.
8. **Fluxo com estoque central + unidades independentes**:
   - cadastro mestre de itens no **CENTRAL**,
   - transferência do CENTRAL para **HOTEL** e **CLUB**,
   - preços de lavagem independentes por unidade,
   - idas/voltas da lavanderia, relave e perdas independentes por unidade.

---

## Arquitetura

- **Frontend/App:** Streamlit (`app.py`)
- **Persistência principal:** PostgreSQL
- **Núcleo de auditoria:** `src/codexiaauditor/audit_engine.py`
- **Camada de dados:** `src/codexiaauditor/repository.py`
- **Separação operacional:** `CENTRAL`, `HOTEL` e `CLUB`

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

1. Cadastrar/editar itens no módulo **Cadastro de Itens (Central)**.
2. Lançar compras e saldo no **CENTRAL** em **Estoque Central e de Uso**.
3. Transferir itens em **Transferir Central -> Unidade** para HOTEL/CLUB.
4. Lançar lavanderia e relave separadamente em HOTEL e CLUB.
5. Fazer contagem física diária em cada unidade.
6. Acompanhar painéis e auditoria IA por unidade.
7. Validar cobrança quinzenal/mensal na **Apuração Lavanderia (Planilha)**.

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