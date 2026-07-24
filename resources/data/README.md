# Datos crudos

Los dos archivos fuente **sí están en el repo** (~11 MB entre los dos). La idea es que
cualquiera pueda clonar y correr el ETL, y que el corte quede congelado aunque la fuente
publique otro después — el listado del INVIMA es de mayo de 2026 y ese PDF se reemplaza
cada mes.

| Carpeta | Archivo | Peso | Corte |
|---|---|---|---|
| `raw/sismed/` | `Precio_máximo_de_venta_de_los_medicamentos_por_presentación_comercial_20260724.csv` | 9,5 MB | 2026-07-24 |
| `raw/invima/` | `LISTADO DE ABASTECIMIENTO MAYO 2026.pdf` | 1,6 MB | mayo 2026 |

Este README documenta lo que **de verdad** traen los archivos, no lo que uno esperaría.
Los dos tienen sorpresas y las dos importan.

---

## SISMED — `raw/sismed/*.csv`

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

## INVIMA — `raw/invima/*.pdf`

**Qué es.** El seguimiento de abastecimiento del INVIMA: medicamentos en monitorización,
en riesgo de desabastecimiento y desabastecidos.

**Fuente.** INVIMA — listado de abastecimiento, publicación mensual.

**Forma del archivo.** 93 páginas, y **no es una sola tabla sino tres**, con columnas y
estados distintos. Se distinguen por las coordenadas x de sus rectángulos, no por número
de página (el listado se republica cada mes con otra paginación):

| Tabla | Páginas | Columnas | Estados | Qué es |
|---|---|---|---|---|
| **A** | 0–71 | 9 | `En monitorización`, `En riesgo de desabastecimiento`, `Desabastecido` | Seguimiento activo |
| **B** | 72–89 | 8 o 9 | `No desabastecido` | Casos cerrados |
| **C** | 90–92 | 8 | `No comercializado`, `Descontinuado` | Anexo, **se descarta** |

Columnas de la tabla A:

`No.` · `Nombre del Medicamento` · `ATC` · `Fecha de inicio del seguimiento` ·
`Fecha del último seguimiento` · `Estado` · `Causas / Observaciones` ·
`RESUMEN CANAL COMERCIAL` · `RESUMEN CANAL INSTITUCIONAL`

La B y la C cambian `Causas / Observaciones` (que siempre dice `---`) por una
`Fecha de cierre`, y no traen las dos de RESUMEN.

**La tabla A empieza en la página 0**, debajo de las notas aclaratorias — no en la 1. Los
medicamentos 1 a 6 están ahí.

**Cada tabla renumera desde 1**, así que `No.` no sirve de llave: hay un `No. 1` en la A y
otro en la B.

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

`scripts/extraer_invima.py`, con pdfplumber. Corre sin instalar nada y no necesita el
entorno de la API — por eso pdfplumber **no** es dependencia de `apps/api`:

```bash
uv run --with pdfplumber python resources/data/scripts/extraer_invima.py --paginas 0-2 --verificar
uv run --with pdfplumber python resources/data/scripts/extraer_invima.py    # las 93 páginas
```

Salida: **`clean/desabastecimiento.csv`**, 783 filas, commiteado.
Columnas `nombre,atc,estado,fecha_seguimiento,listado`, con `listado` en `activo`
(tabla A) o `cerrado` (tabla B). El ETL lo lee igual que el CSV del SISMED.

| Estado | Filas |
|---|---|
| `monitorizacion` | 389 |
| `no_desabastecido` | 373 |
| `desabastecido` | 11 |
| `riesgo` | 9 |

Un mismo principio activo aparece varias veces con formas distintas (`ÁCIDO VALPROICO
CÁPSULA DURA`, `... JARABE`, `... SOLUCIÓN INYECTABLE`). Son filas legítimamente
distintas: **no deduplicar por nombre.**

#### Cuatro trampas del PDF

**1. `extract_table()` con los defaults devuelve basura en la tabla A.** La fuente es de
2,4 pt con interlínea de 2,9 pt, y el `y_tolerance` por defecto de pdfplumber es 3 —
mayor que la interlínea. Colapsa las 9 líneas de una celda en una y las ordena por x:

```
2EUA(PVCE U 1NNB RE LA M / IR NO P 0 T ED D 4 T I AI M LAL T / ) AC 2 : D E U C D S 0 I 2D
```

No es un PDF dañado ni un problema de encoding (las tildes salen bien; si se ven mal es
la consola — `PYTHONIOENCODING=utf-8`). Para la tabla A se trabaja directo sobre
`page.chars` con cortes de columna explícitos y agrupando líneas con tolerancia de
0,5 pt. Para la B sí sirve `extract_table`: fuente de 2,8 pt y filas planas.

**2. La tabla A tiene celdas combinadas verticalmente.** Un medicamento ocupa N
sub-filas, una por titular de Registro Sanitario, y solo la primera trae `No.`, `Nombre`
y `Estado`; las demás solo ATC, fechas y RESUMEN. Los `rect` de esas celdas tienen
**altura 0** (son bordes dibujados, no cajas), así que la combinación no se puede leer de
la geometría: el ancla son los dígitos de la columna `No.`. Los grupos además **cruzan
páginas**.

**3. El corte del encabezado tiene ~1 pt de margen.** El encabezado repetido llega hasta
`top=76.9` y la primera fila de datos arranca en `77.7`. Subir el corte se come el
medicamento que abre la página; bajarlo mete texto del encabezado y, peor, deja entrar
las celdas combinadas que cruzan el salto de página: el exportador las dibuja centradas
sobre todo el rango combinado, así que caen en `top` negativo (el `43 AZITROMICINA` de la
página 8 sale en `top=-370.9`). Son un duplicado del medicamento que ya se leyó en la
página anterior.

**4. `desabastecido` es subcadena de `no desabastecido`.** La misma trampa de la sección
de arriba, pero mordiendo al normalizar. Probando los literales en el orden del dict, las
373 filas de la tabla B salen marcadas como **desabastecidas — exactamente al revés**, y
pasan todos los chequeos en silencio. Se prueban de más largo a más corto.

#### Defectos de la fuente, no del parser

Están verificados uno por uno; el script los reporta en cada corrida:

- **Números repetidos**: `133` y `164` en la tabla A, `362` en la B. Son medicamentos
  **distintos** a los que el INVIMA les puso el mismo número (dos presentaciones de
  ESOMEPRAZOL, `FLUCONAZOL` vs `FLUCONAZOL + SECNIDAZOL`, `UPADACITINIB` vs una vacuna).
  No hay ninguna fila con `nombre`+`atc` repetidos.
- **Hueco**: el `No. 201` no existe en la tabla B.
- **`Estado` en blanco** en el `No. 276` (`OXCARBAZEPINA SUSPENSION ORAL`). Queda vacío en
  el CSV: está en el listado de casos cerrados, pero rellenarlo sería inventarse un dato
  de salud.
- **`Fecha de la última revisión` en blanco** en el `No. 352` (los toxoides). Se toma la
  `Fecha de cierre`, y el script avisa cuál fila usó ese respaldo.
- `V07AB` es un ATC de nivel 4 legítimo, no un error: los dos últimos dígitos son
  opcionales.
- El PDF trae espacios de ancho cero pegados a algunos ATC (`S01ED51​`) y la fuente de las
  filas de vacunas mapea mal la mu (`2.50000 æg` es `2.50000 µg`). Los dos se limpian.

**El chequeo que vale**: que la secuencia de `No.` sea contigua dentro de cada tabla. Si
el ancla falla aparece un hueco — así se encontró la trampa 3, que estaba perdiendo 17
medicamentos en silencio.

---

## Nota sobre el match

Los nombres nunca coinciden exactamente entre lo que escribe el usuario y lo que dice la
fuente: una fórmula a mano dice "acetaminofen 500" y SISMED dice
`ACETAMINOFÉN - Sólido - Oral`. La búsqueda es por similitud de trigramas (`pg_trgm`)
sobre texto normalizado sin tildes, y le devuelve al agente los candidatos con su score
para que desambigüe o pregunte. El detalle está en
[`apps/api/README.md`](../../apps/api/README.md).
