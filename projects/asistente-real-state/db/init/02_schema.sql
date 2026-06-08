-- ============================================================
-- ASISTENTE REAL STATE — Base Schema
-- ============================================================

-- ─── ENUMS ───────────────────────────────────────────────────
CREATE TYPE user_role AS ENUM (
    'administrador',
    'agente_real_state',
    'broker',
    'cliente_comprador',
    'cliente_vendedor'
);

CREATE TYPE property_type AS ENUM (
    'departamento', 'casa', 'ph', 'local', 'oficina',
    'terreno', 'cochera', 'galpon', 'otro'
);

CREATE TYPE property_status AS ENUM (
    'disponible', 'reservada', 'vendida', 'alquilada',
    'en_negociacion', 'pausada', 'eliminada'
);

CREATE TYPE operation_type AS ENUM ('venta', 'alquiler', 'alquiler_temporario');

CREATE TYPE lead_stage AS ENUM (
    'nuevo', 'contactado', 'interesado', 'visita_agendada',
    'oferta_realizada', 'negociacion', 'cerrado_ganado', 'cerrado_perdido'
);

CREATE TYPE event_type AS ENUM (
    'visita_comprador', 'captacion_vendedor',
    'reunion_agente', 'llamada', 'otro'
);

CREATE TYPE event_status AS ENUM (
    'pendiente', 'confirmado', 'realizado', 'cancelado', 'reprogramado'
);

CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');
CREATE TYPE message_channel AS ENUM ('whatsapp', 'email', 'sistema');

-- ─── USERS ───────────────────────────────────────────────────
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       TEXT UNIQUE NOT NULL,
    full_name   TEXT NOT NULL,
    role        user_role NOT NULL DEFAULT 'cliente_comprador',
    phone       TEXT,
    avatar_url  TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- ─── PROPERTIES ──────────────────────────────────────────────
CREATE TABLE properties (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    -- identification
    external_id     TEXT,                          -- ID en Adinco u otro CRM
    source          TEXT DEFAULT 'manual',         -- 'manual' | 'adinco' | 'scraping'
    -- location
    address         TEXT NOT NULL,
    neighborhood    TEXT,
    city            TEXT NOT NULL DEFAULT 'Buenos Aires',
    province        TEXT NOT NULL DEFAULT 'CABA',
    country         TEXT NOT NULL DEFAULT 'Argentina',
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    -- specs
    property_type   property_type NOT NULL,
    operation_type  operation_type NOT NULL,
    price           NUMERIC(14, 2),
    currency        CHAR(3) DEFAULT 'USD',
    expenses        NUMERIC(10, 2),
    sqm_total       NUMERIC(8, 2),
    sqm_covered     NUMERIC(8, 2),
    rooms           SMALLINT,
    bedrooms        SMALLINT,
    bathrooms       SMALLINT,
    parking         SMALLINT DEFAULT 0,
    floor           SMALLINT,
    amenities       TEXT[],
    -- status
    status          property_status NOT NULL DEFAULT 'disponible',
    listed_at       DATE DEFAULT CURRENT_DATE,
    -- content
    title           TEXT,
    description     TEXT,
    photos          TEXT[],                        -- Supabase Storage URLs
    -- vector for semantic matching
    embedding       vector(768),                   -- nomic-embed-text dimension
    -- dedup hash: address + price + sqm_total
    dedup_hash      TEXT GENERATED ALWAYS AS (
                        md5(lower(address) || '|' || COALESCE(price::text,'') || '|' || COALESCE(sqm_total::text,''))
                    ) STORED,
    -- audit
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_properties_agent ON properties(agent_id);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_type_op ON properties(property_type, operation_type);
CREATE INDEX idx_properties_neighborhood ON properties(neighborhood);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_dedup ON properties(dedup_hash);
CREATE INDEX idx_properties_embedding ON properties USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_properties_fts ON properties USING gin(to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || address));

-- ─── CLIENTS ─────────────────────────────────────────────────
CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    -- identification
    full_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    whatsapp_id     TEXT UNIQUE,                   -- Meta WA contact ID
    -- profile
    role            user_role NOT NULL DEFAULT 'cliente_comprador',
    source          TEXT,                          -- 'whatsapp' | 'excel' | 'adinco' | 'manual'
    -- buyer preferences (para matching semántico)
    search_zones    TEXT[],
    search_types    property_type[],
    budget_min      NUMERIC(14,2),
    budget_max      NUMERIC(14,2),
    preferences_text TEXT,                         -- texto libre de preferencias
    preference_embedding vector(768),              -- embedding del perfil comprador
    -- seller info
    property_id     UUID REFERENCES properties(id) ON DELETE SET NULL,
    -- pipeline
    stage           lead_stage NOT NULL DEFAULT 'nuevo',
    score           SMALLINT DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
    closing_prob    NUMERIC(5,2),                  -- % predicho por XGBoost
    -- tags and notes
    tags            TEXT[],
    notes           TEXT,
    -- audit
    last_contact_at TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clients_agent ON clients(agent_id);
CREATE INDEX idx_clients_stage ON clients(stage);
CREATE INDEX idx_clients_whatsapp ON clients(whatsapp_id);
CREATE INDEX idx_clients_preference_embedding ON clients USING ivfflat (preference_embedding vector_cosine_ops) WITH (lists = 50);

-- ─── INTERACTIONS (CRM history) ──────────────────────────────
CREATE TABLE interactions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    agent_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    -- content
    channel     message_channel NOT NULL DEFAULT 'sistema',
    direction   message_direction,
    content     TEXT NOT NULL,
    is_ai       BOOLEAN NOT NULL DEFAULT false,    -- generated by AI agent?
    -- whatsapp specifics
    wa_message_id TEXT,
    -- audit
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interactions_client ON interactions(client_id);
CREATE INDEX idx_interactions_agent ON interactions(agent_id);
CREATE INDEX idx_interactions_created ON interactions(created_at DESC);

-- ─── EVENTS (agenda) ─────────────────────────────────────────
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
    property_id     UUID REFERENCES properties(id) ON DELETE SET NULL,
    -- event
    event_type      event_type NOT NULL,
    status          event_status NOT NULL DEFAULT 'pendiente',
    title           TEXT NOT NULL,
    description     TEXT,
    scheduled_at    TIMESTAMPTZ NOT NULL,
    duration_min    SMALLINT DEFAULT 60,
    location        TEXT,
    -- reminders sent
    reminder_24h_sent BOOLEAN DEFAULT false,
    reminder_1h_sent  BOOLEAN DEFAULT false,
    -- audit
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_agent ON events(agent_id);
CREATE INDEX idx_events_scheduled ON events(scheduled_at);
CREATE INDEX idx_events_status ON events(status);

-- ─── RAG DOCUMENTS (legal, FAQs, objections) ─────────────────
CREATE TABLE rag_documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_type    TEXT NOT NULL,                     -- 'legal' | 'faq' | 'objection'
    source_file TEXT,
    chunk_index SMALLINT NOT NULL DEFAULT 0,
    content     TEXT NOT NULL,
    embedding   vector(768) NOT NULL,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rag_type ON rag_documents(doc_type);
CREATE INDEX idx_rag_embedding ON rag_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─── OBJECTION FEEDBACK (meta-learning) ──────────────────────
CREATE TABLE objection_feedback (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    objection_text      TEXT NOT NULL,
    successful_response TEXT NOT NULL,
    outcome             TEXT,                      -- 'sale_closed' | 'objection_resolved' | etc.
    embedding           vector(768),               -- embedding del par completo
    times_used          INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_objection_embedding ON objection_feedback USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ─── SCRAPING SOURCES (admin configurable) ───────────────────
CREATE TABLE scraping_sources (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    base_url        TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    schedule_hours  SMALLINT NOT NULL DEFAULT 6,   -- run every N hours
    last_run_at     TIMESTAMPTZ,
    last_run_status TEXT,
    failure_count   SMALLINT DEFAULT 0,
    config          JSONB DEFAULT '{}',            -- selectors, login fields, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── AUDIT LOG ───────────────────────────────────────────────
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    entity_type TEXT,
    entity_id   UUID,
    diff        JSONB,
    ip_address  INET,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_actor ON audit_log(actor_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- ─── AUTO-UPDATE updated_at ──────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at        BEFORE UPDATE ON users        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_properties_updated_at   BEFORE UPDATE ON properties   FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_clients_updated_at      BEFORE UPDATE ON clients      FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_events_updated_at       BEFORE UPDATE ON events       FOR EACH ROW EXECUTE FUNCTION update_updated_at();
