# Curuba

Agente de WhatsApp para pacientes en Colombia. Hace tres cosas: (1) lee una fórmula
médica —texto o foto— extrae los medicamentos y los cotiza contra SISMED; (2) consulta
si un medicamento está desabastecido según INVIMA, cuando el usuario lo pregunta;
(3) hace el triage de la **ruta legal** y genera el PDF del escrito que procede.

La (3) son cuatro escritos, no uno: derecho de petición, tutela, incidente de desacato y
demanda ante la función jurisdiccional de la Supersalud. **Cuál procede lo decide
`legal.decidir_ruta()` en Python, nunca el modelo** — escoger mal el mecanismo es el modo
de falla real del producto.

Proyecto de hackathon (Platanus Build Night). Optimizar para que funcione y se pueda
demostrar, no para generalidad.

## Stack

| Pieza | Qué | Dónde corre |
|---|---|---|
| API | FastAPI + Pydantic AI | Railway |
| Modelo | Claude vía OpenRouter | — |
| Datos | Postgres (`pg_trgm`, `unaccent`) | Railway |
| Canal | Twilio WhatsApp (número propio) | — |
| PDF | `fpdf2` | — |
| Landing | Next.js | Railway |

## Estado

```
apps/api/     FastAPI + Pydantic AI, va a Railway. Camina de punta a punta: webhook,
              agente con cinco tools (en `tools/`), datos en Postgres y la ruta legal
              con sus cuatro PDF (en `legal/`). Falta leer fotos de fórmulas
apps/web/     Landing en Next.js, corre en Railway como el servicio `curuba-web`. Escrita
              y desplegada; no depende de la API
resources/
  data/raw/     Fuentes SISMED e INVIMA (~11 MB, SÍ van al repo)
  data/clean/   desabastecimiento.csv — derivado del PDF, es lo que lee el ETL
  data/scripts/ extraer_invima.py — de un solo uso, no es dependencia de la API
  docs/         DEPLOYMENT.md, RESEARCH.md (las cifras y sus fuentes) y DESIGN.md
```

El estado real de cada servicio está al principio de su README, no aquí — este archivo se
desactualiza primero.

**Los datos del INVIMA ya están extraídos.** El PDF resultó ser tres tablas en fuente de
2,4 pt con celdas combinadas que cruzan páginas; `resources/data/scripts/extraer_invima.py` lo
convierte a `desabastecimiento.csv` (783 filas, commiteado). Ese script es de un solo uso
y se vuelve a correr cuando salga el listado del mes siguiente — **el ETL lee dos CSV y
nunca abre un PDF**, por eso pdfplumber no es dependencia de la API. Las cuatro trampas
del parseo están en `resources/data/README.md`; hay una que marca 373 medicamentos justo al revés de
lo que dicen.

**Antes de escribir código en cualquiera de los dos, leer su README.** Ahí está la
estructura de archivos planeada, el modelo de datos, los endpoints, las variables de
entorno y las trampas conocidas. Ese es el spec, no este archivo.

## Convenciones

- **Todo lo que ve el usuario va en español.** Los nombres de las tools también
  (`buscar_medicamento`, `consultar_desabastecimiento`) — el modelo escoge mejor.
- **Todo el SQL debe quedar en `db.py`.** Ninguna query suelta en `agent.py` ni en
  `main.py`.
- **Un paquete por concern, archivos planos adentro.** La raíz de `curuba/` se mantiene
  corta —`main`, `config`, `db`, `agent`, `etl`— y lo que crece se vuelve paquete:
  `tools/` (un módulo por grupo de tools) y `legal/` (texto, documentos, fechas, campos,
  ruteo, plantillas, pdf). Dentro de un paquete, un archivo por responsabilidad y sin
  anidar de más. No crear un módulo suelto en la raíz para algo que le cabe a un paquete.
- Config solo por variables de entorno, nunca hardcodeada.

## Comandos

```bash
cd apps/api
uv sync                                              # --extra etl añade pandas
uv run uvicorn curuba.main:app --app-dir src --reload
uv pip compile pyproject.toml -o requirements.txt    # regenerar para Railway

PYTHONPATH=src uv run python -m curuba.agent         # REPL del agente, sin WhatsApp
PYTHONPATH=src uv run python -m curuba.db            # aplicar schema.sql a mano
PYTHONPATH=src uv run python -m curuba.etl           # cargar resources/data/ a Postgres
```

En el REPL, `reiniciar` borra la conversación **y el caso** — se usa todo el tiempo
probando la entrevista legal, que si no arrastra los campos de la corrida anterior.

El REPL solo necesita `OPENROUTER_API_KEY` y `DATABASE_URL`: sirve para iterar el prompt
sin tocar Twilio. Para probar el webhook completo en local no hace falta túnel — se le
manda un POST form-encoded a `/webhooks/twilio/whatsapp` con `From=whatsapp:%2B57...`
(el `+` va como `%2B`) y la respuesta sale por la API REST al celular de verdad. Eso sí,
el número tiene que haberle escrito al sender en las últimas 24 h o Meta rechaza el
mensaje con **error 63016**.

## Despliegue

Todo el detalle está en [`resources/docs/DEPLOYMENT.md`](resources/docs/DEPLOYMENT.md):
Railway, la configuración del sender de Twilio, la ventana de 24 h de Meta y el orden en
que conviene probar. Lo mínimo para no romper nada sin leerlo:

- **Hay dos repos.** Railway no accede al de la organización, así que `origin` tiene dos
  push URLs y un solo `git push` actualiza el del jurado y el espejo
  `jl-tavera/curuba-platanus`. Esa config vive en `.git/config`, **no se commitea**, y un
  hook `pre-push` aborta si falta alguno.
- **Se trabaja siempre en esta carpeta.** `../curuba-platanus` es copia de solo lectura.

## Skills

`.claude/skills/` está commiteado: al clonar ya vienen. Todo se instala **project-local**,
nunca a nivel de usuario. Son tres sistemas distintos y cada uno se actualiza diferente:

**1. CLI `skills` de Vercel** → `.claude/skills/` en la raíz (9 skills), manifiesto
`skills-lock.json`. Las seis de `apps/web` (`vercel-react-best-practices`,
`frontend-design`, los cuatro workflows de Next.js) más `use-railway`,
`pydantic-models-py` y `fastapi-router-py`.

```bash
npx skills add <repo> --skill <nombre> -a claude-code --copy -y
npx skills update -p
```

**2. `library-skills`** → las skills que vienen **dentro de los paquetes instalados**.
Ahora mismo `building-pydantic-ai-agents`, que la trae `pydantic-ai-slim`. Se corre desde
`apps/api`, **no desde la raíz**: descubre leyendo el `.venv`, y en la raíz no hay ni
`pyproject.toml` ni venv, así que ahí no encuentra nada —`--all` tampoco lo arregla—.
Por eso queda en `apps/api/.claude/skills/`, scopeada a ese directorio.

```bash
cd apps/api
uvx library-skills scan                        # ver qué hay, sin escribir
uvx library-skills --claude --copy --no-tool-skill -y -s <nombre>
```

`library-skills` solo le hace seguimiento a lo que instala como symlink. Como en Windows
toca `--copy`, marca la copia como `hand-authored` y sigue reportando la skill del paquete
como `new`: **`--check` no sirve de detector de drift acá**, siempre sale 0. Al subir la
versión de `pydantic-ai-slim` hay que volver a correr el comando de instalación a mano;
sobreescribe la copia.

**3. Plugin de Twilio** → `twilio-developer-kit@twilio`, declarado en
`.claude/settings.json` (`--scope project`; `local` iría al `settings.local.json`, que
está en el gitignore global y no se comparte). Un plugin se instala entero: no se pueden
escoger skills sueltas adentro, y este trae las de 30+ productos.

```bash
claude plugin marketplace add twilio/ai --scope project
claude plugin install twilio-developer-kit@twilio --scope project
```

Cuatro trampas al agregar más:

- **`--skill '*'` trae también las skills internas del repo fuente.** En `vercel/next.js`
  eso son 12 extra para contribuirle a Next.js (`backport-pr`, `v8-jit`,
  `react-vendoring`…). Pedir las skills por nombre, siempre.
- **`microsoft/skills` necesita `--full-depth`.** Sin él descubre 13 skills; con él, 182.
  `pydantic-models-py` y `fastapi-router-py` están en el segundo grupo (cuelgan de
  `.github/plugins/azure-sdk-python/`), así que sin la bandera falla con "skill not found".
- **`--copy` es obligatorio en Windows.** Los tres instaladores hacen symlinks por defecto.
- **`.agents/` está en el `.gitignore`.** Los instaladores escriben ahí una copia paralela
  de cada skill; la que Claude lee es `.claude/skills/`.

## Tres trampas conocidas

1. **Twilio corta el webhook a los ~15s.** Una corrida del agente con tools se demora
   más. El webhook responde `200` con TwiML vacío de inmediato y la respuesta real se
   manda aparte por la API REST desde un `BackgroundTasks`. Si esto se rompe, Twilio
   reintenta en silencio y llegan mensajes duplicados.
2. **El PDF y el español.** Registrar `DejaVuSans.ttf` explícitamente
   (`pdf.add_font('DejaVu', '', ruta)`) o las tildes y la ñ salen dañadas. **Sin
   `uni=True`:** ese parámetro desapareció en fpdf2 2.8 y pasarlo revienta con
   `TypeError`. Y aparte: `strftime('%B')` sigue el locale del sistema y en el contenedor
   sale en inglés — genera "24 de July de 2026". Los meses en español están en
   `legal.MESES`.
3. **El match de medicamentos nunca es exacto.** Una fórmula escrita a mano dice
   "acetaminofen 500" y SISMED dice `ACETAMINOFÉN 500 MG TABLETA RECUBIERTA`. Se usa
   similitud por trigramas y se le devuelven al agente los candidatos **con su score**
   para que desambigüe o pregunte. No escoger el primero en silencio: un precio
   equivocado en una app de salud es el peor error posible aquí.

## Aviso legal

Curuba no da asesoría médica ni jurídica. La tutela que genera es un **borrador que
debe revisarse antes de radicarse**. Ese aviso va en el pie del PDF, en la respuesta de
WhatsApp y en la landing. No quitarlo.
