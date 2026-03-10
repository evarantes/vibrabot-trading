# CODEXIAAUDITOR

**Sistema de Auditoria de Enxoval para Hotéis com IA**

Sistema completo para rastrear e auditar o enxoval do hotel, identificar desfalques e obter análises inteligentes com IA.

## Funcionalidades

- **Compras**: Registro do que foi comprado de enxoval (lençóis, toalhas, fronhas, etc.)
- **Estoque**: Controle do que está disponível no almoxarifado
- **Lavanderia**: Acompanhamento diário do que sai e volta da lavanderia
- **Em Uso**: Itens nos quartos em uso pelos hóspedes
- **Desfalque**: Cálculo automático (Compras - Estoque - Lavanderia - Uso)
- **Análise com IA**: Identificação de onde está o erro e recomendações acionáveis

## Fluxo de Movimentação

```
COMPRA → Estoque
Estoque → Lavanderia (envio diário)
Lavanderia → Estoque (retorno)
Estoque → Uso (colocação no quarto)
Uso → Lavanderia (retorno do quarto - roupa suja)
```

## Instalação

```bash
# Instalar dependências
npm install

# Configurar banco de dados
npx prisma generate
npx prisma db push
npx prisma db seed

# Configurar variáveis (opcional - para análise com IA)
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY

# Iniciar em desenvolvimento
npm run dev
```

Acesse [http://localhost:3000](http://localhost:3000)

## Uso

1. **Registrar Compras**: Ao comprar enxoval, registre no sistema (entra automaticamente no estoque)
2. **Movimentações Diárias**:
   - **Saída para Lavanderia**: Quando envia roupa suja
   - **Retorno da Lavanderia**: Quando recebe de volta
   - **Saída para Uso**: Ao colocar no quarto
   - **Retorno do Uso**: Quando o hóspede sai (vai para lavanderia)
3. **Executar Auditoria**: O dashboard mostra em tempo real o estado
4. **Análise com IA**: Clique em "Análise com IA" para diagnóstico detalhado

## Tecnologias

- Next.js 14, React, TypeScript
- Prisma + SQLite
- Tailwind CSS
- OpenAI API (opcional)
- Recharts

## Estrutura

```
/app          - Páginas e API routes
/components   - Componentes React
/lib          - Lógica de auditoria e IA
/prisma       - Schema e seed do banco
```

## Licença

MIT
