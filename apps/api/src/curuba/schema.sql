-- Esquema completo de Curuba. Idempotente: se puede correr varias veces.
--   uv run python -m curuba.db          (aplica este archivo)

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
-- Redundante en Postgres 13+ (gen_random_uuid ya es nativa), pero el spec la
-- pide y no cuesta nada tenerla.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- unaccent() NO es IMMUTABLE, así que no se puede usar directo en una columna
-- generada. Envolverla en esta función sí, indicando el diccionario explícito.
CREATE OR REPLACE FUNCTION curuba_norm(txt text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS
$$ SELECT lower(public.unaccent('public.unaccent', txt)) $$;


-- ── Conversaciones ────────────────────────────────────────────────────────
-- Lo único que se usa hoy. Guarda result.all_messages_json() tal cual.
CREATE TABLE IF NOT EXISTS conversations (
    wa_id       text PRIMARY KEY,
    messages    jsonb       NOT NULL,
    actualizado timestamptz NOT NULL DEFAULT now()
);


-- ── SISMED ────────────────────────────────────────────────────────────────
-- Se llena en el slice de la función 1. Ver raw/README.md antes del ETL:
-- `Mercado Relevante` siempre trae 3 segmentos; `Medicamento` varía entre 2 y
-- 6, así que de ahí se toma el primero y el último, nunca por índice.
CREATE TABLE IF NOT EXISTS medications (
    cum                  text PRIMARY KEY,
    principio_activo     text,
    forma                text,
    via                  text,
    nombre_comercial     text,
    laboratorio          text,
    descripcion          text    NOT NULL,
    cantidad             numeric,
    unidad               text,
    precio_institucional numeric NOT NULL,
    precio_comercial     numeric,          -- 32 % dice "No regulado"
    circular             text,
    vigencia_desde       date,
    search_text text GENERATED ALWAYS AS (
        curuba_norm(
            coalesce(principio_activo, '') || ' ' ||
            coalesce(nombre_comercial, '') || ' ' ||
            coalesce(descripcion, '')
        )
    ) STORED
);

CREATE INDEX IF NOT EXISTS medications_search_trgm
    ON medications USING gin (search_text gin_trgm_ops);


-- ── INVIMA ────────────────────────────────────────────────────────────────
-- La fuente no trae CUM (trae ATC), así que no se puede unir con medications
-- por llave: el cruce, si se hace, es por nombre o por ATC.
CREATE TABLE IF NOT EXISTS shortages (
    id                serial PRIMARY KEY,
    nombre            text NOT NULL,
    atc               text,
    estado            text,   -- monitorizacion | no_desabastecido | riesgo | desabastecido
    fecha_seguimiento date,
    listado           text,
    search_text text GENERATED ALWAYS AS (curuba_norm(nombre)) STORED
);

CREATE INDEX IF NOT EXISTS shortages_search_trgm
    ON shortages USING gin (search_text gin_trgm_ops);


-- ── Tutela ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tutela_drafts (
    wa_id       text PRIMARY KEY,
    campos      jsonb       NOT NULL DEFAULT '{}'::jsonb,
    actualizado timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    wa_id     text,
    contenido bytea       NOT NULL,
    creado    timestamptz NOT NULL DEFAULT now()
);
