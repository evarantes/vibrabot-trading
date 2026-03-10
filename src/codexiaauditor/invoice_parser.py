from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any

from pypdf import PdfReader


def _to_float(raw: str | None) -> float:
    if not raw:
        return 0.0
    cleaned = raw.replace(".", "").replace(",", ".") if "," in raw and "." in raw else raw.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_access_key(text: str) -> str:
    compact = re.sub(r"\D", "", text or "")
    match = re.search(r"\d{44}", compact)
    return match.group(0) if match else ""


def parse_access_key_metadata(access_key: str) -> dict[str, Any]:
    key = extract_access_key(access_key)
    if len(key) != 44:
        raise ValueError("Chave de acesso inválida. Informe 44 dígitos.")
    aamm = key[2:6]
    return {
        "access_key": key,
        "invoice_number": key[25:34].lstrip("0") or "0",
        "series": key[22:25].lstrip("0") or "0",
        "emission_month": f"20{aamm[:2]}-{aamm[2:]}",
        "cnpj_issuer": key[6:20],
        "items": [],
    }


def _find_text(node: ET.Element, tag: str) -> str:
    found = node.find(f".//{{*}}{tag}")
    return (found.text or "").strip() if found is not None and found.text else ""


def _parse_date(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue
    if "T" in value:
        return value.split("T", maxsplit=1)[0]
    return value


def parse_nfe_xml(xml_bytes: bytes) -> dict[str, Any]:
    root = ET.fromstring(xml_bytes)

    inf_nfe = root.find(".//{*}infNFe")
    key_attr = (inf_nfe.attrib.get("Id", "") if inf_nfe is not None else "").replace("NFe", "")
    access_key = extract_access_key(key_attr or _find_text(root, "chNFe"))
    invoice_number = _find_text(root, "nNF")
    series = _find_text(root, "serie")
    emission_date = _parse_date(_find_text(root, "dhEmi") or _find_text(root, "dEmi"))
    issuer_name = _find_text(root, "xNome")

    items: list[dict[str, Any]] = []
    for det in root.findall(".//{*}det"):
        description = _find_text(det, "xProd")
        qty = _to_float(_find_text(det, "qCom"))
        unit_value = _to_float(_find_text(det, "vUnCom"))
        total_value = _to_float(_find_text(det, "vProd")) or round(qty * unit_value, 2)
        if description:
            items.append(
                {
                    "description": description,
                    "quantity": qty,
                    "unit_value": unit_value,
                    "total_value": total_value,
                }
            )

    return {
        "source_type": "xml",
        "access_key": access_key,
        "invoice_number": invoice_number,
        "series": series,
        "emission_date": emission_date,
        "issuer_name": issuer_name,
        "items": items,
    }


def parse_pdf_invoice(pdf_bytes: bytes) -> dict[str, Any]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]

    access_key = extract_access_key(text)
    nf_match = re.search(r"(?:NF[-\s]*e?|Nota Fiscal)\D{0,20}(\d{3,9})", text, re.IGNORECASE)
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)

    items: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^(?P<description>[A-Z0-9À-Ú\-/\.\s]{4,}?)\s+(?P<qty>\d+[.,]?\d*)\s+(?P<unit>\d+[.,]\d{2})\s+(?P<total>\d+[.,]\d{2})$",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        qty = _to_float(match.group("qty"))
        unit_value = _to_float(match.group("unit"))
        total_value = _to_float(match.group("total"))
        if qty <= 0 or unit_value <= 0:
            continue
        if abs((qty * unit_value) - total_value) > max(5.0, total_value * 0.15):
            continue
        items.append(
            {
                "description": match.group("description").strip(),
                "quantity": qty,
                "unit_value": unit_value,
                "total_value": total_value,
            }
        )

    return {
        "source_type": "pdf",
        "access_key": access_key,
        "invoice_number": nf_match.group(1) if nf_match else "",
        "series": "",
        "emission_date": _parse_date(date_match.group(1) if date_match else ""),
        "issuer_name": "",
        "items": items,
        "raw_text": text,
    }


def parse_invoice_file(filename: str, content: bytes) -> dict[str, Any]:
    lower = (filename or "").lower()
    if lower.endswith(".xml"):
        return parse_nfe_xml(content)
    if lower.endswith(".pdf"):
        return parse_pdf_invoice(content)
    raise ValueError("Formato não suportado. Envie XML ou PDF.")


def parse_emission_date_to_date(value: str, fallback: date | None = None) -> date:
    if not value:
        return fallback or date.today()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value.split("T", maxsplit=1)[0])
    except ValueError:
        return fallback or date.today()
