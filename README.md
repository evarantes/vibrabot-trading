# CodexiaAuditor

Sistema inteligente de auditoria e controle de enxoval hoteleiro com analise por IA.

## Sobre o Projeto

O CodexiaAuditor foi desenvolvido para resolver o problema de desfalque de enxoval em hoteis. O sistema rastreia todo o ciclo de vida do enxoval - desde a compra ate o uso nos quartos, passando pelo estoque e lavanderia - e utiliza inteligencia artificial para identificar discrepancias, perdas e gerar recomendacoes.

### Funcionalidades

- **Dashboard** - Visao geral com metricas, graficos de distribuicao e historico de lavanderia
- **Compras** - Registro completo de compras com fornecedor, nota fiscal e preco
- **Estoque** - Controle de estoque com contagem diaria e alertas de nivel baixo
- **Lavanderia** - Acompanhamento diario de envio, retorno e danos na lavanderia
- **Em Uso** - Registro de enxoval distribuido por quarto
- **Auditoria IA** - Analise inteligente que cruza todos os dados para identificar:
  - Pecas desaparecidas e percentual de desfalque
  - Taxa de retorno da lavanderia por item
  - Inconsistencias entre compras e estoque
  - Nivel de risco (critico, alto, medio, baixo, ok)
  - Recomendacoes de acoes corretivas

### Formula de Auditoria

```
Total Esperado = Soma de todas as compras
Localizado = Estoque + Na Lavanderia + Em Uso
Desaparecido = Total Esperado - Localizado
```

## Tecnologias

- **Next.js 16** - Framework React com App Router
- **TypeScript** - Tipagem estatica
- **Tailwind CSS** - Estilizacao
- **Prisma 7** - ORM com SQLite
- **Recharts** - Graficos
- **Lucide React** - Icones

## Instalacao

```bash
# Clonar repositorio
git clone <url-do-repositorio>
cd codexia-auditor

# Instalar dependencias
npm install

# Setup do banco (gerar client + migrar + dados de exemplo)
npm run setup
```

## Executar

```bash
# Modo desenvolvimento
npm run dev

# Build para producao
npm run build
npm start
```

## Scripts Disponíveis

| Comando | Descricao |
|---------|-----------|
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Build de producao |
| `npm start` | Servidor de producao |
| `npm run db:migrate` | Executar migracoes |
| `npm run db:seed` | Popular com dados de exemplo |
| `npm run db:reset` | Resetar banco e repopular |
| `npm run db:studio` | Abrir Prisma Studio |
| `npm run setup` | Setup completo (gerar + migrar + popular) |

## Estrutura do Projeto

```
src/
├── app/
│   ├── api/           # API Routes (REST)
│   │   ├── audit/     # Executar auditoria IA
│   │   ├── categories/# CRUD de categorias
│   │   ├── dashboard/ # Dados do dashboard
│   │   ├── items/     # CRUD de itens
│   │   ├── laundry/   # Registros de lavanderia
│   │   ├── purchases/ # Registros de compras
│   │   ├── room-usage/# Uso nos quartos
│   │   └── stock/     # Contagem de estoque
│   ├── auditoria/     # Pagina de auditoria IA
│   ├── compras/       # Pagina de compras
│   ├── em-uso/        # Pagina de enxoval em uso
│   ├── estoque/       # Pagina de estoque
│   ├── lavanderia/    # Pagina de lavanderia
│   └── page.tsx       # Dashboard
├── components/        # Componentes reutilizaveis
├── lib/
│   ├── audit-engine.ts# Motor de auditoria IA
│   ├── prisma.ts      # Cliente Prisma
│   └── utils.ts       # Utilitarios
└── generated/         # Prisma Client gerado
```
