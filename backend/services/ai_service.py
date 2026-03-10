import os
import json
from typing import List, Dict, Any
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def calcular_auditoria(dados_auditoria: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula o desfalque e gera métricas de auditoria."""
    itens_detalhados = []
    total_comprado_geral = 0
    total_contabilizado_geral = 0
    total_desfalque_geral = 0
    total_estoque_geral = 0
    total_lavanderia_geral = 0
    total_em_uso_geral = 0

    for item in dados_auditoria.get("itens", []):
        comprado = item.get("total_comprado", 0)
        estoque = item.get("saldo_estoque", 0)
        lavanderia = item.get("na_lavanderia", 0)
        em_uso = item.get("em_uso", 0)

        contabilizado = estoque + lavanderia + em_uso
        desfalque = comprado - contabilizado
        percentual = (desfalque / comprado * 100) if comprado > 0 else 0

        total_comprado_geral += comprado
        total_contabilizado_geral += contabilizado
        total_desfalque_geral += desfalque
        total_estoque_geral += estoque
        total_lavanderia_geral += lavanderia
        total_em_uso_geral += em_uso

        itens_detalhados.append({
            "item_type_id": item["item_type_id"],
            "item_nome": item["item_nome"],
            "categoria": item["categoria"],
            "total_comprado": comprado,
            "total_estoque": estoque,
            "total_na_lavanderia": lavanderia,
            "total_em_uso": em_uso,
            "total_contabilizado": contabilizado,
            "desfalque": desfalque,
            "percentual_desfalque": round(percentual, 2)
        })

    itens_detalhados.sort(key=lambda x: x["desfalque"], reverse=True)

    return {
        "itens_detalhados": itens_detalhados,
        "totais": {
            "total_comprado": total_comprado_geral,
            "total_estoque": total_estoque_geral,
            "total_na_lavanderia": total_lavanderia_geral,
            "total_em_uso": total_em_uso_geral,
            "total_contabilizado": total_contabilizado_geral,
            "total_desfalque": total_desfalque_geral,
            "percentual_desfalque_geral": round(
                (total_desfalque_geral / total_comprado_geral * 100)
                if total_comprado_geral > 0 else 0, 2
            )
        }
    }


def gerar_analise_ia(dados_auditoria: Dict[str, Any], resultado_calculo: Dict[str, Any]) -> str:
    """Gera análise inteligente da auditoria, usando IA ou análise heurística."""
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key and OPENAI_AVAILABLE:
        return _analise_com_openai(dados_auditoria, resultado_calculo, api_key)
    else:
        return _analise_heuristica(resultado_calculo)


def _analise_com_openai(
    dados_auditoria: Dict[str, Any],
    resultado_calculo: Dict[str, Any],
    api_key: str
) -> str:
    """Gera análise usando a API da OpenAI."""
    try:
        client = OpenAI(api_key=api_key)
        totais = resultado_calculo["totais"]
        itens = resultado_calculo["itens_detalhados"]

        prompt = f"""Você é um auditor especialista em gestão de enxoval hoteleiro. 
Analise os dados abaixo e forneça um relatório de auditoria detalhado em português.

## DADOS DA AUDITORIA

### Totais Gerais:
- Total Comprado: {totais['total_comprado']} peças
- Total em Estoque: {totais['total_estoque']} peças
- Total na Lavanderia: {totais['total_na_lavanderia']} peças
- Total em Uso (quartos): {totais['total_em_uso']} peças
- Total Contabilizado: {totais['total_contabilizado']} peças
- **DESFALQUE TOTAL: {totais['total_desfalque']} peças ({totais['percentual_desfalque_geral']}%)**

### Detalhamento por Item:
{json.dumps(itens, ensure_ascii=False, indent=2)}

### Contexto:
- Período analisado: {dados_auditoria.get('periodo', 'Geral')}
- Data da auditoria: {datetime.now().strftime('%d/%m/%Y %H:%M')}

## ANÁLISE SOLICITADA:

1. **Diagnóstico Geral**: Avalie a gravidade do desfalque encontrado
2. **Itens Críticos**: Identifique os 3 itens com maior desfalque percentual e absoluto
3. **Causas Prováveis**: Liste as causas mais prováveis para os desfalques (furto, perda na lavanderia, mau controle, etc.)
4. **Pontos de Atenção**: Onde provavelmente está ocorrendo o maior problema
5. **Recomendações**: Ações específicas para corrigir o problema e evitar futuros desfalques
6. **Plano de Ação Imediato**: 3-5 ações prioritárias para investigação

Seja direto, objetivo e use linguagem profissional adequada para um gestor hoteleiro."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um auditor especialista em gestão hoteleira e controle de enxoval."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )

        return response.choices[0].message.content or _analise_heuristica(resultado_calculo)

    except Exception as e:
        return f"[Análise IA indisponível: {str(e)}]\n\n" + _analise_heuristica(resultado_calculo)


def _analise_heuristica(resultado_calculo: Dict[str, Any]) -> str:
    """Gera análise heurística baseada em regras quando a IA não está disponível."""
    totais = resultado_calculo["totais"]
    itens = resultado_calculo["itens_detalhados"]
    percentual = totais["percentual_desfalque_geral"]

    linhas = []
    linhas.append("# RELATÓRIO DE AUDITORIA DE ENXOVAL HOTELEIRO")
    linhas.append(f"\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append(f"\n---\n")

    # Diagnóstico Geral
    linhas.append("## 1. DIAGNÓSTICO GERAL\n")
    if percentual == 0:
        linhas.append("✅ **Situação EXCELENTE**: Nenhum desfalque detectado. Todos os itens estão contabilizados.")
    elif percentual <= 2:
        linhas.append(f"🟡 **Situação ACEITÁVEL**: Desfalque de {percentual}% está dentro da margem tolerável para operações hoteleiras.")
    elif percentual <= 5:
        linhas.append(f"🟠 **Situação PREOCUPANTE**: Desfalque de {percentual}% está acima do ideal. Investigação recomendada.")
    elif percentual <= 10:
        linhas.append(f"🔴 **Situação CRÍTICA**: Desfalque de {percentual}% indica perda significativa. Ação imediata necessária.")
    else:
        linhas.append(f"⚠️ **ALERTA MÁXIMO**: Desfalque de {percentual}% é extremamente alto! Possível falha sistêmica ou desvio.")

    linhas.append(f"\n**Resumo Quantitativo:**")
    linhas.append(f"- Total comprado: **{totais['total_comprado']} peças**")
    linhas.append(f"- Total contabilizado: **{totais['total_contabilizado']} peças**")
    linhas.append(f"- Desfalque: **{totais['total_desfalque']} peças ({percentual}%)**")

    # Itens Críticos
    linhas.append("\n## 2. ITENS CRÍTICOS\n")
    itens_com_desfalque = [i for i in itens if i["desfalque"] > 0]
    if itens_com_desfalque:
        for i, item in enumerate(itens_com_desfalque[:5], 1):
            status_icon = "🔴" if item["percentual_desfalque"] > 10 else "🟠" if item["percentual_desfalque"] > 5 else "🟡"
            linhas.append(f"{status_icon} **{i}. {item['item_nome']}**: {item['desfalque']} peças faltando ({item['percentual_desfalque']}%)")
    else:
        linhas.append("✅ Nenhum item com desfalque detectado.")

    # Causas Prováveis
    linhas.append("\n## 3. CAUSAS PROVÁVEIS\n")
    if percentual > 0:
        if totais["total_na_lavanderia"] > 0:
            linhas.append("- 🧺 **Lavanderia**: Itens enviados podem não ter retornado ou foram contabilizados incorretamente")
        linhas.append("- 📋 **Falha de registro**: Movimentações sem lançamento no sistema")
        linhas.append("- 🏨 **Quartos não registrados**: Itens em uso sem registro no sistema")
        if percentual > 5:
            linhas.append("- 🔍 **Possível desvio**: Percentual alto sugere investigação de furto ou desvio")
        linhas.append("- 📦 **Perdas operacionais**: Danos, descartes não registrados")

    # Recomendações
    linhas.append("\n## 4. RECOMENDAÇÕES\n")
    linhas.append("1. **Inventário físico imediato** de todos os itens em cada quarto")
    linhas.append("2. **Reconciliação com lavanderia**: Verificar todos os registros de envio/retorno")
    linhas.append("3. **Revisão de processos**: Implementar checklist de controle diário")
    linhas.append("4. **Rastreabilidade**: Marcar fisicamente os itens com código/tag")
    linhas.append("5. **Treinamento de equipe**: Reforçar importância do registro correto")

    # Plano de Ação
    linhas.append("\n## 5. PLANO DE AÇÃO IMEDIATO\n")
    linhas.append("**Próximas 24h:**")
    linhas.append("- [ ] Realizar contagem física em todos os quartos")
    linhas.append("- [ ] Verificar itens pendentes na lavanderia")
    linhas.append("\n**Próximos 7 dias:**")
    linhas.append("- [ ] Implementar planilha de controle diário por andar")
    linhas.append("- [ ] Reunião com equipe de governança")
    linhas.append("- [ ] Definir responsável pelo controle de enxoval")
    linhas.append("\n**Próximos 30 dias:**")
    linhas.append("- [ ] Estabelecer ciclo de inventário quinzenal")
    linhas.append("- [ ] Criar indicadores de desempenho (KPIs) para controle de enxoval")

    linhas.append("\n---")
    linhas.append("\n*Análise gerada pelo CodexiaAuditor — Sistema de Auditoria de Enxoval Hoteleiro*")

    return "\n".join(linhas)
