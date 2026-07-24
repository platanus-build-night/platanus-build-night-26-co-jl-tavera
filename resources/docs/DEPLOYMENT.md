# Desplegar Curuba

Cómo se pone en pie el número de WhatsApp: los dos repos, Railway, Twilio y el orden en
que conviene probar. Cada sección marcada con ⚠️ es una trampa que ya costó tiempo una vez
— están escritas para no volver a pagarlas.

---

## 1. Los dos repos

Railway solo se conecta a repos que tú seas dueño, y este vive en la organización
`platanus-build-night`. La solución es un espejo privado y un `origin` con **dos push
URLs**: un solo `git push` actualiza los dos.

```
~/Dev/projects/hackathons/
├── platanus-build-night-26-co-jl-tavera/   ← se trabaja AQUÍ
│      git push ──┬──> platanus-build-night/…      (repo del jurado)
│                 └──> jl-tavera/curuba-platanus   (de aquí despliega Railway)
└── curuba-platanus/                        ← copia de solo lectura
```

Si hay que rehacerlo (repo clonado de cero, `.git/config` perdido):

```bash
git remote set-url --add --push origin https://github.com/platanus-build-night/platanus-build-night-26-co-jl-tavera.git
git remote set-url --add --push origin https://github.com/jl-tavera/curuba-platanus.git
git remote get-url --push --all origin   # deben salir los dos
```

> ⚠️ **El orden no es cosmético.** El **primer** `--add --push` *reemplaza* el default
> implícito (que era el URL de fetch). Si se agrega solo el espejo, el repo del jurado
> deja de recibir commits **en silencio** — y eso no se nota hasta que alguien va a
> calificar.

### El hook que lo vigila

Esa configuración vive en `.git/config`, que **no se commitea**. Si se pierde, el espejo
se queda atrás y Railway sigue desplegando código viejo sin un solo error. Por eso hay un
`.git/hooks/pre-push` que aborta si falta cualquiera de los dos remotos:

```
[pre-push] ABORTADO. Faltan push URLs en origin:
  - espejo curuba-platanus (de donde despliega Railway)
```

El hook tampoco se commitea. Si el repo se clona de nuevo, hay que rehacerlo junto con los
remotos.

### La copia de solo lectura

`../curuba-platanus` es un clon del espejo con el push inhabilitado a propósito
(`git remote set-url --push origin NO-PUSHEAR-DESDE-AQUI…`). **No se trabaja ahí:** si se
commitea, las historias divergen y el push desde la carpeta buena empieza a fallar. Para
actualizarla, `git pull` adentro.

---

## 2. Railway

### Servicio de la API

*New Project → Deploy from GitHub repo →* **`jl-tavera/curuba-platanus`** (el espejo, no
el de Platanus). Como es privado, hay que darle acceso explícito a ese repo cuando se
autoriza la GitHub App; si no aparece en la lista, es que no se concedió.

Después, en *Settings* del servicio:

| Ajuste | Valor |
|---|---|
| Root Directory | `apps/api` |
| **Config file path** | `apps/api/railway.json` |

> ⚠️ **Son dos ajustes distintos y el segundo no hereda del primero.** Los docs de Railway
> lo dicen explícito: *"The Railway Config File doesn't follow the Root Directory path."*
> Sin el segundo, Railway busca el `railway.json` en la raíz del repo, no lo encuentra, se
> inventa un start command y el deploy falla con un error que no menciona nada de esto.

### Postgres

*+ New → Database → PostgreSQL*, en el mismo proyecto.

No hay que correr migraciones a mano: `schema.sql` se aplica solo en el `lifespan` de
FastAPI en cada arranque, y es idempotente. Efecto secundario útil: si las extensiones
`pg_trgm`/`unaccent` no se dejan instalar, **el arranque falla y el healthcheck lo grita**,
en vez de descubrirlo al escribir la primera query de trigramas.

### Variables

```
DATABASE_URL=${{Postgres.DATABASE_URL}}      ← referencia, no pegar la URL
OPENROUTER_API_KEY=sk-or-v1-...
CURUBA_MODEL=openrouter:anthropic/claude-sonnet-5
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+12603057633
VALIDATE_TWILIO_SIGNATURE=false              ← ver §5
```

La sintaxis `${{Postgres.DATABASE_URL}}` es de Railway y tiene autocompletado en el
dashboard. Si el servicio de Postgres quedó con otro nombre, va ese.

Por último: *Settings → Networking → **Generate Domain***.

> **La URL privada vs. la pública.** Para correr algo contra la base **desde tu máquina**
> (por ejemplo el ETL) hace falta `DATABASE_PUBLIC_URL`, que está en las variables del
> servicio de Postgres. La `DATABASE_URL` privada solo resuelve dentro de Railway.

---

## 3. Twilio

En la página del WhatsApp Sender:

| Campo | Valor |
|---|---|
| Messaging service | **vacío** — ver abajo |
| Webhook URL for incoming messages | `https://<app>.up.railway.app/webhooks/twilio/whatsapp` |
| Webhook method | `HTTP Post` |
| Fallback URL | vacío |
| Status callback URL | vacío — el Debugger de Twilio da lo mismo sin escribir otro endpoint |
| TwiML Application | `None` — eso es WhatsApp *Calling*, no aplica a mensajes |

> ⚠️ **El Messaging Service puede ganarle al webhook del sender.** El comportamiento lo
> controla el flag `use_inbound_webhook_on_number`: por defecto el servicio hace *defer to
> sender's webhook*, pero si esa configuración cambia, los mensajes se van a otro lado
> mientras esta pantalla se ve perfectamente correcta. Dejándolo vacío no hay ambigüedad.

El dominio de Railway no existe hasta que se despliega, así que el orden es **deploy →
copiar URL → pegarla acá**, no al revés.

---

## 4. La ventana de 24 horas

Meta solo permite mensajes de texto libre dentro de las **24 h siguientes al último
mensaje del usuario**. Fuera de esa ventana hay que usar plantillas pre-aprobadas.

En la práctica: **antes de probar, hay que escribirle al número desde el celular de
prueba.** Si no, el envío falla con:

```
status = undelivered   error = 63016
```

El mensaje se generó bien y Twilio lo aceptó con `201 Created` — Meta lo bloqueó en la
última milla. Es el error que más parece un bug del código sin serlo.

> **El límite de 250 conversaciones no aplica.** Es sobre conversaciones **iniciadas por
> el negocio**, y Curuba siempre responde: el paciente escribe primero.

---

## 5. La firma del webhook

`VALIDATE_TWILIO_SIGNATURE` arranca en **`false`** y pasa a **`true`** apenas llegue el
primer WhatsApp. No es comodidad, es aislar variables: en el primer deploy pueden fallar
el build, el config path, Postgres o la URL del webhook, y un 403 de `RequestValidator` no
trae mensaje — no dice cuál de los cuatro es.

> ⚠️ **No dejarlo en `false`.** El webhook queda abierto: cualquiera que adivine la URL
> puede hacer correr el agente, quemando tokens de OpenRouter y mandando WhatsApps desde
> el número propio.

Al prenderla, si sale 403:

| Síntoma | Causa |
|---|---|
| 403 en **todos** los mensajes | El esquema de la URL. Detrás del proxy de Railway `request.url` reporta `http://` pero Twilio firmó la `https://`. Ya está resuelto en `_url_publica()` de `main.py` |
| 403 en **algunos** | Otra cosa — el `Auth Token` cambió, o un proxy raro |

---

## 6. Verificación en escalera

Cada paso aísla una falla distinta. **Los dos primeros no necesitan Railway ni que Twilio
llame**, así que se puede llegar lejos sin gastar un ciclo de deploy.

**1. El agente solo.** Necesita `OPENROUTER_API_KEY` y `DATABASE_URL`, nada de Twilio:

```bash
cd apps/api && PYTHONPATH=src uv run python -m curuba.agent
```

Un REPL en la terminal. Es donde conviene iterar el prompt.

**2. Un WhatsApp real, desde local.** Levantar `uvicorn` y simular lo que mandaría Twilio,
con **tu celular** en `From` (ahí llega la respuesta):

```bash
curl -X POST http://localhost:8000/webhooks/twilio/whatsapp \
  -d "From=whatsapp:%2B57XXXXXXXXXX" \
  -d "Body=hola, quien eres?"
```

> El `+` va como **`%2B`**. Si se manda pelado, el form lo interpreta como espacio y
> Twilio rechaza el número.

Esto ejercita agente + OpenRouter + envío REST de una sola vez. El `curl` debe responder
`<Response></Response>` al instante y el WhatsApp llegar unos segundos después.

**3. Deploy.** `git push` (va a los dos repos), variables cargadas, y
`GET https://<app>.up.railway.app/health` responde `{"ok": true}`.

**4. WhatsApp de verdad.** Apuntar el webhook de Twilio al dominio de Railway y escribirle
al número. Si no llega nada, el **Debugger de Twilio** dice si el webhook devolvió error o
se demoró.

**5. Cerrar la puerta.** `VALIDATE_TWILIO_SIGNATURE=true` y otro mensaje.

---

## Apéndice: por qué el webhook responde vacío

`main.py` contesta `<Response></Response>` de inmediato y corre el agente en un
`BackgroundTasks`. **Twilio corta el webhook a los ~15 s** y una corrida con tools se
demora más; si se contesta tarde, Twilio reintenta en silencio y al usuario le llegan
mensajes duplicados — y se rompe justo en la demo, que es cuando las respuestas son más
largas.

Dos detalles que acompañan a eso:

- El cliente REST de Twilio es **bloqueante**, así que el envío va en
  `anyio.to_thread.run_sync` para no congelar el event loop.
- La respuesta se corta a 1500 caracteres: Twilio rechaza cuerpos de más de **1600**
  (error 21617) y al usuario **no le llega nada**. Una respuesta de LLM los pasa sin
  esfuerzo.
