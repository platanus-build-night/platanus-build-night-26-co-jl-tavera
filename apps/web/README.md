# Curuba — Landing

La página pública. Explica qué hace Curuba y manda a la gente al WhatsApp. Es una sola
página: no hay login, ni dashboard, ni backend propio — todo el producto vive en el chat.

> **Estado: escrita y desplegada.** La página vive en `app/page.tsx` y corre en Railway
> como el servicio `curuba-web`. Lo que sigue es el spec con el que se escribió: las
> cifras, el copy y los ejemplos de chat están resueltos acá abajo.
>
> **La landing no depende de la API.** No la consume, no le pega a Postgres, no tiene
> variables de servidor: el único llamado a la acción es un enlace `wa.me`. Por eso se pudo
> terminar y desplegar antes que las tools del agente.

## Stack

Next.js (App Router) + Tailwind, desplegado en **Railway**. Todo estático: no hay fetch en
runtime, así que la página se prerenderiza completa.

## Estructura

```
apps/web/
├── package.json
├── next.config.ts
├── railway.json           # builder, start command con -p $PORT, watchPatterns
├── .env.local
├── public/
│   └── project-logo.png   # copiado de la raíz del repo — ver "Marca y assets"
└── app/
    ├── layout.tsx      # metadata, og:image, favicon, fuente
    ├── page.tsx        # la landing entera
    ├── globals.css     # Tailwind
    └── demo/           # el panel de tarima — ver "El panel de /demo"
        ├── page.tsx    # EventSource, celular, burbujas
        └── grafo.tsx   # el mapa del agente en SVG
```

**La landing es una sola `page.tsx`.** Los tres chats de ejemplo y las tres cifras van
como arrays de datos dentro del archivo, no como componentes en archivos sueltos. Es la
misma regla que sigue la API —*antes de crear uno nuevo, extender el que ya existe*— y sin
decirlo esto termina en ocho componentes para una página que se lee en 40 segundos.

## El panel de /demo

Una segunda ruta, para proyectar en la sustentación: a la izquierda (3/4) el mapa del
agente prendiéndose tool por tool mientras corre, a la derecha (1/4) un celular con la
conversación real apareciendo en vivo —foto de la fórmula y PDF incluidos—. **Los datos son
de verdad**: sale todo de la corrida que atiende el webhook de Twilio.

Se conecta por un solo `EventSource` a `GET /demo/eventos` de la API, que la alimenta con
`event_stream_handler` de Pydantic AI. El contrato de eventos y la red de seguridad están
en `apps/api/src/curuba/demo.py`.

Cuatro cosas que hay que saber antes de tocarla:

- **Es el único `"use client"` del proyecto**, y rompe a propósito el presupuesto técnico de
  `DESIGN.md` §10 ("la página no manda JavaScript de aplicación"). Ese presupuesto es de la
  landing y sigue en pie: `/` compila `○ (Static)`. Una pantalla que pinta una corrida en
  vivo no puede existir sin estado — esta es la conversación que el doc pedía tener.
- **Solo muestra una conversación**, la de `CURUBA_DEMO_WA` en la API. Es una allowlist de
  verdad, no un filtro de presentación: el descarte va en el emisor, así que la
  conversación de otro paciente no entra al stream ni le queda la foto guardada.
- **`NEXT_PUBLIC_API_URL`** es lo único nuevo que hay que poner en Railway. Sin ella cae a
  `http://localhost:8000`, que es lo que se quiere en local.
- **El marco del celular está duplicado**, no extraído de `page.tsx`. Sacarlo a un archivo
  compartido obligaba a cambiarle la API a la landing —que ya está desplegada— por 30
  líneas. Si se toca el marco de un lado, mirar el otro.

El grafo son coordenadas a mano en `grafo.tsx` (`NODOS`) y el SVG de las aristas va con
`preserveAspectRatio="none"` para que se estire exactamente como los porcentajes de las
cajas HTML; el grosor del trazo se salva con `vectorEffect="non-scaling-stroke"`. Con
proporción fija el grafo se recortaba unos píxeles arriba y abajo en cuanto la ventana no
daba la proporción exacta. `RIO_ABAJO` es la única fuente de la topología: qué prende cada
tool río abajo, y de ahí salen las aristas y los estados.

## Secciones de la página

```
┌────────────────────────────────┐
│  Hero: logo, nombre, línea, CTA│
├────────────────────────────────┤
│  90 %   57,3 %   312.500       │
├────────────────────────────────┤
│  ① fórmula → qué pagas         │
│  ② ¿desabastecido?             │
│  ③ el escrito que procede      │
├────────────────────────────────┤
│  De dónde salen los datos      │
├────────────────────────────────┤
│  Aviso legal                   │
└────────────────────────────────┘
```

### 1. Hero

Logo, nombre, una línea y el botón de WhatsApp. **El botón es lo único que importa arriba
del fold.**

| Pieza | Texto |
|---|---|
| Título | **Reducimos el gasto de bolsillo de los colombianos en medicamentos.** *Gratis, por WhatsApp.* |
| Subtítulo | ¿Cuánto debería costar tu medicamento? ¿Y qué hacer si tu EPS no te lo entrega? Manda una foto de tu fórmula o del producto: te decimos si te toca pagarlo y cuánto, si está desabastecido, y te armamos el reclamo listo para radicar. Gratis. |
| Botón | Escríbele por WhatsApp |

**El título vende el resultado, no la utilidad.** La versión anterior era *"Averigua cuánto
debería costar tu fórmula"* — una función, y encima la segunda: lo primero que hace Curuba
es mirar si el medicamento está financiado con la UPC, porque si lo está el paciente no
paga nada. Reducir el gasto de bolsillo es lo que sale de las tres funciones juntas, y es
lo que el research sostiene ([+57,3 % entre 2022 y
2025](../../resources/docs/RESEARCH.md#el-paciente-termina-pagando)).

*Gratis, por WhatsApp* va **dentro del `<h1>`**, en un `<span>` a `0.46em`: es el mismo
titular dicho en dos alturas. Como elemento aparte competía con el eyebrow que ya está
arriba. Y sí, "Gratis" se repite en el subtítulo — a propósito: es la objeción, y en una
landing la objeción se mata dos veces.

> El título creció de 41 a 66 caracteres, así que la caja se reajustó: `max-w-[14ch]` →
> `max-w-[19ch]` y `clamp(2.4rem,5vw,4.5rem)` → `clamp(2.1rem,4.4vw,3.6rem)`. Si se vuelve
> a tocar el copy del `<h1>`, hay que volver a mirar esos dos números o el hero se sale del
> `100svh` en escritorio.

> Una versión aún más vieja de este spec proponía *"Sabé cuánto debería costar tu
> fórmula"*. Se descartó: el imperativo voseo es válido en Antioquia pero ajeno para un
> paciente en Vichada, y el resto del producto tutea. Queda anotado por si se quiere volver
> atrás, pero que sea una decisión y no un descuido.

El subtítulo **ya no es el oneliner literal** de
[`build-night-project.json`](../../build-night-project.json): el oneliner tiene que ser una
sola frase autocontenida para el jurado y acá manda la pregunta que se hace el paciente.
Los dos dicen lo mismo y hay que moverlos juntos, pero no son la misma cadena. El oneliner
tal cual sí va en la `description` y el `og:description` de `layout.tsx`.

### 2. Banda de cifras

Tres números con la fuente al pie de la banda. No es una tabla: son tres cifras grandes y
una línea de atribución.

**Una cifra por sección del research**, en ese orden: el sistema no entrega, el paciente
termina pagando, y termina en un juzgado. La del medio es la que sostiene el titular, y por
eso desplazó al 74,3 % de concesión que estaba antes en el tercer slot.

| Cifra | Rótulo |
|---|---|
| **90 %** | de los pacientes no recibe sus medicamentos, o los recibe a medias y con demoras |
| **57,3 %** | creció el gasto de bolsillo en salud entre 2022 y 2025 — 61,7 % en zonas rurales |
| **312.500** | tutelas en salud en 2025 (+17,8 % frente a 2024) |

Atribución: *Defensoría del Pueblo, 2025 — encuesta en puntos de dispensación (n=3.449) ·
Afidro / Algebra Labs sobre datos DANE.* La segunda fuente no es opcional: el 57,3 % no es
de la Defensoría y acreditarlo mal es peor que no ponerlo. Todas las fuentes en
`resources/docs/RESEARCH.md`.

**Los dos detalles chiquitos no son decoración.** El `n=3.449` es lo que separa una
encuesta de un titular. Y el `+17,8 %` es a propósito: la prensa titula **+17,92 %**
porque compara contra una base redondeada de 265.000; contra el 265.173 de la serie el
aumento es 17,8 %. La investigación ya sostiene esa precisión —
[ver la nota](../../resources/docs/RESEARCH.md#y-termina-en-un-juzgado) — y la landing no la
puede aflojar.

### 3. Las tres funciones

Una tarjeta por función, cada una con un intercambio real de WhatsApp. **Los ejemplos
convencen más que la descripción.** Van literales del [README raíz](../../README.md#las-tres-funciones):

**① Fórmula → qué pagas**

> **Tú:** _[foto de una fórmula]_
> **Curuba:** Leí 3 medicamentos. El losartán y el acetaminofén están **financiados con la
> UPC**: los reclamas en el dispensador de tu EPS pagando solo la cuota moderadora, no los
> compras. El omeprazol no aparece en el listado — confírmalo con tu EPS antes de pagarlo.
> Si te toca comprarlo, el techo regulado del canal institucional es:
> • Omeprazol 20 mg — sólido oral x 14 → $6.100 la presentación

**La tarjeta empieza por la cobertura y no por el precio, y ese orden es el argumento.**
Es el mismo del agente (`agent.py`, sección *El orden en que consultas*): enrutar bien
ahorra ~100 %, comparar precios ahorra 20–40 %. Una tarjeta que abre con tres precios está
vendiendo la función menos valiosa de las dos y mandando a comprar lo que ya estaba pago.

Las cifras del ejemplo son ilustrativas y **la página tiene que decirlo**, en letra chica
debajo de la tarjeta: la cobertura sale del PBS y el techo del corte de SISMED, por
presentación y no por unidad.

**② ¿Está desabastecido?**

> **Tú:** ¿el losartán está desabastecido?
> **Curuba:** El INVIMA lo tiene en seguimiento con estado *desabastecido* desde el último
> corte. Si en tu droguería no lo consiguen, tu EPS sigue obligada a garantizarte el
> tratamiento — puede ser con otra presentación o por otro proveedor.

Igual: intercambio ilustrativo, el estado real es el del corte cargado. Y vale la pena
decir para qué sirve la función, que no es obvio: **define si el problema es del país o es
de tu EPS.**

**③ El escrito que procede → PDF**

**No es "tutela → PDF" y ese es el punto.** Son cuatro escritos —derecho de petición,
acción de tutela, incidente de desacato y demanda ante la función jurisdiccional de la
Supersalud— y cuál procede lo decide `legal.decidir_ruta()` en Python, nunca el modelo.
Generar el PDF es lo fácil; escoger el mecanismo es lo que cuesta semanas cuando se hace
mal. Una tarjeta que solo dice "tutela" está vendiendo una plantilla descargable.

El intercambio va literal de una corrida real del agente
([README raíz](../../README.md#3-la-ruta-legal)) porque **pide una tutela y recibe otra
cosa** — que es exactamente la demostración:

> **Tú:** llevo tres semanas yendo a la farmacia y no me entregan el losartán, quiero poner
> una tutela ya
> **Curuba:** Si no recibes el losartán ya, ¿corre riesgo tu vida o tu salud de forma grave?
> **Tú:** no, es para la tensión. no he radicado nada
> **Curuba:** Entonces lo que procede es un **derecho de petición** ante tu EPS, no la
> tutela: como todavía no le has pedido nada por escrito, este es el paso que toca primero
> y deja el radicado con fecha que sostiene la tutela después.
> **Curuba:** Aquí está tu derecho de petición 📎 La ley le da a la EPS 15 días hábiles; si
> no responde, ya con esa constancia sí procede la tutela.

Cinco burbujas, las mismas que tenía la versión anterior: la tarjeta no cambia de alto.

Una línea de apoyo con las normas de los dos escalones que aparecen en el chat: Ley 1755 de
2015, art. 14 (los 15 días hábiles) · art. 86 C.P. · Decreto 2591 de 1991.

### 4. De dónde salen los datos

Esto es lo que hace creíbles los precios; **no esconderlo en un pie de página.**

Van **en el orden en que las consulta el agente**, no por tamaño: primero si te toca
pagarlo, después cuánto, después si lo vas a conseguir.

| Fuente | Qué aporta | Corte | Tamaño |
|---|---|---|---|
| **PBS** (Resolución 2808 de 2022) | Qué está financiado con la UPC — o sea qué no te toca pagar | 2026-07-24 | 2.067 medicamentos |
| **SISMED** (MinSalud / SISPRO) | Techos de precio de la Circular CNPMDM | 2026-07-24 | 38.731 medicamentos |
| **INVIMA** | Estado de seguimiento de abastecimiento | mayo 2026 | 783 medicamentos |

El grid de esta sección y el de las precisiones son `sm:grid-cols-2 lg:grid-cols-3`: a `sm`
quedan 2+1 y a `lg` los tres en línea. Es la misma tarjeta de antes, solo que ahora son
tres — si vuelve a entrar una cuarta fuente hay que decidir el layout, no dejarla caer.

Con enlace a [`resources/data/README.md`](../../resources/data/README.md) —columnas, cortes y trampas de
parseo— y a [`resources/docs/RESEARCH.md`](../../resources/docs/RESEARCH.md), que rastrea cada cifra
hasta su fuente.

### 5. Aviso legal

Visible, no en letra chiquita. Ver abajo.

## Las tres precisiones que la página no puede perder

Son las tres cosas que el repo entero se esfuerza en sostener y que una landing tiende a
suavizar sin darse cuenta. Van con su porqué para que no se pierdan al redactar el JSX.

**«No lo encontré» no es «no está cubierto».** Es la regla nº 1 del prompt del agente
(`agent.py`, *Lo que no puedes decir nunca*) y por eso va de primera. El listado del PBS no
es exhaustivo y el cruce por principio activo con SISMED solo alcanza el 72,5 %: que un
medicamento no aparezca significa "no lo encontré", nunca "no está cubierto". El falso
negativo manda a alguien a pagar de su bolsillo algo que le correspondía —
[la advertencia completa](../../resources/docs/RESEARCH.md#pbs--cobertura-con-cargo-a-la-upc).
La página lo dice en una tarjeta propia porque es el único error de los tres que cuesta
plata en la dirección contraria a la que promete el titular.

**El precio es del canal institucional, no del mostrador.** El CSV del SISMED trae tres
columnas de precio, y la que le interesaría al paciente —el precio máximo de venta **final
al público**— viene con valor en **4 filas de 38.731**; en el resto dice `No regulado`. El
institucional, en cambio, viene en las 38.731. Así que la página **no puede prometer
"esto es lo que vas a pagar en la droguería"**: dice cuál es el techo regulado del canal
institucional, que sirve de referencia para saber si lo que están pidiendo está fuera de
rango. Es menos vendedor y es lo único honesto. El detalle está en
[`resources/data/README.md`](../../resources/data/README.md#sorpresa-2-el-precio-que-le-importa-al-paciente-casi-nunca-está-regulado).

**"No desabastecido" no es lo mismo que "no aparece".** El corte de mayo 2026 trae 783
medicamentos en cuatro estados:

| Estado | Medicamentos |
|---|---|
| En monitorización | 389 |
| No desabastecido *(seguimiento cerrado)* | 373 |
| Desabastecido | 11 |
| En riesgo de desabastecimiento | 9 |

Al primero el INVIMA sí le hizo seguimiento y lo cerró; al que no aparece nunca lo miró.
Son casi la mitad de las filas y la diferencia importa: que el INVIMA no tenga un
medicamento en seguimiento no significa que haya stock en tu barrio.

## Marca y assets

La paleta sale del logo (`project-logo.png`, en la raíz del repo): verde bosque para
contornos y texto, amarillo curuba para el fondo cálido, naranja de la pulpa para el
acento, verde hoja para el CTA — que además es el verde con el que la gente asocia
WhatsApp, y eso acá juega a favor.

**Hay que copiar `project-logo.png` a `apps/web/public/`.** Railway construye con el Root
Directory en `apps/web` y no ve la raíz del repo, así que un `../../project-logo.png`
falla en el build aunque funcione en local. De ahí salen el favicon y el `og:image`.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `NEXT_PUBLIC_WHATSAPP_URL` | El enlace `wa.me` con el número y un texto prellenado |
| `NEXT_PUBLIC_SITE_URL` | El dominio público, para que el `og:image` sea absoluto |
| `NEXT_PUBLIC_API_URL` | La API, **solo para `/demo`**. En local cae a `http://localhost:8000` |

```
NEXT_PUBLIC_WHATSAPP_URL=https://wa.me/12603057633?text=Hola%20Curuba
NEXT_PUBLIC_SITE_URL=https://<dominio-de-railway>
NEXT_PUBLIC_API_URL=https://<dominio-de-la-api>
```

El número no va hardcodeado en el JSX: durante el hackathon puede cambiar, y teniéndolo en
el entorno se cambia sin editar código. El valor sale de `TWILIO_WHATSAPP_FROM` en
`apps/api/.env.example` — **solo el número**: ese archivo tiene credenciales reales al lado
y nada más de ahí entra a este repo público.

> ⚠️ **`NEXT_PUBLIC_*` se hornea en el build, no se lee en runtime.** La página se
> prerenderiza entera, así que el valor queda escrito adentro del HTML. Cambiar la variable
> en Railway y reiniciar **no cambia nada**: hay que redesplegar. (Esto es de Next, no de
> Railway; en Vercel era igual.)

`NEXT_PUBLIC_SITE_URL` es opcional en local — `layout.tsx` cae a `RAILWAY_PUBLIC_DOMAIN` y,
si tampoco está, a `http://localhost:3000`. En producción **no** es opcional: si al momento
de compilar no hay ninguna de las dos, el `og:image` queda apuntando a `localhost` y
WhatsApp no muestra la tarjeta al compartir el enlace.

**Ningún secreto lleva prefijo `NEXT_PUBLIC_`.** Termina en el HTML público. La landing no
necesita credenciales de ningún tipo.

**El texto prellenado no es cosmético.** Meta rechaza los mensajes salientes con **error
63016** si el número no le ha escrito al sender en las últimas 24 horas. Que el usuario
mande el primer mensaje es justamente lo que abre esa ventana, así que el enlace tiene que
traer el texto listo para que solo tenga que darle enviar.

## Cómo correrlo

```bash
cd apps/web
npm install
npm run dev
```

La landing no necesita la API corriendo, ni Postgres, ni túnel. **`/demo` sí necesita la
API** (`uvicorn` en el 8000) con `CURUBA_DEMO_WA` y `PUBLIC_BASE_URL` puestas; para moverlo
sin Twilio, se le manda un POST form-encoded al webhook y el panel se mueve igual — está
explicado en el `CLAUDE.md` de la raíz.

## Deploy en Railway

La landing es un servicio más del mismo proyecto de Railway donde ya viven la API y
Postgres: **`curuba-web`**. Un solo panel, un solo `git push`, un solo lugar donde mirar
logs.

**Railway no se puede conectar a este repo.** Es de la organización `platanus-build-night`
y las plataformas de deploy solo acceden a repos propios. El espejo ya existe:
**`jl-tavera/curuba-platanus`**, y `origin` tiene dos push URLs, así que un solo `git push`
actualiza los dos. La receta completa —y el hook `pre-push` que aborta si falta alguno de
los dos remotos— está en [`CLAUDE.md`](../../CLAUDE.md) y en
[`DEPLOYMENT.md`](../../resources/docs/DEPLOYMENT.md).

Dos ajustes en *Settings*, y **el segundo no hereda del primero**:

| Ajuste | Valor |
|---|---|
| Root Directory | `apps/web` |
| Config file path | `apps/web/railway.json` |

Lo demás lo pone `railway.json`: builder `RAILPACK`, healthcheck en `/`, `watchPatterns`
para que un cambio en `apps/api` no reconstruya esto, y el start command con **`-p $PORT`**
—sin eso `next start` se queda en el 3000 y el healthcheck falla con el deploy en verde—.

El detalle completo, incluido el orden obligatorio *crear → generar dominio → redesplegar*,
está en [`DEPLOYMENT.md`](../../resources/docs/DEPLOYMENT.md#servicio-de-la-landing).

Antes de gastar un ciclo de deploy conviene probar el build en local, que es el mismo que
corre Railway:

```bash
npm run build && npm start
```

## Aviso legal

El aviso tiene que aparecer **en la página**, no solo en el repo:

> Curuba no da asesoría médica ni jurídica. Los precios son techos regulados del SISMED
> para el canal institucional, no lo que cobra un punto de venta. El estado de
> desabastecimiento es el del último corte publicado por el INVIMA y puede haber cambiado.
> Que un medicamento no aparezca en el listado del PBS no significa que no esté cubierto.
> Los escritos legales que genera son **borradores que deben revisarse antes de
> radicarse**.
