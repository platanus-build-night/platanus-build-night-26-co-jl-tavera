# Curuba

Agente de WhatsApp para pacientes en Colombia. Hace tres cosas: (1) lee una fórmula
médica —texto o foto— extrae los medicamentos y los cotiza contra SISMED; (2) consulta
si un medicamento está desabastecido según INVIMA, cuando el usuario lo pregunta;
(3) hace las preguntas de procedibilidad y genera el PDF de una tutela.

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
| Landing | Next.js | Vercel |

## Estado

**Nada está implementado todavía.** El repo es un scaffold: estructura de carpetas y
specs. Los dos servicios están especificados pero vacíos.

```
apps/api/     Spec en apps/api/README.md — FastAPI + Pydantic AI, va a Railway
apps/web/     Spec en apps/web/README.md — landing en Next.js, va a Vercel
raw/          Fuentes SISMED e INVIMA (los dos archivos SÍ van al repo, ~11 MB)
```

**Antes de escribir código en cualquiera de los dos, leer su README.** Ahí está la
estructura de archivos planeada, el modelo de datos, los endpoints, las variables de
entorno y las trampas conocidas. Ese es el spec, no este archivo.

## Convenciones

- **Todo lo que ve el usuario va en español.** Los nombres de las tools también
  (`buscar_medicamento`, `consultar_desabastecimiento`) — el modelo escoge mejor.
- **Todo el SQL debe quedar en `db.py`.** Ninguna query suelta en `agent.py` ni en
  `main.py`.
- **Mantener pocos archivos.** Antes de crear uno nuevo, extender el que ya existe.
  La API son 7 archivos Python a propósito.
- Config solo por variables de entorno, nunca hardcodeada.

## Comandos

Aplican una vez que `apps/api` exista (hoy todavía no).

```bash
cd apps/api
uv sync --extra etl                                  # instalar (etl trae pandas)
uv run python -m curuba.etl                          # cargar raw/ a Postgres
uv run uvicorn curuba.main:app --app-dir src --reload
uv pip compile pyproject.toml -o requirements.txt    # regenerar para Railway
```

Para probar el webhook en local hace falta un túnel público (`ngrok http 8000`) y
apuntar el webhook de Twilio ahí.

## Tres trampas conocidas

1. **Twilio corta el webhook a los ~15s.** Una corrida del agente con tools se demora
   más. El webhook responde `200` con TwiML vacío de inmediato y la respuesta real se
   manda aparte por la API REST desde un `BackgroundTasks`. Si esto se rompe, Twilio
   reintenta en silencio y llegan mensajes duplicados.
2. **El PDF y el español.** Registrar `DejaVuSans.ttf` explícitamente
   (`pdf.add_font('DejaVu', '', ruta, uni=True)`); las fuentes por defecto dañan las
   tildes y la ñ. Y aparte: `strftime('%B')` sigue el locale del sistema y en el
   contenedor sale en inglés — genera "24 de July de 2026". Los meses en español van en
   una constante.
3. **El match de medicamentos nunca es exacto.** Una fórmula escrita a mano dice
   "acetaminofen 500" y SISMED dice `ACETAMINOFÉN 500 MG TABLETA RECUBIERTA`. Se usa
   similitud por trigramas y se le devuelven al agente los candidatos **con su score**
   para que desambigüe o pregunte. No escoger el primero en silencio: un precio
   equivocado en una app de salud es el peor error posible aquí.

## Aviso legal

Curuba no da asesoría médica ni jurídica. La tutela que genera es un **borrador que
debe revisarse antes de radicarse**. Ese aviso va en el pie del PDF, en la respuesta de
WhatsApp y en la landing. No quitarlo.
