"""
test_drive_scraper.py — L2 unit tests for Node 3.2: Drive + Excel ingestion.
All Google API calls are mocked; only logic and parsing are tested.
"""
import io
import pytest
import openpyxl
from unittest.mock import MagicMock, patch, AsyncMock

from app.scraping.excel_parser import (
    _slug,
    normalize_headers,
    parse_excel_property_row,
    parse_excel_contact_row,
    _PROPERTY_COLUMN_MAP,
    _CONTACT_COLUMN_MAP,
)
from app.scraping.drive_scraper import (
    _detect_sheet_role,
    parse_workbook,
    run_drive_sync,
)


# ─── _slug ────────────────────────────────────────────────────────────────────
class TestSlug:
    def test_basic(self):
        assert _slug("Dirección") == "direccion"

    def test_spaces_to_underscore(self):
        assert _slug("Tipo Propiedad") == "tipo_propiedad"

    def test_already_clean(self):
        assert _slug("precio") == "precio"

    def test_mixed_case(self):
        assert _slug("Full_Name") == "full_name"


# ─── normalize_headers ────────────────────────────────────────────────────────
class TestNormalizeHeaders:
    def test_maps_known_headers(self):
        raw = ["Dirección", "Precio", "Superficie"]
        out = normalize_headers(raw, _PROPERTY_COLUMN_MAP)
        assert out == ["direccion", "precio", "superficie"]

    def test_unknown_header_kept(self):
        raw = ["columna_rara"]
        out = normalize_headers(raw, _PROPERTY_COLUMN_MAP)
        assert out == ["columna_rara"]

    def test_contact_map(self):
        raw = ["Full_Name", "Email", "Phone"]
        out = normalize_headers(raw, _CONTACT_COLUMN_MAP)
        assert out == ["nombre", "email", "telefono"]


# ─── parse_excel_property_row ─────────────────────────────────────────────────
class TestParseExcelPropertyRow:
    def _row(self):
        return {
            "id_ext": "DRV-001",
            "precio": "150000",
            "superficie": "90",
            "sup_cubierta": "75",
            "direccion": "Calle Falsa 123",
            "barrio": "Belgrano",
            "ciudad": "Buenos Aires",
            "provincia": "CABA",
            "tipo": "departamento",
            "operacion": "venta",
            "ambientes": "3.0",
            "dormitorios": "2.0",
            "banos": "1.0",
            "titulo": "Dpto Belgrano",
            "descripcion": "Luminoso",
        }

    def test_full_row(self):
        parsed = parse_excel_property_row(self._row(), "drive_test")
        assert parsed["external_id"] == "DRV-001"
        assert parsed["price"] == 150000.0
        assert parsed["rooms"] == 3
        assert parsed["bedrooms"] == 2
        assert parsed["source"] == "drive_test"
        assert parsed["property_type"] == "departamento"

    def test_float_rooms_parsed(self):
        row = self._row()
        row["ambientes"] = "4.0"
        parsed = parse_excel_property_row(row)
        assert parsed["rooms"] == 4

    def test_empty_address_fallback(self):
        row = self._row()
        row["direccion"] = ""
        parsed = parse_excel_property_row(row)
        assert parsed["address"] == "Sin dirección"

    def test_ars_currency_detection(self):
        row = self._row()
        row["moneda"] = "ARS"
        parsed = parse_excel_property_row(row)
        assert parsed["currency"] == "ARS"

    def test_dedup_hash_generated(self):
        parsed = parse_excel_property_row(self._row())
        assert len(parsed["dedup_hash"]) == 32


# ─── parse_excel_contact_row ──────────────────────────────────────────────────
class TestParseExcelContactRow:
    def test_full(self):
        row = {"nombre": "Carlos", "email": "c@x.com", "telefono": "1122334455", "observaciones": ""}
        parsed = parse_excel_contact_row(row)
        assert parsed["full_name"] == "Carlos"
        assert parsed["email"] == "c@x.com"
        assert parsed["source"] == "excel"

    def test_empty_name_fallback(self):
        row = {"nombre": "", "email": "", "telefono": "", "observaciones": ""}
        parsed = parse_excel_contact_row(row)
        assert parsed["full_name"] == "Sin nombre"

    def test_none_phone(self):
        row = {"nombre": "X", "email": "", "telefono": "", "observaciones": ""}
        parsed = parse_excel_contact_row(row)
        assert parsed["phone"] is None


# ─── _detect_sheet_role ───────────────────────────────────────────────────────
class TestDetectSheetRole:
    @pytest.mark.parametrize("title,expected", [
        ("Propiedades", "properties"),
        ("Listado_inmuebles", "properties"),
        ("Ficha técnica", "properties"),
        ("Contactos", "contacts"),
        ("Clientes leads", "contacts"),
        ("Buyer list", "contacts"),
        ("Resumen", "unknown"),
    ])
    def test_roles(self, title, expected):
        assert _detect_sheet_role(title) == expected


# ─── parse_workbook ───────────────────────────────────────────────────────────
def _make_workbook_bytes(sheets: dict[str, list[list]]) -> bytes:
    """Helper: create an xlsx in memory from {sheet_name: [[row], [row], ...]}"""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet
    for title, rows in sheets.items():
        ws = wb.create_sheet(title=title)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestParseWorkbook:
    def test_single_properties_sheet(self):
        xlsx = _make_workbook_bytes({
            "Propiedades": [
                ["Dirección", "Precio", "Tipo", "Operacion", "Superficie"],
                ["Av. Santa Fe 100", "120000", "departamento", "venta", "65"],
                ["Corrientes 200", "200000", "casa", "venta", "120"],
            ]
        })
        result = parse_workbook(xlsx, "test")
        assert len(result["properties"]) == 2
        assert result["properties"][0]["address"] == "Av. Santa Fe 100"
        assert result["contacts"] == []

    def test_contacts_sheet_detected(self):
        xlsx = _make_workbook_bytes({
            "Contactos": [
                ["Nombre", "Email", "Telefono"],
                ["Ana Lopez", "ana@mail.com", "1155"],
            ]
        })
        result = parse_workbook(xlsx)
        assert len(result["contacts"]) == 1
        assert result["contacts"][0]["full_name"] == "Ana Lopez"

    def test_mixed_workbook(self):
        xlsx = _make_workbook_bytes({
            "Propiedades": [
                ["Dirección", "Precio", "Tipo", "Operacion", "Superficie"],
                ["Calle 1", "50000", "casa", "alquiler", "80"],
            ],
            "Clientes": [
                ["Nombre", "Email", "Telefono"],
                ["Jorge", "j@x.com", "999"],
            ],
        })
        result = parse_workbook(xlsx)
        assert len(result["properties"]) == 1
        assert len(result["contacts"]) == 1

    def test_blank_rows_skipped(self):
        xlsx = _make_workbook_bytes({
            "Propiedades": [
                ["Dirección", "Precio", "Tipo", "Operacion", "Superficie"],
                ["Av. Test 1", "80000", "casa", "venta", "100"],
                [None, None, None, None, None],  # blank row
                ["Av. Test 2", "90000", "local", "venta", "50"],
            ]
        })
        result = parse_workbook(xlsx)
        assert len(result["properties"]) == 2

    def test_single_sheet_workbook_defaults_to_properties(self):
        xlsx = _make_workbook_bytes({
            "Hoja1": [
                ["Dirección", "Precio", "Tipo", "Operacion", "Superficie"],
                ["Libertad 500", "60000", "oficina", "alquiler", "40"],
            ]
        })
        result = parse_workbook(xlsx)
        assert len(result["properties"]) == 1


# ─── run_drive_sync — config validation ───────────────────────────────────────
@pytest.mark.asyncio
async def test_run_drive_sync_missing_credentials():
    config = {"id": "src1", "folder_ids": ["folder123"]}  # no credentials
    result = await run_drive_sync(config)
    assert result["status"] == "config_error"


@pytest.mark.asyncio
async def test_run_drive_sync_missing_folders():
    config = {"id": "src1", "credentials": {"type": "service_account"}}  # no folders
    result = await run_drive_sync(config)
    assert result["status"] == "config_error"


@pytest.mark.asyncio
async def test_run_drive_sync_circuit_open():
    from app.scraping.adinco_scraper import circuit_breaker
    circuit_breaker._open["src_drive"] = True
    config = {"id": "src_drive", "credentials": {}, "folder_ids": ["x"]}
    result = await run_drive_sync(config)
    assert result["status"] == "circuit_open"
    circuit_breaker._open["src_drive"] = False  # cleanup
