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
    -- Mercado relevante: 645 grupos. Mismo id_mr = mismo principio activo, forma y vía,
    -- o sea que el gobierno ya hizo el clustering de equivalentes (mediana de 21
    -- presentaciones por grupo). No se expone en ninguna tool todavía: "misma molécula"
    -- NO es intercambiabilidad clínica y el agente no puede recomendar cambios. Se guarda
    -- porque cuesta una columna y evita recargar 38.731 filas después.
    id_mr                text,
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

-- `CREATE TABLE IF NOT EXISTS` no altera una tabla que ya existe, así que en las bases
-- que se crearon antes de que id_mr entrara al proyecto la columna no aparece sola.
ALTER TABLE medications ADD COLUMN IF NOT EXISTS id_mr text;

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


-- ── PBS ───────────────────────────────────────────────────────────────────
-- Cobertura con cargo a la UPC. Es la tabla que se consulta PRIMERO: si el medicamento
-- está financiado, la ruta es el dispensador de la EPS y el precio es casi irrelevante.
--
-- Dos cosas que se ven raras y son a propósito:
--
--   1. La PK es serial y no el ATC. `CodigoATC` se repite (1.469 distintos en 2.067
--      filas) y dentro de un mismo ATC la cobertura CAMBIA: N02BE51 tiene 29 filas de
--      combinaciones de acetaminofén repartidas entre financiado, condicionada y MIPRES.
--      Por eso la búsqueda va por principio activo (2.007 distintos, casi único) y el ATC
--      solo sirve para cruzar con shortages.
--   2. `cobertura` es texto de cinco valores, no un booleano. En particular `mipres` NO
--      significa "cómprelo usted": es otra vía de prescripción que la EPS igual debe
--      surtir. Ver resources/data/README.md.
CREATE TABLE IF NOT EXISTS coverage (
    id               serial PRIMARY KEY,
    atc              text,
    principio_activo text NOT NULL,
    forma            text,
    cobertura        text,   -- upc | condicionada | mipres | excluido | NULL ("Sin dato")
    aclaracion       text,   -- el criterio, textual. El agente lo cita, no lo interpreta
    search_text text GENERATED ALWAYS AS (curuba_norm(principio_activo)) STORED
);

CREATE INDEX IF NOT EXISTS coverage_search_trgm
    ON coverage USING gin (search_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS coverage_atc ON coverage (atc);


-- ── Ruta legal ────────────────────────────────────────────────────────────
-- Un caso por número. `campos` guarda TODA la entrevista en un solo jsonb: los
-- datos de identidad, los del caso, los de triage y los específicos de cada
-- escrito. No se parte por tipo de documento a propósito — la mitad de los
-- campos los comparten los cuatro, y quien decide cuál escrito procede es
-- decidir_ruta() sobre estos mismos datos, no una elección previa del usuario.
--
-- Reemplaza a `tutela_drafts`, que se declaró cuando el plan era un solo
-- documento y nunca llegó a usarse. El DROP es seguro por eso mismo.
DROP TABLE IF EXISTS tutela_drafts;

CREATE TABLE IF NOT EXISTS casos (
    wa_id       text PRIMARY KEY,
    campos      jsonb       NOT NULL DEFAULT '{}'::jsonb,
    actualizado timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    wa_id     text,
    -- peticion | tutela | desacato | supersalud. Sirve para el nombre del
    -- archivo que se le manda al usuario y para saber qué se generó.
    tipo      text,
    contenido bytea       NOT NULL,
    creado    timestamptz NOT NULL DEFAULT now()
);

-- `CREATE TABLE IF NOT EXISTS` no altera una tabla que ya existe: en las bases
-- creadas antes de la ruta legal la columna no aparece sola.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS tipo text;


-- ── Caché de las búsquedas web ────────────────────────────────────────────
-- Las dos tools que salen a Perplexity Sonar guardan acá su respuesta. Lo que
-- de verdad compra esta tabla NO es la plata ($0.005 por búsqueda): es que la
-- demo sea REPRODUCIBLE. Sonar no es determinista, así que "Dolex" puede
-- resolver bien en el ensayo y devolver otra cosa en la sustentación. Con
-- caché, la segunda corrida es la primera, byte por byte. De paso, repetir una
-- consulta pasa de ~5 s a ~5 ms, que en WhatsApp se nota.
--
-- El TTL se aplica al LEER (ver leer_cache_web), no hay limpieza programada:
-- es un hackathon y la tabla no pasa de unas decenas de filas.
CREATE TABLE IF NOT EXISTS web_cache (
    clave     text PRIMARY KEY,   -- "identificar:dolex" | "drogueria:losartan 50"
    respuesta jsonb       NOT NULL,
    creado    timestamptz NOT NULL DEFAULT now()
);
