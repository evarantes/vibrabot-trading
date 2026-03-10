import OpenAI from "openai";
import type { ResumoAuditoria } from "./auditoria";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY || "",
});

export async function analisarAuditoriaIA(resumo: ResumoAuditoria): Promise<string> {
  if (!process.env.OPENAI_API_KEY) {
    return gerarAnaliseFallback(resumo);
  }

  try {
    const prompt = `Você é um auditor especializado em gestão de enxoval de hotéis. Analise os dados de auditoria abaixo e forneça:

1. DIAGNÓSTICO: Onde está o desfalque? (lavanderia, uso, perda, roubo?)
2. PONTOS CRÍTICOS: Quais itens têm maior perda?
3. RECOMENDAÇÕES: Ações concretas para reduzir o desfalque
4. PADRÕES: Identifique possíveis causas (ex: lavanderia não devolvendo, trocas excessivas)

DADOS DA AUDITORIA:
- Data: ${resumo.data.toISOString().split("T")[0]}
- Total comprado (histórico): ${resumo.totalCompras}
- Em estoque: ${resumo.totalEstoque}
- Na lavanderia: ${resumo.totalLavanderia}
- Em uso nos quartos: ${resumo.totalEmUso}
- Total atual (estoque + lavanderia + uso): ${resumo.totalAtual}
- DESFALQUE: ${resumo.desfalque} itens

DETALHAMENTO POR TIPO:
${resumo.porTipo
  .map(
    (t) =>
      `- ${t.tipoNome}: Comprou ${t.totalCompras} | Estoque ${t.emEstoque} | Lavanderia ${t.naLavanderia} | Uso ${t.emUso} | Desfalque ${t.desfalque}`
  )
  .join("\n")}

Responda em português, de forma objetiva e acionável.`;

    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: prompt }],
      max_tokens: 1000,
    });

    return completion.choices[0]?.message?.content || gerarAnaliseFallback(resumo);
  } catch (error) {
    console.error("Erro na análise IA:", error);
    return gerarAnaliseFallback(resumo);
  }
}

function gerarAnaliseFallback(resumo: ResumoAuditoria): string {
  const itensComDesfalque = resumo.porTipo.filter((t) => t.desfalque > 0);
  const maiorDesfalque = itensComDesfalque.sort((a, b) => b.desfalque - a.desfalque)[0];

  let analise = `## Análise de Auditoria - ${resumo.data.toISOString().split("T")[0]}\n\n`;
  analise += `**Resumo:** Desfalque total de ${resumo.desfalque} itens (${resumo.totalCompras} comprados vs ${resumo.totalAtual} contabilizados).\n\n`;

  if (maiorDesfalque) {
    analise += `**Maior desfalque:** ${maiorDesfalque.tipoNome} (${maiorDesfalque.desfalque} itens)\n\n`;
  }

  const total = resumo.totalAtual || 1;
  analise += `**Distribuição atual:**\n`;
  analise += `- Estoque: ${resumo.totalEstoque} (${((resumo.totalEstoque / total) * 100).toFixed(1)}%)\n`;
  analise += `- Lavanderia: ${resumo.totalLavanderia} (${((resumo.totalLavanderia / total) * 100).toFixed(1)}%)\n`;
  analise += `- Em uso: ${resumo.totalEmUso} (${((resumo.totalEmUso / total) * 100).toFixed(1)}%)\n\n`;

  analise += `**Recomendações:**\n`;
  analise += `1. Verificar se a lavanderia está devolvendo todos os itens enviados\n`;
  analise += `2. Contagem física nos quartos para validar "em uso"\n`;
  analise += `3. Conferir se há itens perdidos ou descartados sem registro\n`;
  analise += `4. Configure OPENAI_API_KEY para análise mais detalhada com IA\n`;

  return analise;
}
