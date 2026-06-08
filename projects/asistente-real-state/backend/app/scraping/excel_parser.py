"""
excel_parser.py — Shared normalizer for Excel/Sheets rows → internal schema.
Used by drive_scraper. Column names are matched case-insensitively and
normalized to remove accents/spaces, so minor header variations are tolerated.
"""
import re
import unicodedata
from typing import Any

from app.scraping.adinco_scraper import (
    clean_price,
    normalize_operation_type,
    normalize_property_type,
    make_dedup_hash,
)


def _slug(text: str) -> str:
    """Normalize header: lowercase, strip accents, collapse non-alphanum to '_'."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


# Maps normalized header slugs → canonical field names used by parsers
_PROPERTY_COLUMN_MAP: dict[str, str] = {
    "id": "id_ext",
    "id_externo": "id_ext",
    "codigo": "id_ext",
    "precio": "precio",
    "price": "precio",
    "superficie": "superficie",
    "sup_total": "superficie",
    "superficie_total": "superficie",
    "sup_cubierta": "sup_cubierta",
    "superficie_cubierta": "sup_cubierta",
    "direccion": "direccion",
    "address": "direccion",
    "barrio": "barrio",
    "neighborhood": "barrio",
    "ciudad": "ciudad",
    "city": "ciudad",
    "provincia": "provincia",
    "province": "provincia",
    "tipo": "tipo",
    "type": "tipo",
    "tipo_propiedad": "tipo",
    "operacion": "operacion",
    "operation": "operacion",
    "tipo_operacion": "operacion",
    "ambientes": "ambientes",
    "rooms": "ambientes",
    "dormitorios": "dormitorios",
    "bedrooms": "dormitorios",
    "banos": "banos",
    "bathrooms": "banos",
    "titulo": "titulo",
    "title": "titulo",
    "descripcion": "descripcion",
    "description": "descripcion",
    "moneda": "moneda",
    "currency": "moneda",
}

_CONTACT_COLUMN_MAP: dict[str, str] = {
    "nombre": "nombre",
    "name": "nombre",
    "nombre_completo": "nombre",
    "full_name": "nombre",
    "email": "email",
    "correo": "email",
    "telefono": "telefono",
    "phone": "telefono",
    "tel": "telefono",
    "celular": "telefono",
    "observaciones": "observaciones",
    "notas": "observaciones",
    "notes": "observaciones",
}


def normalize_headers(raw_headers: list[str], column_map: dict[str, str]) -> list[str]:
    """Map raw Excel headers to canonical field names. Unknown headers kept as-is."""
    result = []
    for h in raw_headers:
        slug = _slug(str(h))
        result.append(column_map.get(slug, slug))
    return result


def parse_excel_property_row(row: dict[str, Any], source_name: str = "excel") -> dict[str, Any]:
    """Normalize a row dict (canonical keys) → internal property schema."""
    price = clean_price(str(row.get("precio") or ""))
    sqm = clean_price(str(row.get("superficie") or ""))
    sqm_cov = clean_price(str(row.get("sup_cubierta") or ""))
    address = str(row.get("direccion") or "").strip()

    raw_ambientes = str(row.get("ambientes") or "")
    raw_dorm = str(row.get("dormitorios") or "")
    raw_banos = str(row.get("banos") or "")

    # Strip decimal part if cell came as float (e.g. 3.0 → "3")
    def _int_or_none(val: str) -> int | None:
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    currency_raw = str(row.get("moneda") or row.get("precio") or "").lower()
    currency = "ARS" if any(x in currency_raw for x in ("ars", "peso", "$a")) else "USD"

    return {
        "external_id": str(row.get("id_ext") or ""),
        "source": source_name,
        "address": address or "Sin dirección",
        "neighborhood": str(row.get("barrio") or "").strip() or None,
        "city": str(row.get("ciudad") or "Buenos Aires").strip(),
        "province": str(row.get("provincia") or "CABA").strip(),
        "property_type": normalize_property_type(str(row.get("tipo") or "")),
        "operation_type": normalize_operation_type(str(row.get("operacion") or "")),
        "price": price,
        "currency": currency,
        "sqm_total": sqm,
        "sqm_covered": sqm_cov,
        "rooms": _int_or_none(raw_ambientes),
        "bedrooms": _int_or_none(raw_dorm),
        "bathrooms": _int_or_none(raw_banos),
        "title": str(row.get("titulo") or ""),
        "description": str(row.get("descripcion") or ""),
        "dedup_hash": make_dedup_hash(address, price, sqm),
    }


def parse_excel_contact_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a row dict (canonical keys) → internal client schema."""
    return {
        "full_name": str(row.get("nombre") or "").strip() or "Sin nombre",
        "email": str(row.get("email") or "").strip() or None,
        "phone": str(row.get("telefono") or "").strip() or None,
        "source": "excel",
        "notes": str(row.get("observaciones") or ""),
    }
