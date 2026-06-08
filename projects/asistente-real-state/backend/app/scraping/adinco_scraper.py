"""
adinco_scraper.py — RPA worker for Adinco CRM.
Uses Playwright headless to simulate login, extract property/contact listings,
normalize data to the internal schema, and deduplicate against the DB.

Circuit breaker: pauses automatically after 3 consecutive failures.
"""
import asyncio
import hashlib
import re
import structlog
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PWTimeout

from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()

# ─── Adinco config (stored in DB via scraping_sources table) ─────────────────
DEFAULT_ADINCO_CONFIG = {
    "login_url": "",          # set by admin in scraping_sources.config
    "username": "",           # from secrets / env — NEVER hardcoded
    "password": "",
    "properties_url": "",
    "contacts_url": "",
    "selectors": {
        "username_input": "#usuario",
        "password_input": "#password",
        "login_button": "button[type=submit]",
        "property_rows": "table.listado tbody tr",
        "contact_rows": "table.contactos tbody tr",
    },
}


# ─── Circuit Breaker ──────────────────────────────────────────────────────────
class CircuitBreaker:
    """
    Tracks consecutive failures per source.
    Opens after threshold failures → blocks execution until manual reset.
    """
    def __init__(self, threshold: int = 3):
        self._failures: dict[str, int] = {}
        self._open: dict[str, bool] = {}
        self.threshold = threshold

    def is_open(self, source_id: str) -> bool:
        return self._open.get(source_id, False)

    def record_failure(self, source_id: str):
        self._failures[source_id] = self._failures.get(source_id, 0) + 1
        if self._failures[source_id] >= self.threshold:
            self._open[source_id] = True
            log.warning("circuit_breaker.open", source=source_id, failures=self._failures[source_id])

    def record_success(self, source_id: str):
        self._failures[source_id] = 0
        self._open[source_id] = False

    def reset(self, source_id: str):
        self._failures[source_id] = 0
        self._open[source_id] = False
        log.info("circuit_breaker.reset", source=source_id)


circuit_breaker = CircuitBreaker(threshold=3)


# ─── Parser helpers ───────────────────────────────────────────────────────────
def clean_price(raw: str) -> float | None:
    """Extract numeric price from strings like 'USD 125.000' or '$85,000'."""
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", raw)
    return float(digits) if digits else None


def normalize_operation_type(raw: str) -> str:
    raw = raw.lower()
    if "alq" in raw and "temp" in raw:
        return "alquiler_temporario"
    if "alq" in raw:
        return "alquiler"
    return "venta"


def normalize_property_type(raw: str) -> str:
    raw = raw.lower()
    mapping = {
        "depto": "departamento", "departamento": "departamento",
        "casa": "casa", "ph": "ph",
        "local": "local", "oficina": "oficina",
        "terreno": "terreno", "lote": "terreno",
        "cochera": "cochera", "galpón": "galpon", "galpon": "galpon",
    }
    for key, val in mapping.items():
        if key in raw:
            return val
    return "otro"


def make_dedup_hash(address: str, price: float | None, sqm_total: float | None) -> str:
    raw = f"{address.lower().strip()}|{price or ''}|{sqm_total or ''}"
    return hashlib.md5(raw.encode()).hexdigest()


def parse_property_row(row_data: dict[str, str]) -> dict[str, Any]:
    """
    Normalize a raw Adinco property row dict → internal property schema.
    row_data keys depend on the Adinco table column structure.
    """
    price = clean_price(row_data.get("precio", ""))
    sqm = clean_price(row_data.get("superficie", ""))
    sqm_cov = clean_price(row_data.get("sup_cubierta", ""))

    address = row_data.get("direccion", "").strip()
    neighborhood = row_data.get("barrio", "").strip()

    return {
        "external_id": row_data.get("id_adinco", ""),
        "source": "adinco",
        "address": address or "Sin dirección",
        "neighborhood": neighborhood or None,
        "city": row_data.get("ciudad", "Buenos Aires").strip(),
        "province": row_data.get("provincia", "CABA").strip(),
        "property_type": normalize_property_type(row_data.get("tipo", "")),
        "operation_type": normalize_operation_type(row_data.get("operacion", "")),
        "price": price,
        "currency": "USD" if "$u" not in row_data.get("precio", "").lower() else "ARS",
        "sqm_total": sqm,
        "sqm_covered": sqm_cov,
        "rooms": int(row_data["ambientes"]) if row_data.get("ambientes", "").isdigit() else None,
        "bedrooms": int(row_data["dormitorios"]) if row_data.get("dormitorios", "").isdigit() else None,
        "bathrooms": int(row_data["banos"]) if row_data.get("banos", "").isdigit() else None,
        "title": row_data.get("titulo", ""),
        "description": row_data.get("descripcion", ""),
        "dedup_hash": make_dedup_hash(address, price, sqm),
    }


def parse_contact_row(row_data: dict[str, str]) -> dict[str, Any]:
    """Normalize a raw Adinco contact row → internal client schema."""
    return {
        "full_name": row_data.get("nombre", "").strip() or "Sin nombre",
        "email": row_data.get("email", "").strip() or None,
        "phone": row_data.get("telefono", "").strip() or None,
        "source": "adinco",
        "notes": row_data.get("observaciones", ""),
    }


# ─── Playwright session ───────────────────────────────────────────────────────
async def _login(page: Page, config: dict) -> bool:
    """Simulate login to Adinco. Returns True if successful."""
    try:
        await page.goto(config["login_url"], wait_until="networkidle", timeout=30000)
        sel = config.get("selectors", DEFAULT_ADINCO_CONFIG["selectors"])

        await page.fill(sel["username_input"], config["username"])
        await page.fill(sel["password_input"], config["password"])
        await page.click(sel["login_button"])
        await page.wait_for_load_state("networkidle", timeout=15000)

        title = await page.title()
        if "login" in title.lower() or "error" in title.lower():
            log.error("adinco.login_failed", title=title)
            return False

        log.info("adinco.login_ok")
        return True
    except PWTimeout:
        log.error("adinco.login_timeout")
        return False


async def _extract_table_rows(page: Page, url: str, row_selector: str) -> list[dict[str, str]]:
    """
    Navigate to a listing page and extract all table rows as dicts.
    Handles pagination by looking for a 'next page' button.
    """
    rows = []
    await page.goto(url, wait_until="networkidle", timeout=30000)

    while True:
        headers = await page.eval_on_selector_all(
            "table thead th",
            "els => els.map(e => e.innerText.trim().toLowerCase().replace(/ /g,'_'))"
        )
        if not headers:
            break

        raw_rows = await page.eval_on_selector_all(
            row_selector,
            """rows => rows.map(row =>
                Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim())
            )"""
        )

        for raw in raw_rows:
            row_dict = dict(zip(headers, raw))
            rows.append(row_dict)

        next_btn = await page.query_selector("a.paginacion-siguiente, a[aria-label='Next'], .next-page")
        if not next_btn:
            break
        is_disabled = await next_btn.get_attribute("class") or ""
        if "disabled" in is_disabled:
            break
        await next_btn.click()
        await page.wait_for_load_state("networkidle", timeout=15000)

    return rows


# ─── DB operations ────────────────────────────────────────────────────────────
async def _upsert_properties(raw_rows: list[dict], db) -> tuple[int, int]:
    """Insert new properties, skip duplicates. Returns (inserted, skipped)."""
    from sqlalchemy import select
    from app.models.property import Property

    inserted, skipped = 0, 0
    for row in raw_rows:
        try:
            parsed = parse_property_row(row)
            if not parsed["address"] or parsed["address"] == "Sin dirección":
                continue

            existing = await db.execute(
                select(Property).where(Property.dedup_hash == parsed.pop("dedup_hash"))
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            prop = Property(**parsed)
            db.add(prop)
            inserted += 1
        except Exception as e:
            log.warning("adinco.parse_error", error=str(e), row=str(row)[:100])

    await db.commit()
    return inserted, skipped


async def _upsert_contacts(raw_rows: list[dict], db) -> tuple[int, int]:
    """Insert new contacts from Adinco, skip if phone/email already exists."""
    from sqlalchemy import select, or_
    from app.models.client import Client

    inserted, skipped = 0, 0
    for row in raw_rows:
        try:
            parsed = parse_contact_row(row)
            email = parsed.get("email")
            phone = parsed.get("phone")

            if email or phone:
                filters = []
                if email:
                    filters.append(Client.email == email)
                if phone:
                    filters.append(Client.phone == phone)
                existing = await db.execute(select(Client).where(or_(*filters)))
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

            client = Client(**parsed)
            db.add(client)
            inserted += 1
        except Exception as e:
            log.warning("adinco.contact_parse_error", error=str(e))

    await db.commit()
    return inserted, skipped


# ─── Main scraping function ───────────────────────────────────────────────────
async def run_scraper(source_config: dict) -> dict:
    """
    Main entry point for the Adinco RPA worker.
    source_config comes from the scraping_sources table (set by admin).
    """
    source_id = source_config.get("id", "adinco")

    if circuit_breaker.is_open(source_id):
        log.warning("adinco.circuit_open_skip", source=source_id)
        return {"status": "circuit_open", "source": source_id}

    from app.core.database import AsyncSessionLocal

    start = datetime.now(timezone.utc)
    log.info("adinco.scrape_start", source=source_id)

    try:
        async with async_playwright() as pw:
            browser: Browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = await context.new_page()

            logged_in = await _login(page, source_config)
            if not logged_in:
                await browser.close()
                circuit_breaker.record_failure(source_id)
                return {"status": "login_failed", "source": source_id}

            sel = source_config.get("selectors", DEFAULT_ADINCO_CONFIG["selectors"])

            prop_rows = []
            if source_config.get("properties_url"):
                prop_rows = await _extract_table_rows(
                    page, source_config["properties_url"], sel["property_rows"]
                )

            contact_rows = []
            if source_config.get("contacts_url"):
                contact_rows = await _extract_table_rows(
                    page, source_config["contacts_url"], sel["contact_rows"]
                )

            await browser.close()

        async with AsyncSessionLocal() as db:
            prop_ins, prop_skip = await _upsert_properties(prop_rows, db)
            contact_ins, contact_skip = await _upsert_contacts(contact_rows, db)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        circuit_breaker.record_success(source_id)

        result = {
            "status": "ok",
            "source": source_id,
            "properties": {"found": len(prop_rows), "inserted": prop_ins, "skipped": prop_skip},
            "contacts": {"found": len(contact_rows), "inserted": contact_ins, "skipped": contact_skip},
            "elapsed_s": round(elapsed, 2),
        }
        log.info("adinco.scrape_complete", **result)
        return result

    except Exception as e:
        circuit_breaker.record_failure(source_id)
        log.error("adinco.scrape_error", source=source_id, error=str(e))
        return {"status": "error", "source": source_id, "error": str(e)}
