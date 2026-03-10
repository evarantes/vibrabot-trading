from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any

from .repository import (
    get_balances,
    get_daily_allocated_usage,
    get_laundry_billing_summary,
    get_laundry_movements,
    get_loss_totals,
)


def _pending_laundry_info(movements: list[dict[str, Any]], as_of_date: date) -> tuple[int, int]:
    pending_batches: list[dict[str, Any]] = []

    for move in movements:
        raw_date = move["movement_date"]
        move_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(raw_date)
        qty = int(move["quantity"])
        move_type = move["movement_type"]

        if move_type in {"LAUNDRY_SENT", "LAUNDRY_REWASH_SENT"}:
            pending_batches.append({"date": move_date, "qty": qty})
            continue

        remaining_return = qty
        while remaining_return > 0 and pending_batches:
            first_batch = pending_batches[0]
            abatido = min(first_batch["qty"], remaining_return)
            first_batch["qty"] -= abatido
            remaining_return -= abatido
            if first_batch["qty"] == 0:
                pending_batches.pop(0)

    pending_qty = sum(batch["qty"] for batch in pending_batches)
    if pending_qty <= 0 or not pending_batches:
        return 0, 0

    oldest_date = pending_batches[0]["date"]
    max_days_pending = (as_of_date - oldest_date).days
    return pending_qty, max_days_pending


def _usage_anomaly_score(series: list[dict[str, Any]]) -> tuple[int, str]:
    if len(series) < 8:
        return 0, ""

    values = [int(row["net_use_delta"]) for row in series]
    current_value = values[-1]
    baseline = values[:-1]
    avg = mean(baseline)
    std = pstdev(baseline) or 1.0
    threshold = avg + (2 * std)

    if current_value <= threshold or current_value < 5:
        return 0, ""

    z_score = (current_value - avg) / std
    score = 10 if z_score < 3 else 18
    description = (
        f"Consumo fora do padrão no dia: {current_value} peças líquidas em uso "
        f"(média histórica {avg:.1f}, desvio {std:.1f})."
    )
    return score, description


def generate_audit_report(as_of_date: date, operation_unit: str = "HOTEL") -> dict[str, Any]:
    balances = get_balances(as_of_date, operation_unit=operation_unit)
    loss_last_7 = get_loss_totals(7, as_of_date, operation_unit=operation_unit)
    loss_prev_7 = get_loss_totals(7, as_of_date - timedelta(days=7), operation_unit=operation_unit)
    laundry_summary_30d = get_laundry_billing_summary(days=30, ref_date=as_of_date, operation_unit=operation_unit)

    findings: list[dict[str, Any]] = []
    risk_by_item: dict[int, int] = {}
    global_risk_points = 0

    for row in balances:
        item_id = int(row["id"])
        item_name = row["name"]
        par_level = int(row["par_level"] or 0)

        risk_by_item[item_id] = 0

        stock_theoretical = int(row["stock_theoretical"] or 0)
        laundry_theoretical = int(row["laundry_theoretical"] or 0)
        in_use_theoretical = int(row["in_use_theoretical"] or 0)

        counted_stock = row["counted_stock"]
        counted_laundry = row["counted_laundry"]
        counted_in_use = row["counted_in_use"]

        if counted_stock is not None:
            diff_stock = int(counted_stock) - stock_theoretical
            if diff_stock != 0:
                abs_diff = abs(diff_stock)
                severity = "alta" if abs_diff >= max(10, int(par_level * 0.25)) else "media"
                score = 25 if severity == "alta" else 15
                findings.append(
                    {
                        "item": item_name,
                        "severidade": severity,
                        "area": "estoque_fisico",
                        "descricao": (
                            f"Divergência no estoque físico: teórico={stock_theoretical}, "
                            f"contado={counted_stock}, diferença={diff_stock}."
                        ),
                        "acao": "Recontar estoque, validar baixas manuais e conferir perdas registradas.",
                        "risco_pontos": score,
                    }
                )
                risk_by_item[item_id] += score

        if counted_laundry is not None:
            diff_laundry = int(counted_laundry) - laundry_theoretical
            if abs(diff_laundry) >= 5:
                findings.append(
                    {
                        "item": item_name,
                        "severidade": "media",
                        "area": "lavanderia",
                        "descricao": (
                            f"Divergência na posição de lavanderia: teórico={laundry_theoretical}, "
                            f"contado={counted_laundry}, diferença={diff_laundry}."
                        ),
                        "acao": "Conferir romaneios e comprovantes de envio/retorno da lavanderia.",
                        "risco_pontos": 12,
                    }
                )
                risk_by_item[item_id] += 12

        if counted_in_use is not None:
            diff_in_use = int(counted_in_use) - in_use_theoretical
            if abs(diff_in_use) >= 5:
                findings.append(
                    {
                        "item": item_name,
                        "severidade": "media",
                        "area": "uso_operacao",
                        "descricao": (
                            f"Divergência no enxoval em uso: teórico={in_use_theoretical}, "
                            f"contado={counted_in_use}, diferença={diff_in_use}."
                        ),
                        "acao": "Verificar devoluções pendentes dos andares/governança.",
                        "risco_pontos": 10,
                    }
                )
                risk_by_item[item_id] += 10

        laundry_moves = get_laundry_movements(item_id, as_of_date, operation_unit=operation_unit)
        pending_qty, pending_days = _pending_laundry_info(laundry_moves, as_of_date)
        if pending_qty > 0 and pending_days >= 3:
            severity = "alta" if pending_days >= 5 else "media"
            score = 16 if severity == "alta" else 9
            findings.append(
                {
                    "item": item_name,
                    "severidade": severity,
                    "area": "lavanderia",
                    "descricao": (
                        f"{pending_qty} peças pendentes de retorno da lavanderia há até "
                        f"{pending_days} dia(s)."
                    ),
                    "acao": "Cobrar retorno por lote e cruzar com as notas de envio diárias.",
                    "risco_pontos": score,
                }
            )
            risk_by_item[item_id] += score

        usage_series = get_daily_allocated_usage(
            item_id=item_id,
            days=30,
            ref_date=as_of_date,
            operation_unit=operation_unit,
        )
        usage_score, usage_desc = _usage_anomaly_score(usage_series)
        if usage_score > 0:
            findings.append(
                {
                    "item": item_name,
                    "severidade": "media",
                    "area": "consumo",
                    "descricao": usage_desc,
                    "acao": "Auditar consumo por ala e checar ocorrências atípicas no período.",
                    "risco_pontos": usage_score,
                }
            )
            risk_by_item[item_id] += usage_score

        last_loss = loss_last_7.get(item_id, 0)
        prev_loss = loss_prev_7.get(item_id, 0)
        if last_loss >= 3 and last_loss > prev_loss:
            delta = last_loss - prev_loss
            findings.append(
                {
                    "item": item_name,
                    "severidade": "alta" if delta >= 5 else "media",
                    "area": "perdas",
                    "descricao": (
                        f"Perdas em alta: últimos 7 dias={last_loss}, 7 dias anteriores={prev_loss}."
                    ),
                    "acao": "Abrir investigação de causa raiz por setor e turno.",
                    "risco_pontos": 20 if delta >= 5 else 12,
                }
            )
            risk_by_item[item_id] += 20 if delta >= 5 else 12

    billed_sent = laundry_summary_30d["billed_sent"]
    rewash_sent = laundry_summary_30d["rewash_sent"]
    if billed_sent >= 20 and rewash_sent > 0:
        rewash_ratio = rewash_sent / billed_sent
        if rewash_ratio >= 0.1:
            score = 15 if rewash_ratio >= 0.2 else 9
            findings.append(
                {
                    "item": "GERAL",
                    "severidade": "alta" if rewash_ratio >= 0.2 else "media",
                    "area": "qualidade_lavanderia",
                    "descricao": (
                        f"Taxa de relavagem elevada nos últimos 30 dias: "
                        f"{rewash_sent}/{billed_sent} ({rewash_ratio:.1%})."
                    ),
                    "acao": "Negociar qualidade com a lavanderia e auditar lotes com recorrência de relavagem.",
                    "risco_pontos": score,
                }
            )
            global_risk_points += score

    findings.sort(key=lambda row: row["risco_pontos"], reverse=True)
    overall_score = min(100, sum(risk_by_item.values()) + global_risk_points)
    items_with_alert = len([x for x in risk_by_item.values() if x > 0])

    return {
        "as_of_date": as_of_date.isoformat(),
        "operation_unit": operation_unit,
        "overall_risk_score": overall_score,
        "items_with_alert": items_with_alert,
        "laundry_summary_30d": laundry_summary_30d,
        "findings": findings,
        "balances": balances,
    }

