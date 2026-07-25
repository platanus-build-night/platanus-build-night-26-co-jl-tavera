# Curuba — API

El servicio que está detrás del número de WhatsApp. Recibe los mensajes que reenvía
Twilio, corre el agente y responde: cotiza fórmulas contra SISMED, consulta
desabastecimientos del INVIMA y genera el PDF de una tutela.

> **Estado: los datos y las tres tools que los leen ya funcionan; falta la tutela.**
> Existen `config.py`, `db.py`, `agent.py`, `main.py`, `etl.py` y `schema.sql`. Las tres
> fuentes están cargadas en Postgres (2.067 / 38.731 / 783 filas) y el agente contesta
> con `consultar_cobertura`, `buscar_medicamento` y `consultar_desabastecimiento`. El
> historial está en Postgres, no en RAM.
> **Todavía no existen** `tutela.py`, `DejaVuSans.ttf`, `guardar_dato_tutela`,
> `generar_tutela`, `GET /f/{id}` ni la lectura de fotos. Tampoco está declarado `fpdf2`
> en `pyproject.toml`, ni `PUBLIC_BASE_URL` en `config.py`: los dos hacen falta para ese
> slice.

**Lo importante de la arquitectura: es un solo agente con cinco tools, no tres
endpoints.** WhatsApp es una sola conversación, así que no hay ruteo por palabras clave
ni menús — el modelo decide qué tool usar. Eso es lo que permite que "mándame una foto de
tu fórmula", "¿el losartán está desabastecido?" y "quiero hacer una tutela" convivan en el
mismo hilo sin código de despacho.

## Stack

| Pieza | Qué |
|---|---|
| Web | FastAPI + Uvicorn |
| Agente | Pydantic AI (`pydantic-ai-slim[openrouter]`) |
| Modelo | Claude vía OpenRouter |
| Datos | Postgres con `pg_trgm` y `unaccent` (asyncpg) |
| Canal | Twilio WhatsApp |
| PDF | `fpdf2` |
| Deploy | Railway |

## Estructura planeada

Siete archivos. Es a propósito: antes de crear uno nuevo, extender el que ya existe.

```
apps/api/
├── pyproject.toml
├── requirements.txt          # exportado de uv; red de seguridad para Nixpacks
├── railway.json
├── .env
└── src/curuba/
    ├── main.py
    ├── config.py
    ├── db.py
    ├── agent.py
    ├── tutela.py
    ├── etl.py
    ├── schema.sql
    └── DejaVuSans.ttf
```

| Archivo | Qué va adentro |
|---|---|
| `main.py` | App de FastAPI: webhook de Twilio, `GET /f/{id}`, `/health` |
| `config.py` | Settings desde el entorno con `pydantic-settings` |
| `db.py` | Pool de asyncpg y **todo** el SQL del proyecto |
| `agent.py` | El `Agent` de Pydantic AI: prompt del sistema y las cuatro tools |
| `tutela.py` | Campos de procedibilidad y render del PDF |
| `etl.py` | Carga `resources/data/` a Postgres — se corre en local, no en Railway |
| `schema.sql` | Tablas, extensiones e índices |
| `DejaVuSans.ttf` | Fuente Unicode para el PDF (ver trampa #2) |

## Las cinco tools

| Tool | Qué hace |
|---|---|
| `consultar_cobertura(nombre)` | Busca en el PBS si lo financia la UPC. Devuelve la cobertura (`upc`, `condicionada`, `mipres`, `excluido`), qué significa y la aclaración textual |
| `buscar_medicamento(nombre)` | Busca en SISMED por similitud y devuelve hasta 8 candidatos con presentación, laboratorio, precio institucional y **score** |
| `consultar_desabastecimiento(nombre)` | Busca en el seguimiento del INVIMA; devuelve estado (`monitorizacion`, `riesgo`, `desabastecido`, `no_desabastecido`) y fecha, o dice explícitamente que no hay reportes |
| `guardar_dato_tutela(campo, valor)` | Guarda una respuesta de la entrevista y devuelve qué campos faltan |
| `generar_tutela()` | Valida que no falte nada, arma el PDF, lo guarda y devuelve su URL pública |

**`consultar_cobertura` va primero y el prompt lo dice.** Si el medicamento está
financiado con la UPC, el precio es casi irrelevante: la ruta es el dispensador de la EPS
pagando la cuota moderadora. Dar el precio antes manda al paciente a gastar plata que no
tenía que gastar. Comparar precios ahorra 20–40 %; enrutar bien ahorra ~100 %.

**Las tres tools de datos devuelven `encontrado` aparte de los candidatos.** Es para que
"no lo encontré" no se pueda confundir con "la respuesta es no" — sobre todo en cobertura,
donde el listado no es exhaustivo. Y el significado de cada estado se traduce en Python
(`COBERTURAS` y `ESTADOS` en `agent.py`), no se deja a interpretación del modelo: `mipres`
**no** es "cómprelo usted".

**Cotizar una fórmula completa no es una tool aparte**: el agente llama
`buscar_medicamento` una vez por medicamento y suma. Menos código y el modelo maneja
mejor los casos raros (dos presentaciones del mismo principio activo, un medicamento que
no aparece).

**La entrevista de la tutela tampoco es una máquina de estados.** El agente pregunta de a
una, guarda cada respuesta con `guardar_dato_tutela`, y esa tool le devuelve los campos
que faltan. Así maneja gratis las respuestas desordenadas, las correcciones y los
mensajes donde la persona contesta tres cosas de una.

### Campos de la tutela

`accionante_nombre` · `accionante_cedula` · `accionante_ciudad` · `accionante_direccion`
· `accionante_telefono` · `accionado` · `servicio_negado` · `solicitud_previa` ·
`perjuicio` · `otro_medio_defensa` · `fecha_hechos` · `tutela_previa`

El PDF debe cubrir lo que un juez va a mirar: hechos, derechos vulnerados (arts. 11, 1 y
49 C.P. y Ley 1751 de 2015), **procedibilidad** (subsidiariedad, inmediatez, legitimación
por pasiva, no temeridad), pretensiones, juramento, pruebas, notificaciones y firma.

## Modelo de datos

Requiere las extensiones `pg_trgm`, `unaccent` y `pgcrypto`.

| Tabla | Para qué |
|---|---|
| `coverage` | PBS. Principio activo, ATC y cobertura con cargo a la UPC |
| `medications` | SISMED. PK `cum` |
| `shortages` | INVIMA. Nombre, ATC, estado |
| `conversations` | PK `wa_id`, historial de Pydantic AI serializado en `jsonb` |
| `tutela_drafts` | PK `wa_id`, respuestas de procedibilidad en `jsonb` |
| `documents` | PDFs generados en `bytea`, servidos por `GET /f/{id}` |

`coverage`, `medications` y `shortages` llevan una columna generada `search_text` con el
texto normalizado, e índice GIN `gin_trgm_ops` encima.

### `coverage`

La PK es un `serial` y **no** el ATC: `CodigoATC` se repite (1.469 distintos en 2.067
filas) y, peor, dentro de un mismo ATC la cobertura cambia — `N02BE51` tiene 29 filas de
combinaciones de acetaminofén repartidas entre `upc`, `condicionada` y `mipres`. La
búsqueda va por principio activo (2.007 distintos, casi único); el ATC solo sirve para
cruzar con `shortages`.

| Columna | De dónde sale |
|---|---|
| `atc` | `CodigoATC` |
| `principio_activo` | `PrincipioActivo`. Es la llave de búsqueda |
| `forma` | `FormaFarmaceutica`. `Resumen` es idéntica y se descarta |
| `cobertura` | `CoberturaPlanBeneficiosUPC` normalizada a `upc` \| `condicionada` \| `mipres` \| `excluido` \| `NULL` |
| `aclaracion` | `Aclaracion`, textual. `Sin dato` (1.061 filas) se guarda como `NULL` |

**`mipres` no es "no cubierto"** — son 420 filas y es otra vía de prescripción que la EPS
igual debe surtir. Y como el listado no es exhaustivo (el cruce con SISMED por principio
activo llega al 72,5 %), la ausencia se reporta como "no lo encontré", nunca como
negación. El detalle está en [`resources/data/README.md`](../../resources/data/README.md).

### `medications`

El CSV del SISMED **no trae columnas de principio activo, marca ni laboratorio** — hay
que derivarlas. Detalle completo del archivo en [`resources/data/README.md`](../../resources/data/README.md).

| Columna | De dónde sale |
|---|---|
| `cum` | `CUM`. PK — verificado único en las 38.731 filas |
| `principio_activo` | `Mercado Relevante`, segmento 1 |
| `forma` / `via` | `Mercado Relevante`, segmentos 2 y 3 |
| `nombre_comercial` | `Medicamento`, **primer** segmento |
| `laboratorio` | `Medicamento`, **último** segmento |
| `descripcion` | `Medicamento` completo — es lo que se le muestra al usuario |
| `cantidad` / `unidad` | `Cantidad por unidad de medida`, `Unidad de medida` |
| `precio_institucional` | Precio máximo institucional. `NOT NULL`: siempre viene |
| `precio_comercial` | Precio máximo comercial primaria/secundaria. Nullable — 32 % dice `No regulado` |
| `circular` / `vigencia_desde` | `Circular CNPMDM`, `Fecha de inicio vigencia...` |

`Mercado Relevante` siempre trae 3 segmentos, así que ahí sí se puede partir por
posición. `Medicamento` varía entre 2 y 6 segmentos: **primero y último, nunca por
índice**.

`search_text` se genera sobre `principio_activo + nombre_comercial + descripcion`.

> **El precio final al público casi nunca está regulado.** La columna de precio comercial
> final trae valor en **4 filas de 38.731**; el resto dice `No regulado`. Por eso no se
> guarda. La consecuencia es de producto, no de esquema: Curuba **no puede decir "esto es
> lo que deberías pagar en la droguería"**, solo cuál es el techo regulado del canal
> institucional. Las instrucciones del agente tienen que sostener esa distinción al
> responder.

### `shortages`

Se carga desde `resources/data/clean/desabastecimiento.csv` — **783 filas**, ya extraídas del PDF
(ver [`resources/data/README.md`](../../resources/data/README.md)). El ETL no abre PDFs.

La fuente del INVIMA **no trae CUM**, trae ATC — o sea que no se puede unir con
`medications` por llave; el cruce, si se hace, es por nombre o por ATC. El `No.` tampoco
sirve de llave: el PDF renumera desde 1 en cada tabla y además repite tres números.

| Columna | De dónde sale |
|---|---|
| `nombre` | `nombre` (trae la forma y la concentración pegadas: `ACETAMINOFEN + CODEINA TABLETA 325 mg + 30 mg`) |
| `atc` | `atc`. Ojo: los dos últimos dígitos son opcionales (`V07AB` es válido) |
| `estado` | `monitorizacion` \| `riesgo` \| `desabastecido` \| `no_desabastecido`. **Nullable**: una fila viene sin estado en la fuente |
| `fecha_seguimiento` | `fecha_seguimiento`, ya en ISO |
| `listado` | `activo` \| `cerrado` |

`search_text` sobre `nombre`.

> **`no_desabastecido` son 373 de las 783 filas y no significa "no hay reportes".**
> Significa que el INVIMA sí le hizo seguimiento y lo cerró. Es información útil para el
> paciente y es lo contrario de que el medicamento no aparezca en la tabla. Las
> instrucciones del agente tienen que distinguir los dos casos al responder — es la misma
> clase de distinción que la de precio institucional vs. precio de mostrador.

Un mismo principio activo aparece varias veces con formas distintas (`ÁCIDO VALPROICO
CÁPSULA DURA`, `... JARABE`, `... SOLUCIÓN INYECTABLE`): son filas legítimamente
distintas, así que la tool devuelve varias y deja que el agente escoja, igual que
`buscar_medicamento`.

**Ojo con `unaccent`:** no es `IMMUTABLE`, así que no se puede usar directo en una columna
generada. Hay que envolverla:

```sql
CREATE OR REPLACE FUNCTION curuba_norm(txt text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS
$$ SELECT lower(public.unaccent('public.unaccent', txt)) $$;
```

### Historial de conversación

El webhook no tiene estado. Guardar `result.all_messages_json()` en
`conversations.messages` y recargarlo con
`ModelMessagesTypeAdapter.validate_json(...)`.

## Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| `POST` | `/webhooks/twilio/whatsapp` | Lo que llama Twilio. Form-encoded |
| `GET` | `/f/{id}` | Sirve los PDFs. **Tiene que ser público**: Twilio lo descarga para adjuntarlo |
| `GET` | `/health` | Healthcheck de Railway |

Campos del webhook: `From` (`whatsapp:+57...`), `Body`, `NumMedia`, `MediaUrl0`,
`MediaContentType0`, `MessageSid`, `ProfileName`. Validar el header
`X-Twilio-Signature` con `twilio.request_validator.RequestValidator`. Las URLs de media
requieren **Basic auth** con el Account SID y el Auth Token para descargarse.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Postgres. Railway la inyecta sola; en local, la URL pública del servicio |
| `OPENROUTER_API_KEY` | OpenRouter |
| `CURUBA_MODEL` | Por defecto `openrouter:anthropic/claude-sonnet-5`. Verificar el slug en openrouter.ai/models |
| `TWILIO_ACCOUNT_SID` | Twilio |
| `TWILIO_AUTH_TOKEN` | Twilio — también valida la firma del webhook |
| `TWILIO_WHATSAPP_FROM` | El número, con formato `whatsapp:+57...` |
| `PUBLIC_BASE_URL` | URL pública de la API; con esto se arman los enlaces de los PDFs |
| `VALIDATE_TWILIO_SIGNATURE` | `false` solo para pruebas locales |

El modelo necesita visión para leer fotos de fórmulas. Las imágenes se pasan con
`BinaryContent(data=..., media_type=...)` dentro de la lista del prompt.

## Cómo correrlo

```bash
cd apps/api
cp .env.example .env          # llenar las variables de arriba

uv sync                       # el ETL no necesita el extra: usa csv de la stdlib
uv run python -m curuba.etl   # crea el esquema y carga resources/data/
uv run python -m curuba.etl --solo pbs --limite 100   # una fuente, unas pocas filas
uv run uvicorn curuba.main:app --app-dir src --reload
```

El webhook necesita una URL pública para probarse de verdad:

```bash
ngrok http 8000
# apuntar el webhook de WhatsApp en la consola de Twilio a
# https://<subdominio>.ngrok.io/webhooks/twilio/whatsapp
```

Vale la pena dejar un comando `reiniciar` por WhatsApp que borre la conversación y el
borrador de tutela — se usa mucho mientras se prueba.

## Deploy en Railway

- Builder **Nixpacks**, con un `requirements.txt` commiteado.
- Start: `uvicorn curuba.main:app --app-dir src --host 0.0.0.0 --port $PORT`
- Healthcheck: `/health`
- **El ETL no agrega dependencias.** Lee los tres CSV con `csv` de la stdlib y carga con
  el `copy_records_to_table` de asyncpg, que ya está. El extra
  `[project.optional-dependencies] etl` (pandas, openpyxl) quedó **sin uso** — se puede
  borrar. De todos modos `uv pip compile pyproject.toml -o requirements.txt` no incluye
  los extras, así que Railway nunca los instaló.

## Tres trampas

Ya costaron tiempo una vez. Están aquí para no volver a descubrirlas.

**1. Twilio corta el webhook a los ~15 segundos.** Una corrida del agente con tools se
demora más. El webhook tiene que responder `200` con TwiML vacío de inmediato y mandar la
respuesta real aparte, por la API REST de Twilio, desde un `BackgroundTasks`. Si esto se
hace mal, Twilio reintenta en silencio y al usuario le llegan mensajes duplicados —
además se rompe justo en la demo, que es cuando las respuestas son más largas.

**2. El PDF necesita una fuente Unicode registrada a mano.**

```python
pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
```

Sin eso las tildes y la ñ salen dañadas. Y aparte: `strftime("%B")` sigue el locale del
sistema, y en el contenedor sale en inglés — genera *"24 de July de 2026"* en el
encabezado. Hay que tener los meses en español en una constante, no depender del locale.

**3. El match de medicamentos nunca es exacto, y `similarity()` no sirve para esto.** Una
fórmula escrita a mano dice "losartan 50" y SISMED dice `ARAMAX - Amlodipino 2,5mg/1U +
Losartan 50mg/1U - Sólido - Oral x 30 - MEGALABS`.

La versión obvia —`similarity()` con el operador `%`— **devuelve cero filas siempre**, y
falla en silencio: no hay error, solo un resultado vacío que parece "no existe".
`similarity(a, b)` divide los trigramas en común sobre la unión de los dos, así que
castiga la diferencia de longitud, y `search_text` promedia 103 caracteres contra una
consulta de dos palabras:

```
similarity('omeprazol', 'esomeprazol nexium nexium - esomeprazol 40mg/1u ...')  -> 0.119
word_similarity('omeprazol', <lo mismo>)                                        -> 0.800
```

Con el umbral por defecto de 0.3, la primera no pasa nunca. Va `word_similarity` con el
operador `<%`, que mide qué tan bien encaja la consulta dentro de un pedazo del texto:

```sql
SELECT * FROM (
    SELECT DISTINCT ON (descripcion, precio_institucional)
           cum, principio_activo, descripcion, precio_institucional,
           round(word_similarity(curuba_norm($1), search_text)::numeric, 2) AS score
    FROM medications
    WHERE curuba_norm($1) <% search_text
    ORDER BY descripcion, precio_institucional,
             word_similarity(curuba_norm($1), search_text) DESC
) c
ORDER BY score DESC,
         similarity(curuba_norm(principio_activo), curuba_norm($1)) DESC
LIMIT 8;
```

Dos detalles que no son cosméticos:

- **`similarity` sí se usa, pero solo para desempatar.** Buscar "losartan" deja `LOSARTÁN`,
  `LOSARTÁN + AMLODIPINA` y `LOSARTÁN + HIDROCLOROTIAZIDA` empatados en 1.00; sin el
  desempate el orden queda al azar y la molécula sola no sale de primera.
- **`DISTINCT ON` porque un mismo producto tiene varios CUM.** Hay 8.612 grupos con
  descripción y precio idénticos; sin eso, los 8 candidatos pueden ser la misma caja ocho
  veces. Las presentaciones que solo cambian de laboratorio sí se conservan.

Devolverle al agente los candidatos **con su score** y que desambigüe o pregunte. No
escoger el primero en silencio: un precio equivocado en una app de salud es peor que no
dar precio.

Y ojo con el ejemplo clásico: **acetaminofén no está en SISMED** — cero filas. No es un
bug del match, es que no está bajo control directo de precios. Sí está en el PBS y
financiado con la UPC, que es justo el caso que justifica consultar la cobertura primero.

## Datos

Los archivos fuente **están en el repo**, en [`resources/data/`](../../resources/data/README.md):

| Fuente | Archivo | Qué carga el ETL | Corte |
|---|---|---|---|
| PBS | `resources/data/raw/pbs/Medicamentos_del_PBS_20260724.csv` (1,0 MB) | 2.067 filas | 2026-07-24 |
| SISMED | `resources/data/raw/sismed/Precio_máximo_de_venta_..._20260724.csv` (9,5 MB) | 38.731 filas | 2026-07-24 |
| INVIMA | `resources/data/raw/invima/LISTADO DE ABASTECIMIENTO MAYO 2026.pdf` (1,6 MB) | — | mayo 2026 |
| INVIMA | `resources/data/clean/desabastecimiento.csv` (83 KB) | 783 filas | mayo 2026 |

**El ETL lee dos CSV, nunca el PDF.** La extracción es un paso aparte
(`resources/data/scripts/extraer_invima.py`, con pdfplumber) que ya corrió y dejó su salida
commiteada. Por eso pdfplumber **no** va en el extra `etl` ni en `requirements.txt`: solo
haría más lento cada deploy de Railway. Se vuelve a correr cuando el INVIMA publique el
listado del mes siguiente.

`resources/data/README.md` tiene el detalle de columnas, las trampas de parseo de cada uno y la
justificación de por qué se guarda un precio y no otro. **Leerlo antes de escribir el
ETL.**

## Aviso legal

Curuba no da asesoría médica ni jurídica. Los precios son techos regulados del SISMED
para el canal institucional, no lo que cobra un punto de venta. La tutela es un
**borrador que debe revisarse antes de radicarse** — ese aviso va en el pie del PDF y en
la respuesta de WhatsApp.
