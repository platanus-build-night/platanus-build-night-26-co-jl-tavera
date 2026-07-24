# Datos crudos

Los dos archivos fuente **sí están en el repo** (~11 MB entre los dos). La idea es que
cualquiera pueda clonar y correr el ETL, y que el corte quede congelado aunque la fuente
publique otro después — el listado del INVIMA es de mayo de 2026 y ese PDF se reemplaza
cada mes.

| Carpeta | Archivo | Peso | Corte |
|---|---|---|---|
| `sismed/` | `Precio_máximo_de_venta_de_los_medicamentos_por_presentación_comercial_20260724.csv` | 9,5 MB | 2026-07-24 |
| `invima/` | `LISTADO DE ABASTECIMIENTO MAYO 2026.pdf` | 1,6 MB | mayo 2026 |

Este README documenta lo que **de verdad** traen los archivos, no lo que uno esperaría.
Los dos tienen sorpresas y las dos importan.

---

## SISMED — `sismed/*.csv`

**Qué es.** Los precios máximos de venta regulados por la Comisión Nacional de Precios de
Medicamentos y Dispositivos Médicos (CNPMDM). Es un techo, no un precio observado.

**Fuente.** Datos Abiertos del Ministerio de Salud (datos.gov.co).

**Forma del archivo.** 38.731 filas de datos · 13 columnas · UTF-8 · separado por comas ·
todos los campos entre comillas. **El `CUM` es único** — 38.731 valores distintos en
38.731 filas, así que sirve como llave primaria tal cual, sin deduplicar.

### Columnas

| # | Columna | Ejemplo |
|---|---|---|
| 1 | `No` | `91` |
| 2 | `ID MR` | `8` |
| 3 | `Mercado Relevante` | `Ambrisentán - Sólido - Oral` |
| 4 | `CUM` | `20151854-1` |
| 5 | `Medicamento` | `BRIXENT - Ambrisentan 5mg/1U - Sólido - Oral x 10 - XINETIX PHARMA` |
| 6 | `Cantidad por unidad de medida` | `50` |
| 7 | `Unidad de medida` | `mg` |
| 8 | `Precio máximo de venta transacción primaria, secundaria y final Institucional` | `2147666` |
| 9 | `Margen para IPS` | `75168.31` |
| 10 | `Precio máximo de venta transacción primaria y secundaria comercial` | `2147666` |
| 11 | `Precio máximo de venta transacción final comercial` | `No regulado` |
| 12 | `Circular CNPMDM` | `Circular 19 de 2024` |
| 13 | `Fecha de inicio vigencia precio máximo de venta` | `2024 Jul 31 12:00:00 AM` |

### Sorpresa 1: no hay columnas de principio activo, marca ni laboratorio

Están embebidas en dos campos y hay que partirlas por `" - "`:

**`Mercado Relevante`** → siempre 3 segmentos, verificado en las 38.731 filas:

```
Ambrisentán  -  Sólido  -  Oral
principio       forma      vía
```

Aquí sí se puede partir por posición sin miedo.

**`Medicamento`** → 5 segmentos en el 98,6 %, pero **varía entre 2 y 6**:

```
BRIXENT  -  Ambrisentan 5mg/1U  -  Sólido  -  Oral x 10  -  XINETIX PHARMA
marca       principio + conc.      forma      vía y cant.    laboratorio
```

| Segmentos | Filas |
|---|---|
| 5 | 38.180 |
| 4 | 402 |
| 6 | 64 |
| 2 | 50 |
| 3 | 35 |

**No partir por posición.** Tomar el primer segmento como marca y el último como
laboratorio, y guardar el campo completo como descripción — que además es lo más útil
para mostrarle al usuario, porque trae la presentación entera.

### Sorpresa 2: el precio que le importa al paciente casi nunca está regulado

| Columna | Filas sin valor numérico |
|---|---|
| Institucional (col. 8) | **0** — siempre viene |
| Margen para IPS (col. 9) | 0 |
| Comercial primaria/secundaria (col. 10) | 12.332 (32 %) |
| **Comercial final (col. 11)** | **38.727 de 38.731** |

El precio de venta **final al público** está regulado en **4 medicamentos de 38.731**. El
resto dice `No regulado`.

Esto tiene consecuencia de producto, no solo de parseo: Curuba **no puede decir "esto es
lo que deberías pagar en la droguería"**. Lo que puede decir con respaldo es cuál es el
techo regulado del canal institucional. Es una diferencia incómoda pero es la honesta, y
sostenerla es mejor que dar una cifra que no se cumple en el mostrador.

### Detalles de parseo

- Los números vienen en **formato gringo**: punto decimal y coma de miles (`75168.31`,
  `10,152`). No es el formato colombiano.
- `No regulado` aparece con **dos capitalizaciones**: `No Regulado` en la columna 10 y
  `No regulado` en la 11. Comparar en minúsculas.

---

## INVIMA — `invima/*.pdf`

**Qué es.** El seguimiento de abastecimiento del INVIMA: medicamentos en monitorización,
en riesgo de desabastecimiento y desabastecidos.

**Fuente.** INVIMA — listado de abastecimiento, publicación mensual.

**Forma del archivo.** 93 páginas de una sola tabla que se repite. Columnas:

`No.` · `Nombre del Medicamento` · `ATC` · `Fecha de inicio del seguimiento` ·
`Fecha del último seguimiento` · `Estado` · `Causas / Observaciones` ·
`RESUMEN CANAL COMERCIAL` · `RESUMEN CANAL INSTITUCIONAL`

**Estados que aparecen:** *En monitorización* (~421 menciones) y *Desabastecido* (~13).
El título del documento menciona además *riesgo de desabastecimiento*.

### Qué se necesita y qué se descarta

Solo cuatro campos: **nombre, ATC, estado y fecha del último seguimiento**.

Las dos columnas de `RESUMEN` son párrafos largos sobre unidades disponibles por mes,
promedios de venta y capacidad máxima. No aportan a lo que Curuba responde — se
descartan enteras.

### La trampa: buscar "desabastecido" en el texto da al revés

La palabra aparece **384 veces** en el documento, pero la gran mayoría dentro de la frase:

> *El titular informa que el producto está **Disponible (No desabastecido a la fecha)** en
> el mercado.*

que significa exactamente lo contrario. **El estado hay que leerlo de la columna
`Estado`**, no buscando la palabra en el texto de la fila.

### Otros detalles

- Los nombres traen la forma farmacéutica pegada: `ACETAMINOFEN + CODEINA TABLETA`.
- Las combinaciones de principios activos usan `+`.
- Trae código **ATC**, que sirve como llave y como campo de búsqueda adicional.
- La fuente **no trae CUM**, así que no se puede unir con SISMED por llave: el cruce, si
  se hace, tiene que ser por nombre o por ATC.

### Extracción

**Por definir.** Se documenta aquí cuando se decida el método.

---

## Nota sobre el match

Los nombres nunca coinciden exactamente entre lo que escribe el usuario y lo que dice la
fuente: una fórmula a mano dice "acetaminofen 500" y SISMED dice
`ACETAMINOFÉN - Sólido - Oral`. La búsqueda es por similitud de trigramas (`pg_trgm`)
sobre texto normalizado sin tildes, y le devuelve al agente los candidatos con su score
para que desambigüe o pregunte. El detalle está en
[`apps/api/README.md`](../apps/api/README.md).
