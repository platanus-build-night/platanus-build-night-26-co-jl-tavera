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

**90 %** de los pacientes encuestados en puntos de dispensación no recibió sus
medicamentos, o los recibió a medias y con demoras (n=3.449, Defensoría del Pueblo 2025).
El gasto de bolsillo en salud creció **57,3 %** entre 2022 y 2025. Y en 2025 se radicaron
**312.500 tutelas en salud**, un 17,8 % más que en 2024; el juez le da la razón al paciente
el **74,3 %** de las veces.

Las cifras completas —la serie histórica desde 2020, el desglose por ingresos y por zona
rural, las causales que tumban una tutela— están en
[`resources/docs/RESEARCH.md`](resources/docs/RESEARCH.md), cada una con su fuente anotada.

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

**Qué precio es exactamente.** El techo de venta **final al público** viene con valor en 4
filas de 38.731; el del canal **institucional**, en las 38.731. Así que Curuba no dice
"esto es lo que deberías pagar en la droguería" —dice cuál es el techo regulado que sí
está respaldado. Es menos vendedor y es lo único honesto; el porqué está en
[`resources/data/README.md`](resources/data/README.md).

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

La clasificación del INVIMA tiene seis estados; el corte cargado (mayo 2026) trae **783
medicamentos** en cuatro de ellos —cerca de la mitad en monitorización y solo 11
efectivamente desabastecidos.

**Que un medicamento aparezca como *no desabastecido* no es lo mismo a que no aparezca.**
El primero fue objeto de seguimiento y se resolvió; al segundo el INVIMA nunca lo miró, y
que no lo tenga en seguimiento no significa que haya stock en tu barrio. Curuba sostiene
esa diferencia al responder. El conteo por estado y las trampas del listado están en
[`resources/data/README.md`](resources/data/README.md).

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

## Correr localmente

```bash
cd apps/api
cp .env.example .env          # llenar DATABASE_URL, OPENROUTER_API_KEY y las de Twilio

uv sync --extra etl
uv run python -m curuba.etl   # crea el esquema y carga resources/data/ a Postgres
uv run uvicorn curuba.main:app --app-dir src --reload
```

Para probar el webhook de verdad hace falta una URL pública:

```bash
ngrok http 8000
# y apuntar el webhook de WhatsApp en la consola de Twilio a
# https://<tu-subdominio>.ngrok.io/webhooks/twilio/whatsapp
```

Escribiendo `reiniciar` por WhatsApp se borra la conversación y el borrador de tutela.

## Documentación

| | |
|---|---|
| [`apps/api/README.md`](apps/api/README.md) | la API: modelo de datos, tools, endpoints |
| [`apps/web/README.md`](apps/web/README.md) | la landing y su sistema de diseño |
| [`resources/data/README.md`](resources/data/README.md) | columnas, cortes y trampas de parseo de SISMED, INVIMA y PBS |
| [`resources/docs/RESEARCH.md`](resources/docs/RESEARCH.md) | las cifras y de dónde sale cada una |
| [`resources/docs/DEPLOYMENT.md`](resources/docs/DEPLOYMENT.md) | Railway, Twilio y el orden en que conviene probar |

---

*Curuba no da asesoría médica ni jurídica. Los precios son techos regulados del SISMED para
el canal institucional, no lo que cobra un punto de venta. El estado de desabastecimiento es
el del último corte publicado por el INVIMA y puede haber cambiado. La tutela que genera es
un **borrador que debe revisarse antes de radicarse**.*
