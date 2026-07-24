<img src="./project-logo.png" alt="Curuba" width="140" />

# Curuba

**Un agente de WhatsApp que te dice cuál es el precio regulado de los medicamentos de tu
fórmula, si están desabastecidos, y te arma la tutela si te los niegan.**

*A WhatsApp agent for Colombian patients: prescription pricing against the regulated
SISMED ceilings, INVIMA shortage lookups, and generated tutela drafts.*

Platanus Build Night — Bogotá @ Buk · Hacker: Jose Luis Tavera ([@jl-tavera](https://github.com/jl-tavera))

---

## El problema

El medicamento está formulado por un médico, está cubierto por el sistema y su entrega es
un derecho fundamental. Aun así, **9 de cada 10 pacientes no lo reciben, o lo reciben a
medias y con demoras.**

Cuando eso ocurre el paciente tiene tres caminos. Ninguno es navegable sin información que
hoy existe, es pública, y está en formatos que ningún paciente va a abrir:

- **Comprarlo de forma particular.** Los precios máximos están regulados y publicados por
  el Ministerio de Salud en SISMED — en un CSV de 38.731 filas. Sin esa referencia el
  paciente no tiene contra qué comparar lo que le piden en el mostrador.
- **Esperar a que llegue.** No tiene manera de distinguir si el medicamento está
  desabastecido en todo el país o si su EPS simplemente no está cumpliendo. Esa
  distinción define qué debe hacer después, y la respuesta está en un PDF mensual del
  INVIMA de 93 páginas, organizado por principio activo.
- **Interponer una tutela.** Es gratuita, no requiere abogado, el juez falla en 10 días y
  el paciente gana la mayoría de las veces. Pero exige entender los requisitos de
  procedibilidad y redactar un documento jurídico. Una tutela mal formulada no se pierde
  por falta de razón: se cae antes de que el juez mire el fondo.

**Curuba tiene tres funciones porque el paciente tiene tres caminos** — una por camino, en
el único canal que ya tiene abierto.

### Las cifras

Todas las fuentes están en [`research/FUENTES.md`](research/FUENTES.md), con anotación de qué dato aporta
cada una.

**El sistema no entrega**

| Cifra | Fuente |
|---|---|
| **90 %** de los pacientes encuestados en puntos de dispensación no recibió sus medicamentos, o los recibió parcialmente y con demoras (n=3.449) | Defensoría del Pueblo, 2025 |
| **584** medicamentos distintos reportados como no entregados (corte a sept. 2025) | Defensoría del Pueblo, 2025 |
| **48 %** de los casos con seguimiento seguía sin resolverse | Defensoría del Pueblo, 2025 |
| **~40 %** de la población no accedió, o accedió solo parcialmente, a sus medicamentos | Encuesta de Calidad de Vida, DANE 2024 |
| **~685.000** reclamos por medicamentos ante la Supersalud en 2025 | Defensoría del Pueblo / Supersalud |

Los tres medicamentos más reportados como no entregados: **metformina, valsartán y
losartán**. Hipertensión y diabetes — tratamientos crónicos que matan cuando se cortan.

**El paciente termina pagando**

| Cifra | Fuente |
|---|---|
| **61 %** de los encuestados dijo que compraría el medicamento de forma particular | Defensoría del Pueblo, 2025 |
| Comprarlo cuesta entre el **7 % y el 90 % de los ingresos** del paciente | Defensoría del Pueblo, 2025 |
| El gasto de bolsillo en salud creció **57,3 %** entre 2022 y 2025 | Afidro / Algebra Labs sobre datos DANE |
| Creció **61,7 % en zonas rurales** vs. 26,4 % en ciudades | Afidro / Algebra Labs |
| **60,3 %** de las personas de menores ingresos no recibió sus medicamentos, vs. 45,1 % en hogares de mayores ingresos | Afidro / Algebra Labs |
| Los hogares gastaron **$70,2 billones** en salud en 2025: **6,9 % del PIB** | Portafolio / Raddar |

**Y termina en un juzgado**

| Cifra | Fuente |
|---|---|
| **312.500** tutelas en salud en 2025, frente a 265.173 en 2024 (**+17,8 %**) | Defensoría del Pueblo |
| **34 %** de todas las tutelas del país son de salud | Defensoría del Pueblo |
| **36,8 %** de las tutelas en salud de 2025 son por entrega inoportuna de medicamentos o insumos | Defensoría del Pueblo |
| **74,3 %** de tasa de concesión: el juez le da la razón al paciente | Defensoría del Pueblo |
| **1.003.147** tutelas de salud radicadas entre 2020 y agosto de 2025 | Corte Constitucional, vía Defensoría |
| De **18.451** tutelas acompañadas por la Defensoría, **1 de cada 4** fue por negación de medicamentos | Defensoría del Pueblo |

Tutelas en salud por año:

```
2020   81.736
2021   92.372
2022  156.357
2023  197.737
2024  265.173
2025  312.500  ←  +282 % vs 2020
```

Tres departamentos concentran el volumen: **Antioquia** (55.705), **Valle del Cauca**
(27.971) y **Bogotá** (26.372).

<sub>Dos notas de precisión, por si alguien saca la calculadora: la prensa titula
**+17,92 %** para 2025 porque compara contra una base redondeada de 265.000; contra el
265.173 de la serie el aumento es **+17,8 %**. Y los porcentajes territoriales que publica
la fuente (20,5 % / 10,3 % / 9,7 %) implican un total de ~271.700, no los 312.500 del año
— probablemente son de un corte parcial, así que acá van solo los valores absolutos.</sub>

## Las tres funciones

### 1. Fórmula → precio regulado

Le mandas una foto de la fórmula (o la escribes). Curuba extrae los medicamentos, los
busca en SISMED y te devuelve cada uno con su techo de precio y la circular que lo fija.

> **Tú:** _[foto de una fórmula]_
> **Curuba:** Encontré 3 medicamentos en tu fórmula. Estos son los **techos de precio
> regulados del canal institucional** (Circular CNPMDM), no lo que te va a cobrar la
> droguería:
> • Acetaminofén 500 mg — sólido oral x 100 → $12.400 la presentación
> • Losartán 50 mg — sólido oral x 30 → $8.900 la presentación
> • Omeprazol 20 mg — sólido oral x 14 → $6.100 la presentación
> Sirven de referencia para saber si lo que te están pidiendo está fuera de rango.

*Las cifras del ejemplo son ilustrativas: los valores reales los arma el ETL sobre el
corte de SISMED, y el techo es por presentación, no por unidad.*

Los nombres nunca coinciden exactamente —una fórmula a mano dice "acetaminofen 500" y
SISMED dice `ACETAMINOFÉN - Sólido - Oral`— así que la búsqueda es por similitud de
trigramas y, cuando hay duda, Curuba pregunta en vez de adivinar. Un precio equivocado en
una app de salud es peor que no dar precio.

**Qué precio es exactamente.** Esto importa y es la parte incómoda. El CSV del SISMED
trae tres columnas de precio, y la que le interesaría al paciente —el precio máximo de
venta **final al público**— viene con valor en **4 filas de 38.731**; en el resto dice
`No regulado`. El precio del canal **institucional**, en cambio, viene en las 38.731. Así
que Curuba no puede decir "esto es lo que deberías pagar en la droguería": dice cuál es el
techo regulado del canal institucional, que sí está respaldado. Es menos vendedor y es lo
único honesto. El detalle está en [`raw/README.md`](raw/README.md).

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

La clasificación del INVIMA tiene seis estados. El corte cargado (mayo 2026) trae **783
medicamentos** en cuatro de ellos:

| Estado | Medicamentos |
|---|---|
| En monitorización | 389 |
| No desabastecido *(seguimiento cerrado)* | 373 |
| Desabastecido | 11 |
| En riesgo de desabastecimiento | 9 |

Los otros dos —no comercializado y descontinuado— viven en un anexo aparte del PDF y no
se cargan.

**Que un medicamento aparezca como *no desabastecido* no es lo mismo a que no aparezca.**
El primero fue objeto de seguimiento y se resolvió; el segundo el INVIMA nunca lo miró.
Son casi la mitad de las filas y Curuba sostiene la diferencia al responder. Si un
medicamento no aparece, lo dice así: que el INVIMA no lo tenga en seguimiento no
significa que haya stock en tu barrio.

### 3. Tutela

Si te negaron o te están demorando un medicamento, Curuba te hace las preguntas de
procedibilidad —una por mensaje, en lenguaje sencillo— y te devuelve el PDF.

> **Curuba:** ¿Contra qué EPS es la tutela?
> **Tú:** Sanitas
> **Curuba:** ¿Qué medicamento o servicio te negaron?
> **Tú:** el losartán, llevo 3 semanas yendo
> **Curuba:** ¿Ya pusiste la queja o la solicitud ante la EPS antes de esto?
> …
> **Curuba:** Listo, aquí está tu tutela 📎 Revísala antes de radicarla — sobre todo los
> datos personales y las fechas. La radicas en cualquier juzgado, sin abogado y sin costo.

**La ley juega a favor.** La tutela es gratuita, no requiere abogado y no exige
formalidades especiales (art. 86 de la Constitución). El Decreto 2591 de 1991, art. 29,
obliga al juez a fallar en **10 días** y fija un plazo de cumplimiento que **no puede
exceder 48 horas**.

**Pero se cae por la forma, no por el fondo.** Dos mediciones distintas dicen lo mismo
desde ángulos distintos: la Defensoría reporta una tasa de concesión del **74,3 %** (o
sea, ~25,7 % no se conceden), y el registro de la Corte Constitucional desglosa **80 %
concedidas, 4,2 % concedidas parcialmente y 15,8 % negadas, rechazadas o declaradas
improcedentes**. Ese último bloque es el punto ciego: la estadística los agrupa, pero la
jurisprudencia identifica con precisión las causales que tumban una tutela **antes de que
el juez examine si el paciente tenía razón**.

Cada causal es una pregunta que se puede hacer en un chat:

| Causal | Jurisprudencia | Qué se pregunta en la entrevista |
|---|---|---|
| **Subsidiariedad** — no haber acudido a la función jurisdiccional de la Supersalud. La Corte corrigió que **no es un requisito ineludible**, y que la Supersalud no tiene competencia cuando hay omisión o silencio de la EPS | SU-508/2020 · T-343/2025 | `otro_medio_defensa`, `solicitud_previa` |
| **Rechazo por defectos en la solicitud** (art. 17, Decreto 2591) — el juez no puede determinar los hechos. Es **excepcional**: primero debe pedir corrección en 3 días | T-313/2018 | `fecha_hechos`, `servicio_negado` |
| **Legitimación por activa** — quién presenta la tutela y bajo qué figura: titular, representante, apoderado o agente oficioso | T-343/2025 | `accionante_*` |
| **Carencia actual de objeto** — la EPS entrega entre la radicación y el fallo (*hecho superado*). No es una derrota: es el sistema cumpliendo solo porque hubo tutela | T-038/2019 · T-008/2025 | `fecha_hechos`, `tutela_previa` |

**Generar el PDF es lo fácil.** Lo difícil —y lo que nadie está resolviendo— es hacer las
preguntas correctas *antes* de generarlo, para que la tutela no se caiga por la forma. Eso
es lo que separa a Curuba de una plantilla descargable.

El documento cubre lo que un juez va a mirar: hechos, derechos vulnerados (arts. 11, 1 y
49 C.P. y Ley 1751 de 2015), procedibilidad —subsidiariedad, inmediatez, legitimación por
activa y por pasiva, perjuicio irremediable, no temeridad—, pretensiones, juramento,
pruebas, notificaciones y firma.

## Por qué WhatsApp

| Cifra | Fuente |
|---|---|
| **94 %** de penetración de WhatsApp en Colombia | Digital Report 2026 (We Are Social / Meltwater) |
| **41,1 M** usuarios de internet (77,3 % de la población) | DataReportal Colombia 2025 |
| **97,7 %** de los mayores de 16 años tiene smartphone | DataReportal Colombia 2025 |
| **62–80 %** de los usuarios en LATAM ya se comunican con empresas por WhatsApp | Digital Report 2026 |

Un paciente en Vichada con una fórmula en la mano no va a instalar una app. Ya tiene
WhatsApp abierto.

## Cómo funciona

```
   WhatsApp
      │
      ▼
   Twilio ──────► FastAPI (Railway)
                     │   webhook responde 200 de inmediato;
                     │   la respuesta real se manda aparte
                     ▼
              Pydantic AI Agent  ◄──►  Claude (OpenRouter)
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
    SISMED       INVIMA        fpdf2
   (Postgres)  (Postgres)    → PDF tutela
                                  │
                                  ▼
                            GET /f/{id} ──► Twilio adjunta el PDF
```

Un solo agente con cuatro tools; el modelo decide cuál usar. No hay ruteo por palabras
clave, así que las tres funciones conviven en la misma conversación.

## Datos

| Fuente | Qué aporta | Corte |
|---|---|---|
| **SISMED** (MinSalud / SISPRO) | Techos de precio de la Circular CNPMDM — institucional y comercial | 2026-07-24 |
| **INVIMA** | Estado de seguimiento de abastecimiento por principio activo | mayo 2026 |

Los dos archivos fuente **están en el repo**, en `raw/` (~11 MB entre los dos), para que
el corte quede congelado aunque la fuente publique otro después — el listado del INVIMA se
reemplaza cada mes. [`raw/README.md`](raw/README.md) documenta las columnas, las trampas
de parseo de cada archivo y por qué se guarda un precio y no otro.

Las fuentes de las cifras del problema —informes, sentencias y prensa— están en
[`research/FUENTES.md`](research/FUENTES.md).

## Correr localmente

```bash
cd apps/api
cp .env.example .env          # llenar DATABASE_URL, OPENROUTER_API_KEY y las de Twilio

uv sync --extra etl
uv run python -m curuba.etl   # crea el esquema y carga raw/ a Postgres
uv run uvicorn curuba.main:app --app-dir src --reload
```

Para probar el webhook de verdad hace falta una URL pública:

```bash
ngrok http 8000
# y apuntar el webhook de WhatsApp en la consola de Twilio a
# https://<tu-subdominio>.ngrok.io/webhooks/twilio/whatsapp
```

Escribiendo `reiniciar` por WhatsApp se borra la conversación y el borrador de tutela.

## Estructura

```
apps/api/src/curuba/
  main.py      webhook de Twilio, GET /f/{id}, /health
  config.py    settings desde el entorno
  db.py        pool de asyncpg + todo el SQL
  agent.py     el Agent y sus cuatro tools
  tutela.py    campos de procedibilidad + render del PDF
  etl.py       carga raw/ a Postgres
  schema.sql   tablas, extensiones e índices
apps/web/      landing en Next.js
raw/           fuentes SISMED e INVIMA
research/      FUENTES.md — las fuentes de todas las cifras de este README
```

## Aviso legal

Curuba **no da asesoría médica ni jurídica**. Los precios son techos regulados del SISMED
para el canal institucional, no lo que cobra un punto de venta. El estado de
desabastecimiento es el del último corte publicado por el INVIMA y puede haber cambiado.
La tutela que genera es un **borrador que debe revisarse antes de radicarse**.

---

## ⚠️ Deploying (Vercel, Render, etc.)

Deploy platforms like **Vercel**, **Render** or **Netlify** can only connect to
repositories **you own** — they can't be granted access to this organization repo.
To deploy while keeping your commits here, mirror your code to a personal repo:

1. Create a **personal** repository on your own GitHub account.
2. Point your local `origin` at **both** repos, so a single `git push` updates each one:

   ```bash
   # this org repo (keep it as a push target)...
   git remote set-url --add --push origin https://github.com/platanus-build-night/platanus-build-night-26-co-jl-tavera.git
   # ...and your personal repo
   git remote set-url --add --push origin https://github.com/<your-user>/<your-repo>.git
   ```

   From now on `git push` sends every commit to **both** repositories.
3. Connect your deploy service (Vercel, Render, …) to your **personal** repo and deploy from there.

Your commits stay mirrored here for judging, while the deploy runs from the repo you control.
