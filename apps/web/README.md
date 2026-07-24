# Curuba — Landing

La página pública. Explica qué hace Curuba y manda a la gente al WhatsApp. Es una sola
página: no hay login, ni dashboard, ni backend propio — todo el producto vive en el chat.

> **Estado: sin implementar.** Esta carpeta es el spec: hoy solo está este archivo.
>
> **La landing no depende de la API.** No la consume, no le pega a Postgres, no tiene
> variables de servidor: el único llamado a la acción es un enlace `wa.me`. Se puede
> escribir y desplegar aunque las tools del agente todavía no estén listas, y eso la
> vuelve lo primero que se puede dar por terminado.

Este README debe alcanzar para escribir la página entera sin abrir otro archivo. Las
cifras, el copy y los ejemplos de chat ya están resueltos acá abajo.

## Stack

Next.js (App Router) + Tailwind, desplegado en Vercel. Todo estático: no hay fetch en
runtime, así que la página se prerenderiza completa.

## Estructura planeada

```
apps/web/
├── package.json
├── next.config.ts
├── .env.local
├── public/
│   └── project-logo.png   # copiado de la raíz del repo — ver "Marca y assets"
└── app/
    ├── layout.tsx      # metadata, og:image, favicon, fuente
    ├── page.tsx        # la página entera
    └── globals.css     # Tailwind
```

**La landing es una sola `page.tsx`.** Los tres chats de ejemplo y las tres cifras van
como arrays de datos dentro del archivo, no como componentes en archivos sueltos. Es la
misma regla que sigue la API —*antes de crear uno nuevo, extender el que ya existe*— y sin
decirlo esto termina en ocho componentes para una página que se lee en 40 segundos.

## Secciones de la página

```
┌────────────────────────────────┐
│  Hero: logo, nombre, línea, CTA│
├────────────────────────────────┤
│  90 %   312.500   74,3 %       │
├────────────────────────────────┤
│  ① fórmula → precio            │
│  ② ¿desabastecido?             │
│  ③ tutela → PDF                │
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
| Título | **Averigua cuánto debería costar tu fórmula** |
| Subtítulo | Un agente de WhatsApp que te dice cuál es el precio regulado de los medicamentos de tu fórmula, si están desabastecidos, y te arma la tutela si te los niegan. |
| Botón | Escríbele por WhatsApp |

El subtítulo es el oneliner de [`build-night-project.json`](../../build-night-project.json)
tal cual — el mismo que ve el jurado.

> La versión anterior de este spec proponía *"Sabé cuánto debería costar tu fórmula"*. Se
> cambió a propósito: el imperativo voseo es válido en Antioquia pero ajeno para un
> paciente en Vichada, y el resto del producto tutea — el prompt del agente
> (`apps/api/src/curuba/agent.py`) y el README raíz dicen "te dice", "te arma la tutela".
> Queda anotado por si se quiere volver atrás, pero que sea una decisión y no un descuido.

### 2. Banda de cifras

Tres números con la fuente al pie de la banda. No es una tabla: son tres cifras grandes y
una línea de atribución.

| Cifra | Rótulo |
|---|---|
| **90 %** | de los pacientes no recibe sus medicamentos, o los recibe a medias y con demoras |
| **312.500** | tutelas en salud en 2025 (+17,8 % frente a 2024) |
| **74,3 %** | de las tutelas se conceden: el juez le da la razón al paciente |

Atribución: *Defensoría del Pueblo, 2025 — encuesta en puntos de dispensación (n=3.449).
Todas las fuentes en `research/FUENTES.md`.*

**Los dos detalles chiquitos no son decoración.** El `n=3.449` es lo que separa una
encuesta de un titular. Y el `+17,8 %` es a propósito: la prensa titula **+17,92 %**
porque compara contra una base redondeada de 265.000; contra el 265.173 de la serie el
aumento es 17,8 %. El README raíz ya sostiene esa precisión —
[ver la nota](../../README.md#las-cifras) — y la landing no la puede aflojar.

### 3. Las tres funciones

Una tarjeta por función, cada una con un intercambio real de WhatsApp. **Los ejemplos
convencen más que la descripción.** Van literales del [README raíz](../../README.md#las-tres-funciones):

**① Fórmula → precio regulado**

> **Tú:** _[foto de una fórmula]_
> **Curuba:** Encontré 3 medicamentos en tu fórmula. Estos son los **techos de precio
> regulados del canal institucional** (Circular CNPMDM), no lo que te va a cobrar la
> droguería:
> • Acetaminofén 500 mg — sólido oral x 100 → $12.400 la presentación
> • Losartán 50 mg — sólido oral x 30 → $8.900 la presentación
> • Omeprazol 20 mg — sólido oral x 14 → $6.100 la presentación

Las cifras del ejemplo son ilustrativas y **la página tiene que decirlo**, en letra chica
debajo de la tarjeta: los valores reales los arma el ETL sobre el corte de SISMED, y el
techo es por presentación, no por unidad.

**② ¿Está desabastecido?**

> **Tú:** ¿el losartán está desabastecido?
> **Curuba:** El INVIMA lo tiene en seguimiento con estado *desabastecido* desde el último
> corte. Si en tu droguería no lo consiguen, tu EPS sigue obligada a garantizarte el
> tratamiento — puede ser con otra presentación o por otro proveedor.

Igual: intercambio ilustrativo, el estado real es el del corte cargado. Y vale la pena
decir para qué sirve la función, que no es obvio: **define si el problema es del país o es
de tu EPS.**

**③ Tutela → PDF**

> **Curuba:** ¿Contra qué EPS es la tutela?
> **Tú:** Sanitas
> **Curuba:** ¿Qué medicamento o servicio te negaron?
> **Tú:** el losartán, llevo 3 semanas yendo
> **Curuba:** ¿Ya pusiste la queja o la solicitud ante la EPS antes de esto?
> …
> **Curuba:** Listo, aquí está tu tutela 📎 Revísala antes de radicarla — sobre todo los
> datos personales y las fechas. La radicas en cualquier juzgado, sin abogado y sin costo.

Una línea de apoyo: la tutela es gratuita, no requiere abogado y el juez falla en 10 días
(art. 86 C.P. · Decreto 2591 de 1991, art. 29).

### 4. De dónde salen los datos

Esto es lo que hace creíbles los precios; **no esconderlo en un pie de página.**

| Fuente | Qué aporta | Corte | Tamaño |
|---|---|---|---|
| **SISMED** (MinSalud / SISPRO) | Techos de precio de la Circular CNPMDM | 2026-07-24 | 38.731 medicamentos |
| **INVIMA** | Estado de seguimiento de abastecimiento | mayo 2026 | 783 medicamentos |

Con enlace a [`raw/README.md`](../../raw/README.md) —columnas, cortes y trampas de
parseo— y a [`research/FUENTES.md`](../../research/FUENTES.md), que rastrea cada cifra
hasta su fuente.

### 5. Aviso legal

Visible, no en letra chiquita. Ver abajo.

## Las dos precisiones que la página no puede perder

Son las dos cosas que el repo entero se esfuerza en sostener y que una landing tiende a
suavizar sin darse cuenta. Van con su porqué para que no se pierdan al redactar el JSX.

**El precio es del canal institucional, no del mostrador.** El CSV del SISMED trae tres
columnas de precio, y la que le interesaría al paciente —el precio máximo de venta **final
al público**— viene con valor en **4 filas de 38.731**; en el resto dice `No regulado`. El
institucional, en cambio, viene en las 38.731. Así que la página **no puede prometer
"esto es lo que vas a pagar en la droguería"**: dice cuál es el techo regulado del canal
institucional, que sirve de referencia para saber si lo que están pidiendo está fuera de
rango. Es menos vendedor y es lo único honesto. El detalle está en
[`raw/README.md`](../../raw/README.md#sorpresa-2-el-precio-que-le-importa-al-paciente-casi-nunca-está-regulado).

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

**Hay que copiar `project-logo.png` a `apps/web/public/`.** Vercel construye con el Root
Directory en `apps/web` y no ve la raíz del repo, así que un `../../project-logo.png`
falla en el build aunque funcione en local. De ahí salen el favicon y el `og:image`.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `NEXT_PUBLIC_WHATSAPP_URL` | El enlace `wa.me` con el número y un texto prellenado |

```
NEXT_PUBLIC_WHATSAPP_URL=https://wa.me/12603057633?text=Hola%20Curuba
```

El número no va hardcodeado en el JSX: durante el hackathon puede cambiar, y si está en el
entorno se cambia en Vercel sin volver a desplegar código. El valor sale de
`TWILIO_WHATSAPP_FROM` en `apps/api/.env.example` — **solo el número**: ese archivo tiene
credenciales reales al lado y nada más de ahí entra a este repo público.

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

No necesita la API corriendo, ni Postgres, ni túnel.

## Deploy en Vercel

**Vercel no se puede conectar a este repo.** Es de la organización
`platanus-build-night` y las plataformas de deploy solo acceden a repos propios. El espejo
ya existe: **`jl-tavera/curuba-platanus`**, y `origin` tiene dos push URLs, así que un solo
`git push` actualiza los dos. La receta completa —y el hook `pre-push` que aborta si falta
alguno de los dos remotos— está en [`CLAUDE.md`](../../CLAUDE.md) y en el
[README raíz](../../README.md#deploying-vercel-render-etc).

Vercel se conecta **al espejo**, no al repo de la organización.

En el proyecto de Vercel, poner el **Root Directory** en `apps/web`; si no, el build falla
porque no encuentra el `package.json` en la raíz.

## Aviso legal

El aviso tiene que aparecer **en la página**, no solo en el repo:

> Curuba no da asesoría médica ni jurídica. Los precios son techos regulados del SISMED
> para el canal institucional, no lo que cobra un punto de venta. El estado de
> desabastecimiento es el del último corte publicado por el INVIMA y puede haber cambiado.
> La tutela que genera es un **borrador que debe revisarse antes de radicarse**.
