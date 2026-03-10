# CODEXIAAUDITOR

Sistema web para auditoria de enxoval hoteleiro com foco em descobrir desvios, perdas operacionais e falhas de rastreabilidade entre compras, estoque, lavanderia e uso diario.

## Proposta do produto

O CODEXIAAUDITOR foi reposicionado para atender hoteis que precisam responder perguntas como:

- O que foi comprado de enxoval?
- O que esta no estoque agora?
- O que saiu e voltou da lavanderia hoje?
- O que esta em uso nos quartos e na operacao?
- Quantas pecas nao estao conciliadas?
- Em qual setor esta o maior risco de desfalque?

## O que esta implementado neste MVP

- Painel executivo com resumo operacional do enxoval
- Controle visual de comprado, estoque, lavanderia, uso e perdas
- Tabela de auditoria por item
- Timeline de movimentos diarios
- Cadastro manual de movimentos operacionais
- Motor de analise inteligente para apontar:
  - pecas nao conciliadas
  - valor financeiro em risco
  - retorno de lavanderia abaixo do esperado
  - setores prioritarios para investigacao
  - proximos passos recomendados

## Como a analise funciona

A inteligencia operacional do MVP cruza:

`comprado total - (estoque atual + em lavanderia + em uso + perdas registradas)`

Com isso, o sistema identifica pecas desaparecidas ou nao conciliadas e sugere o ponto mais provavel do erro com base em:

- baixa taxa de retorno da lavanderia
- estoque abaixo do minimo
- grande volume em uso
- perdas registradas acima do esperado
- concentracao de risco por setor

## Tecnologias

- React
- TypeScript
- Vite
- LocalStorage para persistencia local de demonstracao

## Como rodar

```bash
npm install
npm run dev
```

Para gerar a versao de producao:

```bash
npm run build
```

## Estrutura principal

- `src/App.tsx`: dashboard, formularios e timeline
- `src/analysis.ts`: motor de auditoria e priorizacao de risco
- `src/data.ts`: base demo inicial
- `src/storage.ts`: persistencia local
- `src/types.ts`: contratos de dados

## Proximos passos recomendados

Para evoluir este MVP para operacao real de hotel:

1. adicionar autenticacao por perfil
2. conectar banco de dados real
3. criar cadastro de unidades, setores, quartos e fornecedores
4. integrar romaneios de lavanderia
5. adicionar OCR, RFID ou leitura por codigo
6. integrar um modelo de IA externo para narrativas, alertas e previsoes

## Observacao sobre o nome do repositorio

O projeto e a aplicacao foram renomeados para **CODEXIAAUDITOR** dentro do codigo. Se voce quiser que o nome do repositorio remoto no GitHub tambem mude, isso ainda precisa ser feito diretamente na plataforma onde o repositorio esta hospedado.