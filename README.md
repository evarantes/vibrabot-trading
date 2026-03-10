# CodexiaAuditor 🏨

**Sistema de Auditoria de Enxoval Hoteleiro com Inteligência Artificial**

O CodexiaAuditor é um sistema completo para controle e auditoria do enxoval de hotéis, permitindo identificar desfalques com precisão através de rastreabilidade total das peças.

---

## Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| **Dashboard** | Visão geral com KPIs, gráficos e alertas automáticos |
| **Tipos de Enxoval** | Cadastro de lençóis, toalhas, fronhas, roupões etc. |
| **Compras** | Registro de todas as aquisições com NF e fornecedor |
| **Estoque** | Controle de entradas, saídas, perdas e descartes |
| **Lavanderia** | Rastreamento diário de envios e retornos por lote |
| **Quartos** | Enxoval atribuído a cada quarto com histórico |
| **Auditoria IA** | Análise inteligente de desfalques com diagnóstico e recomendações |

---

## Como funciona a Auditoria

A fórmula de controle é simples:

```
Desfalque = Total Comprado - (Estoque + Na Lavanderia + Em Uso nos Quartos)
```

Qualquer diferença positiva indica peças não contabilizadas — possível furto, perda ou erro de registro.

---

## Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Inicialização rápida (ambos juntos)

```bash
./start.sh
```

### Acessos

- **Aplicação:** http://localhost:5173
- **API REST:** http://localhost:8000
- **Documentação API:** http://localhost:8000/docs

---

## Configuração da IA

Para ativar a análise avançada com GPT-4, crie o arquivo `backend/.env`:

```env
OPENAI_API_KEY=sk-sua-chave-aqui
```

> Sem a chave, o sistema utiliza análise heurística interna igualmente eficiente.

---

## Fluxo de uso recomendado

1. **Cadastre os tipos de enxoval** (ou use os padrões sugeridos)
2. **Registre as compras** realizadas com quantidade e fornecedor
3. **Controle o estoque** com movimentações diárias
4. **Registre os envios** para lavanderia e confirme os retornos
5. **Atribua peças** aos quartos conforme a distribuição
6. **Gere auditorias** periodicamente para detectar desfalques

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + SQLAlchemy + SQLite |
| Frontend | React + TypeScript + Tailwind CSS |
| Gráficos | Recharts |
| IA | OpenAI GPT-4o-mini (opcional) |

---

*Desenvolvido para gestão hoteleira profissional de enxoval.*
