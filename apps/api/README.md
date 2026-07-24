# Curuba — API

El servicio que está detrás del número de WhatsApp. Recibe los mensajes que reenvía
Twilio, corre el agente y responde: cotiza fórmulas contra SISMED, consulta
desabastecimientos del INVIMA y genera el PDF de una tutela.

> **Estado: el esqueleto camina; faltan las tools.** Ya existen `config.py`, `agent.py` y
> `main.py`: el webhook de Twilio responde, el agente contesta en español por OpenRouter y
> recuerda el hilo (en RAM, no en Postgres todavía). **Todavía no existen** `db.py`,
> `tutela.py`, `etl.py`, `schema.sql`, las cuatro tools, `GET /f/{id}` ni la lectura de
> fotos. Todo lo de abajo sigue siendo el destino, no el estado actual.

**Lo importante de la arquitectura: es un solo agente con cuatro tools, no tres
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

## Las cuatro tools

| Tool | Qué hace |
|---|---|
| `buscar_medicamento(nombre)` | Busca en SISMED por similitud y devuelve hasta 8 candidatos con presentación, laboratorio, precio institucional y **score** |
| `consultar_desabastecimiento(nombre)` | Busca en el seguimiento del INVIMA; devuelve estado (`monitorizacion`, `riesgo`, `desabastecido`, `no_desabastecido`) y fecha, o dice explícitamente que no hay reportes |
| `guardar_dato_tutela(campo, valor)` | Guarda una respuesta de la entrevista y devuelve qué campos faltan |
| `generar_tutela()` | Valida que no falte nada, arma el PDF, lo guarda y devuelve su URL pública |

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
| `medications` | SISMED. PK `cum` |
| `shortages` | INVIMA. Nombre, ATC, estado |
| `conversations` | PK `wa_id`, historial de Pydantic AI serializado en `jsonb` |
| `tutela_drafts` | PK `wa_id`, respuestas de procedibilidad en `jsonb` |
| `documents` | PDFs generados en `bytea`, servidos por `GET /f/{id}` |

`medications` y `shortages` llevan una columna generada `search_text` con el texto
normalizado, e índice GIN `gin_trgm_ops` encima.

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

uv sync --extra etl           # el extra 'etl' trae pandas y openpyxl
uv run python -m curuba.etl   # crea el esquema y carga resources/data/
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
- **Las dependencias del ETL van en un extra opcional** (`[project.optional-dependencies]
  etl`) para que Railway no instale pandas en cada deploy. `uv pip compile pyproject.toml
  -o requirements.txt` no incluye los extras, así que sale bien por defecto.

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

**3. El match de medicamentos nunca es exacto.** Una fórmula escrita a mano dice
"acetaminofen 500" y SISMED dice `ACETAMINOFÉN 500 MG TABLETA RECUBIERTA`:

```sql
SELECT cum, principio_activo, descripcion, precio_institucional,
       similarity(search_text, curuba_norm($1)) AS score
FROM medications
WHERE search_text % curuba_norm($1)
ORDER BY score DESC
LIMIT 8;
```

Devolverle al agente los candidatos **con su score** y que desambigüe o pregunte. No
escoger el primero en silencio: un precio equivocado en una app de salud es peor que no
dar precio.

## Datos

Los archivos fuente **están en el repo**, en [`resources/data/`](../../resources/data/README.md):

| Fuente | Archivo | Qué carga el ETL | Corte |
|---|---|---|---|
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
