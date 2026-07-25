# Desplegar Curuba

Cómo se pone en pie el número de WhatsApp y la landing: los dos repos, Railway, Twilio y el
orden en que conviene probar. Cada sección marcada con ⚠️ es una trampa que ya costó tiempo
una vez — están escritas para no volver a pagarlas.

Todo vive en un solo proyecto de Railway: **`curuba-platanus`** (la API), **`curuba-web`**
(la landing) y **`Postgres`**.

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

### Variables de la API

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

### Cuando el arranque falla en `db.abrir()`

El síntoma: el contenedor arranca, muere en el `lifespan` y vuelve a arrancar, en bucle.

```
File "/app/src/curuba/main.py", line 24, in _ciclo
    await db.abrir()
OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0),
                              [Errno 111] Connect call failed ('127.0.0.1', 5432)
ERROR:    Application startup failed. Exiting.
```

> ⚠️ **`127.0.0.1` no significa que Postgres esté caído: significa que `DATABASE_URL`
> llegó vacía.** Ese es *localhost dentro del contenedor de la API*, donde nunca hubo una
> base. asyncpg con un DSN vacío no se queja: lo ignora, cae a los defaults de libpq y
> termina marcando a `localhost:5432`. Si la variable tuviera la URL privada, el host del
> error sería `postgres.railway.internal`; si tuviera basura, el error sería de parseo
> del DSN, no de conexión.

Las cuatro formas de que falte, en orden de qué tan fácil es no verlas:

| Qué pasó | Cómo se detecta |
|---|---|
| **No existe el servicio de Postgres** | `railway service list` devuelve un solo servicio. Fue lo que pasó la primera vez |
| Nunca se agregó a la API (se agregó solo al Postgres, o a nada) | `DATABASE_URL` no aparece en `variable list` |
| La referencia trae el nombre equivocado del servicio | Aparece vacía — Railway **no marca error** por una referencia que no resuelve |
| Se agregó en otro *environment* | Aparece en `staging` pero no en `production` |

> ⚠️ **La primera fila fue la de verdad y no se parece a un problema de base de datos.**
> El proyecto tenía la API desplegándose, con su Root Directory, su `railway.json` y todas
> las variables de OpenRouter y Twilio bien puestas — y **cero bases de datos**. El paso
> *+ New → Database → PostgreSQL* de esta misma sección se saltó, y como el error que sale
> es de conexión rechazada, se lee como «Postgres está caído» en vez de «Postgres no
> existe». Primer comando ante este traceback: `railway service list`.

Detrás de las otras tres hay un solo hecho: **Railway no comparte variables entre
servicios.** Que el Postgres esté en el mismo proyecto no le pone `DATABASE_URL` a la API;
hay que declararla en las variables **del servicio de la API**, como sale arriba. Y la
referencia lleva el **nombre exacto** del servicio: si quedó como `postgres` en minúscula o
`Postgres-abc123`, se resuelve a nada y el deploy falla igual que si nunca se hubiera
puesto.

Para diagnosticar y arreglar desde el CLI:

```bash
railway service list --json                       # el nombre EXACTO del Postgres
railway variable list --service <api> --json      # ¿está? ¿resuelta o vacía?
railway variable set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' --service <api>
```

Las comillas simples no son opcionales: sin ellas el shell se come las llaves.

> **Un error repetido en los logs es un solo fallo.** `railway.json` trae
> `restartPolicyType: ON_FAILURE`, así que el mismo traceback sale una vez por reinicio.
> Ver tres copias no quiere decir que hayan pasado tres cosas distintas.

Desde el commit que agregó la guarda, `db.abrir()` revienta antes de llegar a asyncpg con
un mensaje que dice cuál variable falta, precedido en los logs por
`no se pudo abrir Postgres — revisar DATABASE_URL y las extensiones`. Si en vez de eso
sale el traceback de `CREATE EXTENSION`, el problema es otro: son `pg_trgm`/`unaccent`, y
eso está descrito arriba en *Postgres*.

### Servicio de la landing

**La landing también va en Railway, no en Vercel.** Es un servicio más del mismo proyecto,
desplegado del mismo espejo y con el mismo `git push`: un solo panel, un solo lugar donde
mirar logs. Es una página estática que no le pega a la API ni a Postgres — el único llamado
a la acción es un enlace `wa.me`.

*+ New → GitHub Repo →* **`jl-tavera/curuba-platanus`**, el mismo de la API. Después, en
*Settings*:

| Ajuste | Valor |
|---|---|
| Nombre | `curuba-web` |
| Root Directory | `apps/web` |
| **Config file path** | `apps/web/railway.json` |

Aplica la misma ⚠️ de la API: **son dos ajustes distintos y el segundo no hereda del
primero**.

#### Cómo se hace lo mismo por CLI

El CLI **no expone** Root Directory ni Config file path: no hay bandera en `railway add` ni
en `railway service source connect`. Se ponen por GraphQL, que sí está en el CLI. El
servicio se crea vacío, se configura y **solo al final** se le conecta el repo, para que el
primer build ya salga con la config buena en vez de fallar y tener que redesplegar:

```bash
railway add --service curuba-web \
  --variables 'NEXT_PUBLIC_WHATSAPP_URL=https://wa.me/12603057633?text=Hola%20Curuba' --json

railway api 'mutation($s: String!, $e: String!, $i: ServiceInstanceUpdateInput!) {
    serviceInstanceUpdate(serviceId: $s, environmentId: $e, input: $i) }' \
  --variables '{"s":"<serviceId>","e":"<environmentId>",
                "i":{"rootDirectory":"apps/web","railwayConfigFile":"apps/web/railway.json"}}'

railway service source connect --repo jl-tavera/curuba-platanus --branch main --service curuba-web
```

Los IDs salen de `railway service list --json` y de `railway status --json`.

> ⚠️ **`serviceInstance` no muestra lo que dice el `railway.json`.** Consultarlo devuelve
> `healthcheckPath: null`, `startCommand: null`, `watchPatterns: []` y un `builder` que
> puede no ser el del archivo — y **eso es normal**: esa query lee solo la capa del
> dashboard. Lo del archivo se mezcla al desplegar y aparece en el `fileServiceManifest` del
> deployment. Leer `serviceInstance` y concluir "no quedó configurado" es un falso positivo;
> el único lugar donde se comprueba es un deployment terminal:
>
> ```bash
> railway deployment list --service curuba-web --limit 1 --json   # → meta.fileServiceManifest
> ```
>
> Corolario: `railwayConfigFile` sale `null` en `curuba-platanus` y aun así su deploy trae
> `configFile: /apps/api/railway.json`. Railway encuentra el `railway.json` que está dentro
> del Root Directory por su cuenta. Ponerlo explícito igual no sobra — no cuesta nada y
> quita la ambigüedad.

`apps/web/railway.json` usa **`RAILPACK`**, no `NIXPACKS`. Railpack es el builder actual de
Railway y Nixpacks está marcado como legacy; la API se quedó en Nixpacks porque ya
funcionaba y no se cambia un builder a mitad de camino. Que los dos servicios usen builders
distintos es deliberado.

El `startCommand` lleva `-p $PORT`:

```
npm run start -- -p $PORT -H 0.0.0.0
```

> ⚠️ **Sin `-p $PORT` el deploy sale `SUCCESS` y el healthcheck igual falla.** `next start`
> se pega al 3000 y Railway le habla al puerto que él asignó. El contenedor está vivo y el
> proceso corriendo; simplemente nadie lo escucha donde toca. Se lee como *Application
> failed to respond*, que parece un crash y no lo es.

### Variables de la landing

```
NEXT_PUBLIC_WHATSAPP_URL=https://wa.me/12603057633?text=Hola%20Curuba
NEXT_PUBLIC_SITE_URL=https://<dominio-generado>     ← después de generar el dominio
```

Y nada más. **Ningún secreto lleva prefijo `NEXT_PUBLIC_`**: esa variable termina escrita
en el HTML público. La landing no necesita `DATABASE_URL`, ni la llave de OpenRouter, ni el
token de Twilio.

> ⚠️ **Las `NEXT_PUBLIC_*` se hornean en el build, no se leen en runtime.** La página se
> prerenderiza entera, así que el valor queda adentro del HTML. Cambiar la variable y
> reiniciar **no cambia nada**: hay que **redesplegar**. (Esto es de Next, no de Railway —
> en Vercel pasaba igual.)

De ahí sale el orden obligatorio, que no es el intuitivo:

1. Crear el servicio y poner `NEXT_PUBLIC_WHATSAPP_URL`.
2. *Settings → Networking → **Generate Domain*** (o `railway domain --service curuba-web`).
3. Poner `NEXT_PUBLIC_SITE_URL` con ese dominio.
4. **Redesplegar**, para que los pasos 2 y 3 entren al build.

> **Generar el dominio dispara un redeploy solo.** Ese build ya trae `RAILWAY_PUBLIC_DOMAIN`,
> así que el `og:image` sale bien incluso antes del paso 4 — el fallback de `layout.tsx`
> hace su trabajo. No sirve de excusa para saltarse el redeploy: `NEXT_PUBLIC_SITE_URL` se
> pone *después* de generar el dominio y esa sí necesita su propio build. Y en cambio poner
> una variable **no** dispara nada: hay que pedir el redeploy a mano.

Saltarse el paso 4 tiene un síntoma silencioso: `layout.tsx` arma el `metadataBase` con
`NEXT_PUBLIC_SITE_URL` y, si falta, con `RAILWAY_PUBLIC_DOMAIN` — que **no existe hasta que
el servicio tiene dominio**. Si ninguna de las dos está al momento de compilar, el
`og:image` queda apuntando a `http://localhost:3000` y **WhatsApp no muestra la tarjeta**,
que es justo el canal por el que se comparte esta página. La página se ve perfecta; lo que
falla es el preview.

Verificación, que es lo único que prueba que la variable entró al build:

```bash
curl -sI https://<dominio-web>/ | head -1                       # 200
curl -s https://<dominio-web>/ | grep -o 'wa\.me[^"]*' | head -1
curl -s https://<dominio-web>/ | grep -o '<meta property="og:image"[^>]*>'
```

### Un solo repo, dos servicios

Los dos `railway.json` traen `watchPatterns` (`apps/api/**` y `apps/web/**`) para que un
cambio en la landing no reconstruya la API y al revés.

**Los globs se evalúan contra la raíz del repo, no contra el Root Directory** — la duda que
dejó la doc de Railway quedó resuelta en el estreno de `curuba-web` (25-07-2026). El commit
`a20b610e` tocó solo `apps/api/**` y `resources/**`, con `apps/api/**` ya activo en la API
desde el build anterior, y la API se desplegó. Si los globs fueran relativos al Root
Directory, el archivo cambiado se habría leído como `src/curuba/agent.py`, `apps/api/**` no
habría matcheado nunca y **no habría salido ningún deploy**. Salió: los patrones de los dos
`railway.json` son correctos como están escritos.

Lo que todavía no se probó es el lado negativo — que un push que toca solo `apps/web/**`
efectivamente *no* reconstruya la API. Es el caso barato de equivocarse (un deploy de más),
no el caro.

> ⚠️ **Si después de un push no se despliega *nada*, es esto igual.** El arreglo es quitar
> `watchPatterns` de los dos archivos: un deploy de más es barato, un deploy que nunca sale
> en medio de una demo no.

### Cuánto cuesta esto

El plan **Hobby** son **USD 5/mes que son a la vez el crédito de consumo**: pagas 5 y
gastas contra esos 5, y si te pasas te cobran solo el delta encima. Tarifas: USD 10/GB de
RAM al mes, USD 20/vCPU al mes, USD 0,05/GB de egress.

Los topes del plan no aprietan (48 GB de RAM y 48 vCPU **por servicio**; el límite de 5
servicios por proyecto es del plan *Trial*, no del Hobby). Lo que aprieta es el crédito:

| Servicio | RAM típica | Costo/mes 24/7 |
|---|---|---|
| `curuba-platanus` | ~300–400 MB | ~USD 3,5–4 |
| `curuba-web` | ~120–180 MB | ~USD 1,3–1,9 |
| `Postgres` | ~80–150 MB | ~USD 1 |
| | | **~USD 6–9** |

Railway factura por segundo, así que **durante el hackathon esto no importa**: cinco días
con todo prendido son ~USD 1–1,5. El sobrecosto solo aparece si el proyecto sigue corriendo
el mes completo.

> **Cuando termine el evento**, prender *Settings → Serverless / App Sleeping* en
> `curuba-web` y `curuba-platanus` deja de facturar CPU y RAM mientras no haya tráfico, y el
> proyecto vuelve a caber en los USD 5. No se prende antes: la primera visita después de un
> rato paga un arranque en frío de varios segundos, y esa visita puede ser la de un juez.

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

La landing va por su cuenta y no depende de ninguno de esos pasos. Antes de gastar un ciclo
de deploy, `cd apps/web && npm run build && npm start` — si el build no pasa en local,
tampoco va a pasar en Railway. Ya desplegada, la prueba que cierra el círculo no es el
`curl`: es **pegar el enlace en un chat de WhatsApp y ver que salga la tarjeta con el
logo**. Eso es lo único que confirma que el `metadataBase` quedó apuntando al dominio de
Railway y no a `localhost`.

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
