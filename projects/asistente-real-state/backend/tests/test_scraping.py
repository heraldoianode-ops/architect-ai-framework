"""
test_scraping.py — L2 unit tests for Node 3.1: Adinco scraper.
Tests: CircuitBreaker, parsers, dedup hash, normalization.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.scraping.adinco_scraper import (
    CircuitBreaker,
    clean_price,
    normalize_operation_type,
    normalize_property_type,
    make_dedup_hash,
    parse_property_row,
    parse_contact_row,
    _upsert_properties,
    _upsert_contacts,
)


# ─── CircuitBreaker ───────────────────────────────────────────────────────────
class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(threshold=3)
        assert cb.is_open("src1") is False

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("src1")
        cb.record_failure("src1")
        assert cb.is_open("src1") is False
        cb.record_failure("src1")
        assert cb.is_open("src1") is True

    def test_success_resets_failures(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("src1")
        cb.record_failure("src1")
        cb.record_success("src1")
        cb.record_failure("src1")  # only 1 failure after reset
        assert cb.is_open("src1") is False

    def test_reset_closes_open_circuit(self):
        cb = CircuitBreaker(threshold=1)
        cb.record_failure("src1")
        assert cb.is_open("src1") is True
        cb.reset("src1")
        assert cb.is_open("src1") is False

    def test_isolates_different_sources(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure("srcA")
        cb.record_failure("srcA")
        assert cb.is_open("srcA") is True
        assert cb.is_open("srcB") is False


# ─── Price parser ─────────────────────────────────────────────────────────────
class TestCleanPrice:
    def test_usd_dot_format(self):
        assert clean_price("USD 125.000") == 125000.0

    def test_dollar_comma_format(self):
        assert clean_price("$85,000") == 85000.0

    def test_plain_number(self):
        assert clean_price("500000") == 500000.0

    def test_empty_string(self):
        assert clean_price("") is None

    def test_none(self):
        assert clean_price(None) is None

    def test_no_digits(self):
        assert clean_price("sin precio") is None


# ─── Operation type normalizer ────────────────────────────────────────────────
class TestNormalizeOperationType:
    def test_venta(self):
        assert normalize_operation_type("Venta") == "venta"

    def test_alquiler(self):
        assert normalize_operation_type("Alquiler") == "alquiler"

    def test_alquiler_temporario(self):
        assert normalize_operation_type("Alq. Temp.") == "alquiler_temporario"
        assert normalize_operation_type("alquiler temporal") == "alquiler_temporario"

    def test_unknown_defaults_to_venta(self):
        assert normalize_operation_type("desconocido") == "venta"


# ─── Property type normalizer ─────────────────────────────────────────────────
class TestNormalizePropertyType:
    @pytest.mark.parametrize("raw,expected", [
        ("Departamento 3 amb", "departamento"),
        ("DEPTO", "departamento"),
        ("Casa en PH", "ph"),
        ("local comercial", "local"),
        ("LOTE 300m2", "terreno"),
        ("Cochera cubierta", "cochera"),
        ("Galpon industrial", "galpon"),
        ("galpón", "galpon"),
        ("Objeto raro", "otro"),
    ])
    def test_mapping(self, raw, expected):
        assert normalize_property_type(raw) == expected


# ─── Dedup hash ───────────────────────────────────────────────────────────────
class TestMakeDedupHash:
    def test_same_inputs_same_hash(self):
        h1 = make_dedup_hash("Av. Corrientes 1234", 85000.0, 65.0)
        h2 = make_dedup_hash("Av. Corrientes 1234", 85000.0, 65.0)
        assert h1 == h2

    def test_different_price_different_hash(self):
        h1 = make_dedup_hash("Av. Corrientes 1234", 85000.0, 65.0)
        h2 = make_dedup_hash("Av. Corrientes 1234", 90000.0, 65.0)
        assert h1 != h2

    def test_case_insensitive_address(self):
        h1 = make_dedup_hash("av. corrientes 1234", 85000.0, 65.0)
        h2 = make_dedup_hash("AV. CORRIENTES 1234", 85000.0, 65.0)
        assert h1 == h2

    def test_none_values_handled(self):
        h = make_dedup_hash("Calle sin precio", None, None)
        assert isinstance(h, str) and len(h) == 32


# ─── Row parsers ──────────────────────────────────────────────────────────────
class TestParsePropertyRow:
    def _sample_row(self):
        return {
            "id_adinco": "A-001",
            "precio": "USD 120.000",
            "superficie": "80",
            "sup_cubierta": "65",
            "direccion": "Av. Santa Fe 2000",
            "barrio": "Palermo",
            "ciudad": "Buenos Aires",
            "provincia": "CABA",
            "tipo": "departamento",
            "operacion": "Venta",
            "ambientes": "3",
            "dormitorios": "2",
            "banos": "1",
            "titulo": "Dpto en Palermo",
            "descripcion": "Amplio departamento",
        }

    def test_full_row(self):
        parsed = parse_property_row(self._sample_row())
        assert parsed["external_id"] == "A-001"
        assert parsed["price"] == 120000.0
        assert parsed["rooms"] == 3
        assert parsed["bedrooms"] == 2
        assert parsed["property_type"] == "departamento"
        assert parsed["operation_type"] == "venta"
        assert parsed["source"] == "adinco"

    def test_missing_address_fallback(self):
        row = self._sample_row()
        row["direccion"] = ""
        parsed = parse_property_row(row)
        assert parsed["address"] == "Sin dirección"

    def test_non_digit_rooms_is_none(self):
        row = self._sample_row()
        row["ambientes"] = "N/A"
        parsed = parse_property_row(row)
        assert parsed["rooms"] is None

    def test_dedup_hash_present(self):
        parsed = parse_property_row(self._sample_row())
        assert "dedup_hash" in parsed
        assert len(parsed["dedup_hash"]) == 32


class TestParseContactRow:
    def test_full_row(self):
        row = {"nombre": "Juan Perez", "email": "juan@mail.com", "telefono": "1155554444", "observaciones": "VIP"}
        parsed = parse_contact_row(row)
        assert parsed["full_name"] == "Juan Perez"
        assert parsed["email"] == "juan@mail.com"
        assert parsed["source"] == "adinco"

    def test_empty_name_fallback(self):
        row = {"nombre": "", "email": "x@y.com", "telefono": "", "observaciones": ""}
        parsed = parse_contact_row(row)
        assert parsed["full_name"] == "Sin nombre"

    def test_empty_phone_is_none(self):
        row = {"nombre": "Ana", "email": "", "telefono": "  ", "observaciones": ""}
        parsed = parse_contact_row(row)
        assert parsed["phone"] is None


# ─── Dedup — _upsert_properties ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_upsert_properties_skips_duplicate():
    """If dedup_hash already exists, row is skipped."""
    from app.models.property import Property

    mock_prop = MagicMock(spec=Property)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_prop  # already exists

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    row = {
        "id_adinco": "X1", "precio": "100000", "superficie": "60", "sup_cubierta": "50",
        "direccion": "Calle Test 123", "barrio": "Centro", "ciudad": "BsAs", "provincia": "CABA",
        "tipo": "casa", "operacion": "venta", "ambientes": "2", "dormitorios": "1", "banos": "1",
        "titulo": "Test", "descripcion": "",
    }

    inserted, skipped = await _upsert_properties([row], db)
    assert inserted == 0
    assert skipped == 1


@pytest.mark.asyncio
async def test_upsert_contacts_skips_duplicate():
    """If email/phone already exists, contact is skipped."""
    from app.models.client import Client

    mock_client = MagicMock(spec=Client)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_client

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    row = {"nombre": "Maria", "email": "maria@mail.com", "telefono": "123", "observaciones": ""}

    inserted, skipped = await _upsert_contacts([row], db)
    assert inserted == 0
    assert skipped == 1
