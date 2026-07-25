<img src="./project-logo.png" alt="Curuba" width="140" />

# Curuba

**Reducimos el gasto de bolsillo de los colombianos en medicamentos: por WhatsApp te
decimos si te toca pagarlo y cuánto, si está desabastecido, y te armamos el escrito legal
que procede.**

*A WhatsApp agent for Colombian patients: PBS coverage lookups, prescription pricing
against the regulated SISMED ceilings, INVIMA shortage status, and generated legal drafts
— petition, tutela, contempt motion or Supersalud claim, whichever actually applies.*

Platanus Build Night — Bogotá @ Buk · Hacker: Jose Luis Tavera ([@jl-tavera](https://github.com/jl-tavera))

**Pruébalo:** [escríbele por WhatsApp](https://wa.me/12603057633?text=Hola%20Curuba) — el
enlace trae el texto listo, y que el primer mensaje salga de ti es lo que abre la ventana
de 24 h de Meta. La landing está en
[curuba-web-production.up.railway.app](https://curuba-web-production.up.railway.app) y
[`/demo`](https://curuba-web-production.up.railway.app/demo) proyecta la corrida del agente
en vivo mientras alguien le escribe.

---

## El problema

El medicamento está formulado por un médico, está cubierto por el sistema y su entrega es
un derecho fundamental. Aun así, **9 de cada 10 pacientes no lo reciben, o lo reciben a
medias y con demoras.**

Cuando eso ocurre el paciente tiene tres caminos. Ninguno es navegable sin información que
hoy existe, es pública, y está en formatos que ningún paciente va a abrir:

- **Comprarlo de forma particular.** Antes de eso está la pregunta que casi nadie hace: si
  el medicamento está financiado con la UPC, no hay que comprarlo — se reclama en el
  dispensador de la EPS pagando solo la cuota moderadora, y eso está en el listado del PBS
  de la Resolución 2808 de 2022. Si de verdad le toca comprarlo, los precios máximos están
  regulados y publicados por el Ministerio de Salud en SISMED — en un CSV de 38.731 filas.
  Sin esas dos referencias el paciente no tiene contra qué comparar lo que le piden en el
  mostrador, ni cómo saber que no tenía que pagarlo.
- **Esperar a que llegue.** No tiene manera de distinguir si el medicamento está
  desabastecido en todo el país o si su EPS simplemente no está cumpliendo. Esa
  distinción define qué debe hacer después, y la respuesta está en un PDF mensual del
  INVIMA de 93 páginas, organizado por principio activo.
- **Reclamarlo por la vía legal.** Y acá no hay un camino, hay cuatro —derecho de
  petición, tutela, incidente de desacato y demanda ante la Supersalud— que no son
  intercambiables: cuál procede depende de si hay riesgo vital, de si ya se radicó algo,
  de si el problema es de entrega o de cobertura. Todos son gratuitos y ninguno requiere
  abogado, pero exigen entender los requisitos de procedibilidad y redactar un documento
  jurídico. Un escrito mal escogido o mal formulado no se pierde por falta de razón: se
  cae antes de que el juez mire el fondo.

**Curuba tiene tres funciones porque el paciente tiene tres caminos** — una por camino, en
el único canal que ya tiene abierto.

### Las cifras

El gasto de bolsillo en salud de los hogares creció **57,3 %** entre 2022 y 2025 —
**61,7 %** en zonas rurales contra 26,4 % en las ciudades. Detrás está el mismo hecho:
**90 %** de los pacientes encuestados en puntos de dispensación no recibió sus
medicamentos, o los recibió a medias y con demoras (n=3.449, Defensoría del Pueblo 2025),
y el **61 %** dijo que terminaría comprándolos de forma particular, lo que le cuesta entre
el **7 % y el 90 % de sus ingresos**. Y en 2025 se radicaron **312.500 tutelas en salud**,
un 17,8 % más que en 2024; el juez le da la razón al paciente el **74,3 %** de las veces.

Las cifras completas —la serie histórica desde 2020, el desglose por ingresos y por zona
rural, las causales que tumban una tutela— están en
[`resources/docs/RESEARCH.md`](resources/docs/RESEARCH.md), cada una con su fuente anotada.

## Las tres funciones

### 1. Fórmula → ¿te toca pagarlo? y ¿cuánto?

Le mandas una foto de la fórmula (o la escribes). Curuba extrae los medicamentos y, uno
por uno, mira **primero si el PBS lo financia con la UPC** — porque si lo financia el
paciente no tiene que comprarlo. Solo si le toca comprarlo entra el precio.

> **Tú:** _[foto de una fórmula]_
> **Curuba:** Leí 3 medicamentos. El losartán y el acetaminofén están **financiados con la
> UPC**: los reclamas en el dispensador de tu EPS pagando solo la cuota moderadora, no los
> compras. El omeprazol no aparece en el listado — confírmalo con tu EPS antes de pagarlo.
> Si te toca comprarlo, el techo regulado del canal institucional es:
> • Omeprazol 20 mg — sólido oral x 14 → $6.100 la presentación

*Las cifras del ejemplo son ilustrativas: la cobertura sale del PBS y el techo del corte de
SISMED, por presentación y no por unidad.*

**Ese orden es el producto.** Enrutar bien ahorra ~100 %; comparar precios ahorra 20–40 %.
Dar el precio de frente manda a alguien a gastarse $800.000 en un adalimumab que la EPS
tenía que ponerle, así que el orden no es una sugerencia del prompt: `precio_en_drogueria`
levanta `ModelRetry` si todavía no se consultó la cobertura.

Los nombres nunca coinciden exactamente —una fórmula a mano dice "acetaminofen 500" y
SISMED dice `ACETAMINOFÉN - Sólido - Oral`— así que la búsqueda es por similitud de
trigramas y, cuando hay duda, Curuba pregunta en vez de adivinar. Un precio equivocado en
una app de salud es peor que no dar precio.

**Y el paciente habla de marcas, no de principios activos.** Las tres bases están indexadas
por principio activo, así que "Dolex" o "Noxpirin" mueren en *no lo encontré*. Cuando el
nombre suena a marca, Curuba sale a buscarlo en la web, resuelve el principio activo y
**vuelve a consultar las tres bases él mismo** con el nombre bueno. Si la búsqueda no trae
fuentes, o el medicamento resulta ser de otro país, se reporta como no encontrado: las
marcas se repiten entre países con composiciones distintas.

**Qué precio es exactamente.** El techo de venta **final al público** viene con valor en 4
filas de 38.731; el del canal **institucional**, en las 38.731. Así que Curuba no dice
"esto es lo que deberías pagar en la droguería" —dice cuál es el techo regulado que sí
está respaldado. Es menos vendedor y es lo único honesto; el porqué está en
[`resources/data/README.md`](resources/data/README.md).

**El precio del mostrador, cuando lo preguntan, sale del catálogo y no de un buscador.**
Curuba le pega directo a los catálogos de Drogas La Rebaja y Farmatodo —~700 ms, y
contestan lo mismo dos veces seguidas—; solo si los dos vienen vacíos cae a una búsqueda
web. Y si no aparece precio en ninguna parte, dice dónde lo venden **sin cifra**: el techo
regulado no se usa como sustituto, que es justo la confusión que este proyecto no puede
sembrar.

### 2. Consulta de desabastecimiento

Le preguntas por un medicamento y te responde con el estado de seguimiento del INVIMA.

> **Tú:** ¿el losartán está desabastecido?
> **Curuba:** El INVIMA lo tiene en seguimiento con estado *desabastecido* desde el último
> corte. Si en tu droguería no lo consiguen, tu EPS sigue obligada a garantizarte el
> tratamiento — puede ser con otra presentación o por otro proveedor.

*Intercambio ilustrativo: el estado que devuelve Curuba es el que traiga el corte cargado
del INVIMA, no uno fijo por medicamento.*

Esta es la función que decide qué hacer después: **el problema es del país o es de tu
EPS.** Si el medicamento está desabastecido, el reclamo es por la alternativa terapéutica;
si no lo está, el incumplimiento es de la EPS y ahí la tutela tiene otro peso.

**Por eso el INVIMA no espera a que lo pregunten.** Viaja pegado a toda consulta de
medicamento, en paralelo y sin costar tiempo: quien escribe "¿me lo cubre la EPS?" no sabe
que el desabastecimiento se pregunta aparte, y es justo lo que le explica por qué no se lo
entregan. Lo que sí decide Python es si eso es noticia — un seguimiento cerrado no se
menciona, o Curuba estaría alarmando a alguien que solo preguntó un precio.

La clasificación del INVIMA tiene seis estados; el corte cargado (mayo 2026) trae **783
medicamentos** en cuatro de ellos —cerca de la mitad en monitorización y solo 11
efectivamente desabastecidos.

**Que un medicamento aparezca como *no desabastecido* no es lo mismo a que no aparezca.**
El primero fue objeto de seguimiento y se resolvió; al segundo el INVIMA nunca lo miró, y
que no lo tenga en seguimiento no significa que haya stock en tu barrio. Curuba sostiene
esa diferencia al responder. El conteo por estado y las trampas del listado están en
[`resources/data/README.md`](resources/data/README.md).

### 3. La ruta legal

Si te negaron o te están demorando un medicamento, Curuba te hace las preguntas de
procedibilidad —una por mensaje, en lenguaje sencillo— y te devuelve el PDF **del escrito
que procede**, que no siempre es la tutela:

| Escrito | Cuándo procede |
|---|---|
| **Derecho de petición** ante la EPS | No hay riesgo inmediato y todavía no has pedido nada por escrito |
| **Acción de tutela** | Corre riesgo tu vida (va directa, con medida provisional), o ya radicaste y se venció el plazo |
| **Incidente de desacato** | Ya hay fallo de tutela y la EPS no cumple |
| **Demanda ante la Supersalud** | El problema es de cobertura o de reembolso, no de entrega |

**Escoger mal el mecanismo es el error que cuesta semanas.** Llevarle a la Supersalud un
problema de entrega es tocar una puerta que no tiene competencia — la Corte lo dijo en
T-243 de 2016 y T-163 de 2018. Por eso el triage no lo improvisa el modelo: es una tabla
de decisión en Python, y el generador **se niega** a producir un escrito que no
corresponda.

Este intercambio es real, copiado de una corrida del agente:

> **Tú:** llevo tres semanas yendo a la farmacia y no me entregan el losartán. quiero
> poner una tutela ya
> **Curuba:** Si no recibes el losartán ya, ¿corre riesgo tu vida o tu salud de forma grave?
> **Tú:** no, es para la tensión
> **Curuba:** ¿El problema es que no te lo entregan, que la EPS dice que no lo cubre, o
> que ya lo pagaste de tu bolsillo?
> **Tú:** no me lo entregan. no he radicado nada, no sabía que tocaba
> …
> **Curuba:** Con lo que me contaste, lo que corresponde ahora es un derecho de petición
> ante tu EPS, no la tutela: como todavía no le has pedido nada por escrito, este es el
> paso que toca primero, es gratis y deja constancia con fecha que te sirve si después
> necesitas tutelar. Vamos armándolo: ¿cuál es tu nombre completo?
> …
> **Curuba:** Aquí está tu derecho de petición listo 📎 No quedó ningún espacio en blanco,
> así que puedes radicarlo tal cual y pide el número de radicado. La ley le da a la EPS 15
> días hábiles para responderte; si no contesta, ya con esa constancia sí procede la tutela.

**Pidió una tutela y Curuba le dio otra cosa, y esa es la función.** No por terco: sin un
radicado previo la tutela llega sin la prueba que la sostiene.

**La ley juega a favor.** La tutela es gratuita, no requiere abogado y no exige
formalidades especiales (art. 86 de la Constitución). El Decreto 2591 de 1991, art. 29,
obliga al juez a fallar en **10 días** y fija un plazo de cumplimiento que **no puede
exceder 48 horas**.

**Pero se cae por la forma, no por el fondo.** Cerca de una de cada cuatro no se concede, y
la jurisprudencia identifica con precisión las causales que la tumban **antes de que el
juez examine si el paciente tenía razón**: subsidiariedad, rechazo por defectos en la
solicitud, legitimación por activa y carencia actual de objeto. Cada una es una pregunta
que se puede hacer en un chat — la tabla que las cruza con las sentencias y con los campos
de la entrevista está en
[`RESEARCH.md`](resources/docs/RESEARCH.md#por-qué-se-cae-una-tutela).

**Generar el PDF es lo fácil.** Lo difícil —y lo que nadie está resolviendo— es hacer las
preguntas correctas *antes* de generarlo, para que la tutela no se caiga por la forma. Eso
es lo que separa a Curuba de una plantilla descargable.

El documento cubre lo que un juez va a mirar: hechos, derechos vulnerados (arts. 11, 1 y
49 C.P. y Ley 1751 de 2015), procedibilidad —subsidiariedad, inmediatez, legitimación por
activa y por pasiva, perjuicio irremediable, no temeridad—, pretensiones, juramento,
pruebas, notificaciones y firma.

## Por qué WhatsApp

WhatsApp tiene **94 % de penetración en Colombia** y el 97,7 % de los mayores de 16 años
tiene smartphone ([las cifras del canal](resources/docs/RESEARCH.md#por-qué-whatsapp)). Un
paciente en Vichada con una fórmula en la mano no va a instalar una app. Ya tiene WhatsApp
abierto.

## Cómo funciona

```
   WhatsApp
      │
      ▼
   Twilio ──────► FastAPI (Railway)
                     │   el webhook responde 200 de inmediato;
                     │   la respuesta real se manda aparte
                     ▼
              Pydantic AI Agent  ◄──►  Claude (OpenRouter)
              7 tools · 2 toolsets
                     │
        ┌────────────┴──────────────┐
        │ toolset medicamentos      │ toolset ruta_legal
        ▼                           ▼
   Postgres · pg_trgm            decidir_ruta()
   PBS 2.067 · SISMED 38.731     tabla en Python
   INVIMA 783                       │  qué escrito procede
        │                           ▼
        │ marca comercial o    fpdf2 → PDF
        ▼ precio de mostrador        │
   La Rebaja · Farmatodo             ▼
   Perplexity Sonar (respaldo)  GET /f/{id} ──► Twilio adjunta el PDF
```

Un solo agente con siete tools; el modelo decide cuál usar. No hay ruteo por palabras
clave, así que las tres funciones conviven en la misma conversación.

**Lo único que el modelo no decide es cuál escrito procede.** Eso sale de una tabla de
decisión en Python, por la misma razón por la que el significado de cada estado de
cobertura también está en Python: en salud y en derecho, un dato equivocado es peor que no
dar ninguno.

### La corrida, en vivo

Un chat de WhatsApp proyectado en una pantalla no muestra nada de lo que pasa debajo. Por
eso hay una segunda ruta en la web, [`/demo`](https://curuba-web-production.up.railway.app/demo):
a la izquierda el mapa del agente prendiéndose tool por tool mientras corre, a la derecha
un celular con la conversación real apareciendo en vivo, con la foto de la fórmula y el PDF
que se genera.

**Los datos no son una maqueta.** Salen del `event_stream_handler` de Pydantic AI sobre la
misma corrida que atiende el webhook de Twilio: un evento por cada tool que se llama y por
cada trozo de texto que escribe el modelo, servidos por SSE en `GET /demo/eventos`. Lo que
sostiene que un panel pueda mirar el camino de producción es que el emisor no bloquea y no
levanta nunca — un panel roto no puede callar una respuesta.

**Solo se proyecta un número, el de `CURUBA_DEMO_WA`,** y el descarte va en el emisor y no
en el cliente: la conversación de otro paciente no entra al bus, no sale por el SSE y no le
queda la foto de su fórmula guardada.

## Correr localmente

```bash
cd apps/api
cp .env.example .env          # llenar DATABASE_URL, OPENROUTER_API_KEY y las de Twilio

uv sync                       # el ETL no necesita extras: lee los CSV con la stdlib
uv run python -m curuba.etl   # crea el esquema y carga resources/data/ a Postgres
uv run uvicorn curuba.main:app --app-dir src --reload
```

**Para iterar el prompt no hace falta ni Twilio ni túnel**, hay un REPL del agente:

```bash
PYTHONPATH=src uv run python -m curuba.agent
#   reiniciar            borra la conversación y el caso
#   limpiar cache        vacía el caché de las búsquedas web
#   foto <ruta> [texto]  manda una imagen, como una fórmula por WhatsApp
```

`reiniciar` también funciona escribiéndolo por WhatsApp, y se usa todo el tiempo probando
la entrevista legal: sin eso la corrida siguiente arrastra los campos de la anterior.

Y el webhook completo se puede probar sin exponer nada — un POST form-encoded a
`/webhooks/twilio/whatsapp` con `From=whatsapp:%2B57...` corre el agente y la respuesta
sale por la API REST al celular de verdad. Si se prefiere que Twilio lo llame:

```bash
ngrok http 8000
# y apuntar el webhook de WhatsApp en la consola de Twilio a
# https://<tu-subdominio>.ngrok.io/webhooks/twilio/whatsapp
```

El panel de `/demo` es la landing corriendo aparte, apuntada a esa API:

```bash
cd apps/web && npm install && npm run dev   # NEXT_PUBLIC_API_URL, si no cae a :8000
```

Necesita `CURUBA_DEMO_WA` y `PUBLIC_BASE_URL` puestas en la API. **Lo mueve el webhook, no
el REPL** —el REPL conversa como el número `local`, que no es el de la allowlist—, así que
para verlo moverse sin Twilio se le manda el POST de arriba con el número de la demo.

## Documentación

| | |
|---|---|
| [`apps/api/README.md`](apps/api/README.md) | la API: modelo de datos, las siete tools, endpoints |
| [`apps/web/README.md`](apps/web/README.md) | la landing, el panel de `/demo` y el copy de cada sección |
| [`resources/data/README.md`](resources/data/README.md) | columnas, cortes y trampas de parseo de SISMED, INVIMA y PBS |
| [`resources/docs/RESEARCH.md`](resources/docs/RESEARCH.md) | las cifras y de dónde sale cada una |
| [`resources/docs/DESIGN.md`](resources/docs/DESIGN.md) | el sistema de diseño: paleta, tipografía y presupuesto técnico |
| [`resources/docs/DEPLOYMENT.md`](resources/docs/DEPLOYMENT.md) | Railway, Twilio y el orden en que conviene probar |

---

*Curuba no da asesoría médica ni jurídica. Los precios son techos regulados del SISMED para
el canal institucional, no lo que cobra un punto de venta. El estado de desabastecimiento es
el del último corte publicado por el INVIMA y puede haber cambiado. Que un medicamento no
aparezca en el listado del PBS no significa que no esté cubierto. Los escritos legales que
genera son **borradores que deben revisarse antes de radicarse**.*
