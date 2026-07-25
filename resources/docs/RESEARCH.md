# Investigación

Acá viven **las cifras y sus fuentes**. El [README](../../README.md) se queda con el
producto y cita de acá lo que necesita: cualquier número que aparezca allá tiene que poder
rastrearse hasta un enlace de este archivo.

Dos mitades. Primero **los hallazgos** —lo que dicen los datos sobre el problema que Curuba
ataca—, después **las fuentes**, cada una anotada con qué dato aporta, para no tener que
abrir los ~90 enlaces averiguando cuál sostiene qué.

Los datos de producto —columnas, cortes y trampas de parseo de SISMED, INVIMA y PBS— están
en [`data/README.md`](../data/README.md), no acá.

---

# Los hallazgos

## El sistema no entrega

| Cifra | Fuente |
|---|---|
| **90 %** de los pacientes encuestados en puntos de dispensación no recibió sus medicamentos, o los recibió parcialmente y con demoras (n=3.449) | Defensoría del Pueblo, 2025 |
| **584** medicamentos distintos reportados como no entregados (corte a sept. 2025) | Defensoría del Pueblo, 2025 |
| **48 %** de los casos con seguimiento seguía sin resolverse | Defensoría del Pueblo, 2025 |
| **~40 %** de la población no accedió, o accedió solo parcialmente, a sus medicamentos | Encuesta de Calidad de Vida, DANE 2024 |
| **~685.000** reclamos por medicamentos ante la Supersalud en 2025 | Defensoría del Pueblo / Supersalud |

Los tres medicamentos más reportados como no entregados: **metformina, valsartán y
losartán**. Hipertensión y diabetes — tratamientos crónicos que matan cuando se cortan.

## El paciente termina pagando

| Cifra | Fuente |
|---|---|
| **61 %** de los encuestados dijo que compraría el medicamento de forma particular | Defensoría del Pueblo, 2025 |
| Comprarlo cuesta entre el **7 % y el 90 % de los ingresos** del paciente | Defensoría del Pueblo, 2025 |
| El gasto de bolsillo en salud creció **57,3 %** entre 2022 y 2025 | Afidro / Algebra Labs sobre datos DANE |
| Creció **61,7 % en zonas rurales** vs. 26,4 % en ciudades | Afidro / Algebra Labs |
| **60,3 %** de las personas de menores ingresos no recibió sus medicamentos, vs. 45,1 % en hogares de mayores ingresos | Afidro / Algebra Labs |
| Los hogares gastaron **$70,2 billones** en salud en 2025: **6,9 % del PIB** | Portafolio / Raddar |

## Y termina en un juzgado

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

**Dos ajustes de precisión, por si alguien saca la calculadora.** La prensa titula
**+17,92 %** para 2025 porque compara contra una base redondeada de 265.000; contra el
265.173 de la serie el aumento es **+17,8 %**, y ese es el que se publica. Y los
porcentajes territoriales que da la fuente (20,5 % / 10,3 % / 9,7 %) implican un total de
~271.700, no los 312.500 del año —probablemente salen de un corte parcial—, así que de esos
tres departamentos van **solo los valores absolutos**.

## Por qué se cae una tutela

**Dos mediciones distintas, desde ángulos distintos.** La Defensoría reporta una tasa de
concesión del **74,3 %** —o sea, ~25,7 % no se conceden—, y el registro de la Corte
Constitucional desglosa **80 % concedidas, 4,2 % concedidas parcialmente y 15,8 % negadas,
rechazadas o declaradas improcedentes**. Los denominadores no coinciden porque miden cosas
distintas: van separadas, nunca sumadas ni promediadas.

Ese último bloque es el punto ciego. La estadística agrupa las tres categorías, pero la
jurisprudencia identifica con precisión las causales que tumban una tutela **antes de que
el juez examine si el paciente tenía razón**. Cada causal es una pregunta que se puede
hacer en un chat — la última columna son los campos de `legal.CAMPOS`:

| Causal | Jurisprudencia | Qué se pregunta en la entrevista |
|---|---|---|
| **Subsidiariedad** — no haber acudido a la función jurisdiccional de la Supersalud. La Corte corrigió que **no es un requisito ineludible**, y que la Supersalud no tiene competencia cuando hay omisión o silencio de la EPS | SU-508/2020 · T-343/2025 | `peticion_radicada`, `peticion_fecha`, `tipo_problema` |
| **Rechazo por defectos en la solicitud** (art. 17, Decreto 2591) — el juez no puede determinar los hechos. Es **excepcional**: primero debe pedir corrección en 3 días | T-313/2018 | `fecha_reclamacion`, `medicamento`, `eps` |
| **Legitimación por activa** — quién presenta la tutela y bajo qué figura: titular, representante, apoderado o agente oficioso | T-343/2025 | `nombre`, `cedula` |
| **Carencia actual de objeto** — la EPS entrega entre la radicación y el fallo (*hecho superado*). No es una derrota: es el sistema cumpliendo solo porque hubo tutela | T-038/2019 · T-008/2025 | `fecha_reclamacion`, `tutela_previa` |

**La subsidiariedad tiene una vuelta que cambia el producto.** Para *entrega* de
medicamentos la Supersalud no es competente —T-243 de 2016 y T-163 de 2018—, así que la
tutela es el mecanismo idóneo y no hay que agotarla. Eso es lo que codifica
`legal.decidir_ruta()`: un problema de entrega **nunca** se rutea a la Supersalud.

Las seis sentencias, con lo que aporta cada una, están en
[Procedibilidad y causales de improcedencia](#procedibilidad-y-causales-de-improcedencia-jurisprudencia).

## Por qué WhatsApp

| Cifra | Fuente |
|---|---|
| **94 %** de penetración de WhatsApp en Colombia | Digital Report 2026 (We Are Social / Meltwater) |
| **41,1 M** usuarios de internet (77,3 % de la población) | DataReportal Colombia 2025 |
| **97,7 %** de los mayores de 16 años tiene smartphone | DataReportal Colombia 2025 |
| **62–80 %** de los usuarios en LATAM ya se comunican con empresas por WhatsApp | Digital Report 2026 |

Un paciente en Vichada con una fórmula en la mano no va a instalar una app. Ya tiene
WhatsApp abierto.

---

# Fuentes primarias e institucionales

## Defensoría del Pueblo

Es la fuente del bloque más importante: la encuesta en puntos de dispensación (n=3.449) y
la serie histórica de tutelas en salud.

- Informe Defensorial de Salud 2025 — *Medicamentos inaccesibles, derechos vulnerados: un análisis con enfoque territorial en Colombia*. **Fuente del 90 % de pacientes sin entrega completa, los 584 medicamentos y el 48 % de casos sin resolver.**
  https://www.defensoria.gov.co/-/defensoria-alerta-crisis-acceso-medicamentos-colombia
- Convocatoria y presentación del informe:
  https://www.defensoria.gov.co/-/defensoria-informe-salud-medicamentos-inaccesibles
- Informe de tutelas en salud (FILBo 2026) — **serie histórica y tasa de concesión del 74,3 %**:
  https://www.defensoria.gov.co/-/tutelas-para-invocar-la-proteccion-del-derecho-a-la-salud
- Entrevista a la Defensora sobre la crisis de medicamentos:
  https://www.defensoria.gov.co/en/-/entrevista-a-la-defensora-del-pueblo-sobre-la-crisis-de-medicamentos-en-el-pa%C3%ADs
- Rendición de cuentas — consolidación del informe:
  https://www.defensoria.gov.co/-/defensoria-del-pueblo-rindio-cuentas-a-la-ciudadania-gestion-transparencia-y-decisiones-impostergables-para-la-garantia-de-los-derechos

## INVIMA — desabastecimiento

Fuente del pilar 2. El listado es **mensual**, así que el enlace del portal cambia de
contenido; el corte congelado que usa Curuba está en `resources/data/raw/invima/`.

- Portal de desabastecimientos (listados mensuales):
  https://www.invima.gov.co/productos-vigilados/medicamentos-y-productos-biologicos/desabastecimientos
- Listado enero 2025 (PDF) — **incluye las definiciones de los seis estados de la clasificación**:
  https://www.invima.gov.co/sites/default/files/medicamentos-productos-biologicos/Desabastecimientos/2025/listado_abastecimiento_y_desabastecimiento_medicamentos_enero_de_2025_-_publicado.pdf
- Listado agosto 2025 (PDF):
  https://www.invima.gov.co/sites/default/files/medicamentos-productos-biologicos/Desabastecimientos/2025/listado_abastecimiento_y_desabastecimiento_medicamentos_agosto_de_2025_-_30_sep.pdf
- Listado enero 2026:
  https://www.invima.gov.co/biblioteca/listado-de-abastecimiento-y-desabastecimiento-de-medicamentos-en-seguimiento-enero-2026pdf
- Listado 2026 consolidado (vía Minsalud, PDF):
  https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/VS/MET/listado-abastecimiento-desabastecimiento-medicamentos-2026.pdf
- Listado enero 2025 (biblioteca INVIMA):
  https://www.invima.gov.co/biblioteca/listado-abastecimiento-desabastecimiento-medicamentos-enero-2025
- Minsalud — Abastecimiento de medicamentos:
  https://www.minsalud.gov.co/salud/MT/paginas/desabastecimiento.aspx
- SaluData (Observatorio de Salud de Bogotá) — indicador de desabastecimiento:
  https://saludata.saludcapital.gov.co/osb/indicadores/desabastecimiento-medicamentos/
- SaluData — **explicación de las clasificaciones del INVIMA**:
  https://saludata.saludcapital.gov.co/osb/consulta-la-nueva-actualizacion-del-listado-de-abastecimiento-y-desabastecimiento-de-medicamentos-del-invima/

## PBS — cobertura con cargo a la UPC

La fuente que contesta la pregunta que va **antes** que el precio: si el medicamento está
financiado con la UPC, la ruta es el dispensador de la EPS y no la droguería. Comparar
precios ahorra 20–40 %; enrutar bien ahorra ~100 %. El detalle de columnas y las tres
sorpresas están en [`data/README.md`](../data/README.md).

- Datos Abiertos Colombia — Medicamentos del PBS (**el CSV que carga el ETL**):
  https://www.datos.gov.co/Salud-y-Protecci-n-Social/Medicamentos-del-PBS/jtqe-tuvf
  Corte 2026-07-24, 2.067 filas, commiteado en `resources/data/raw/pbs/`.
- **Resolución 2808 de 2022** — define el PBS con cargo a la UPC. Los artículos 38, 46 y 52
  son los que cita textualmente la columna `Aclaracion` del CSV para condicionar la
  cobertura:
  https://www.minsalud.gov.co/Normatividad_Nuevo/Resoluci%C3%B3n%20No.%202808%20de%202022.pdf
- Minsalud — **ABECÉ MIPRES** (qué es y cómo funciona la vía de prescripción de lo **no**
  financiado con UPC; que un medicamento salga como MIPRES **no** significa que el paciente
  tenga que comprarlo — son las 420 filas de la sorpresa 1 de `data/README.md`):
  https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/VP/AF/abece-ctc-reporte-prescripcion.pdf
- Minsalud — Manual de usuario del módulo de prescripción MIPRES No UPC:
  https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/DE/DIJ/manual-usuario-modulo-prescripcion-tecnologias-salud-no-financiadas-upc-servicios-complementarios-mipres-no-upc.pdf
- **Resolución 1604 de 2013** — entrega de medicamentos no disponibles: domicilio en 48 h.
  Es el respaldo de lo que Curuba le dice al paciente cuando en el dispensador le dicen "no
  hay". El derecho existe, pero el incumplimiento es alto: **no se promete la entrega**, se
  le da al paciente el texto de la norma para exigirla:
  https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/DE/DIJ/resolucion-1604-de-2013.pdf

⚠️ **Esta fuente no se puede leer al revés.** El listado no es exhaustivo y el cruce por
principio activo con SISMED solo alcanza el 72,5 %. Que un medicamento no aparezca
significa "no lo encontré", nunca "no está cubierto" — un falso negativo manda a alguien a
pagar de su bolsillo algo que le corresponde.

## SISMED y precios de medicamentos

Fuente del pilar 1. Lo que publica es un **techo regulado**, no un precio observado — la
distinción está desarrollada en [`data/README.md`](../data/README.md).

- Datos Abiertos Colombia — Precio máximo de venta por presentación comercial
  (**el CSV que carga el ETL**), dataset `nauz-qkjw`:
  https://www.datos.gov.co/resource/nauz-qkjw.json
  Verificado el 2026-07-24 contra el CSV del repo: la primera fila de la API es idéntica
  a la del archivo (`91` · `8` · `Ambrisentán - Sólido - Oral` · `20151854-1` · BRIXENT).
  **Antes se citaba aquí `3t73-n4q9` ("Precios Medicamentos") como la fuente del ETL y era
  otro dataset** — se deja abajo, pero no es el que se carga.
- Datos Abiertos Colombia — Precios Medicamentos (`3t73-n4q9`), relacionado pero **no** es
  el que carga el ETL:
  https://www.datos.gov.co/Salud-y-Protecci-n-Social/Precios-Medicamentos/3t73-n4q9
- Datos Abiertos Colombia — Consulta pública de precios:
  https://www.datos.gov.co/Salud-y-Protecci-n-Social/Consulta-p-blica-de-Precios-de-Medicamentos/3he6-m866
- Minsalud — Sistema de Información de Precios de Medicamentos (SISMED):
  https://www.minsalud.gov.co/proteccionsocial/Paginas/Sistema%20de%20Informaci%C3%B3n%20de%20Precios%20de%20Medicamentos.aspx
- Minsalud — Regulación de precios (listado de precios máximos vigente, SISMED trimestral):
  https://www.minsalud.gov.co/salud/medicamentos-y-tecnologias/Paginas/medicamentos-regulacion-precios.aspx
- SISPRO — SISMED:
  https://www.sispro.gov.co/central-prestadores-de-servicios/Pages/SISMED-Sistema-de-Informacion-de-Precios-de-Medicamentos.aspx
- SISPRO — Consulta pública de precios en la cadena de comercialización (Circular 2 de 2012):
  https://web.sispro.gov.co/WebPublico/Consultas/ConsultarCNPMCadenaComercializacionCircu2yPA_028_2_2.aspx
- ABECÉ SISMED — guía de reporte (PDF):
  https://www.med-informatica.com/OBSERVAMED/SISMED/abece-sismed.pdf
- Neuroeconomix — **dispersión de precios en mercados no regulados** y rol de la CNPMDM:
  https://neuroeconomix.com/en/regulacion-de-precios-herramienta-propuesta-por-el-sistema-de-salud-para-controlar-el-gasto/

## Marco legal de la tutela

Fuente del pilar 3: los plazos (fallo en 10 días, cumplimiento en 48 horas) y la ausencia
de formalidades.

- Decreto 2591 de 1991 — Secretaría del Senado (texto vigente con control de constitucionalidad). **Art. 29: plazo de fallo. Art. 17: rechazo por defectos en la solicitud.**
  http://www.secretariasenado.gov.co/senado/basedoc/decreto_2591_1991.html
- Decreto 2591 de 1991 — Gestor Normativo, Función Pública:
  https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5304
- Decreto 2591 de 1991 — PDF (Minsalud):
  https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/INEC/IGUB/decreto-2591-de-1991.pdf
- Características y procedimiento de la acción de tutela — **plazo de cumplimiento de 48 horas e impugnación**:
  https://www.gerencie.com/principales-caracteristicas-de-la-accion-de-tutela.html

## Procedibilidad y causales de improcedencia (jurisprudencia)

Estas seis sentencias son las que sostienen la tabla de causales del README. Son el
insumo de las preguntas que hace el agente **antes** de generar el PDF.

- **Sentencia SU-508 de 2020** — Subsidiariedad: agotar la función jurisdiccional de la Supersalud **no es requisito ineludible**; el juez no puede declarar la improcedencia automáticamente y debe verificar idoneidad, eficacia y si el accionante es sujeto de especial protección:
  https://www.corteconstitucional.gov.co/relatoria/2020/SU508-20.htm
- **Sentencia T-343 de 2025** — Legitimación por activa; la Supersalud **no tiene competencia cuando hay omisión o silencio de la EPS** ni resulta eficaz frente a agente oficioso; modalidades de carencia actual de objeto:
  https://www.corteconstitucional.gov.co/relatoria/2025/t-343-25.htm
- **Sentencia T-313 de 2018** — Carácter **excepcional** del rechazo (art. 17): el juez debe pedir corrección en 3 días y agotar sus poderes oficiosos antes de rechazar:
  https://www.corteconstitucional.gov.co/relatoria/2018/t-313-18.htm
- **Sentencia T-038 de 2019** — Configuración de la carencia actual de objeto por **hecho superado**:
  https://www.corteconstitucional.gov.co/relatoria/2019/T-038-19.htm
- **Sentencia T-195 de 2021** — Caso de no entrega de medicamentos (insulina, losartán) con **orden de entrega en 48 horas** y hecho superado parcial:
  https://normas.cra.gov.co/gestor/docs/t-195_2021.htm
- **Sentencia T-008 de 2025** — Hecho superado por prestación del servicio y carencia actual de objeto por situación sobreviniente:
  https://www.corteconstitucional.gov.co/relatoria/2025/t-008-25.htm
- Análisis (dic. 2025) — la Corte reitera los **límites al rechazo** de tutelas en salud:
  https://prime.tirant.com/co/actualidad-prime/corte-constitucional-reitero-limites-al-rechazo-de-tutelas-y-advirtio-barreras-indebidas-en-la-atencion-en-salud-de-personas-privadas-de-la-libertad/
- Infobae — límites para rechazar tutelas por requisitos formales:
  https://www.infobae.com/colombia/2025/12/16/corte-constitucional-fijo-los-limites-para-rechazar-tutelas-a-personas-privadas-de-la-libertad-en-casos-de-salud/

## Informes anuales de tutela en salud (serie histórica)

- El Tiempo — **desglose de fallos del registro de la Corte: 80 % concedidas, 4,2 % parciales, 15,8 % negadas / rechazadas / improcedentes**. Es una medición distinta a la tasa de concesión del 74,3 % de la Defensoría; el README las presenta separadas por eso.
  https://www.eltiempo.com/justicia/cortes/tutelas-por-la-violacion-del-derecho-a-la-salud-en-la-corte-constitucional-483164
- Defensoría — *La tutela y los derechos a la salud y a la seguridad social*, 14ª edición:
  https://www.defensoria.gov.co/-/la-tutela-y-los-derechos-a-la-salud-y-a-la-seguridad-social-14%C2%B0-edici%C3%B3n
- Defensoría — Informe 2021 (16ª edición, repositorio con PDF):
  https://repositorio.defensoria.gov.co/items/24a813da-7ebb-47f9-aca3-58b73b2e6400
- Defensoría — Informe 2023 (repositorio):
  https://repositorio.defensoria.gov.co/items/42d74830-83a8-4efb-bf7c-3bc832476a9a/full
- Defensoría — 198.000 tutelas en 2023 y patologías más frecuentes:
  https://www.defensoria.gov.co/en/-/por-vulneraci%C3%B3n-del-derecho-a-la-salud-los-colombianos-presentaron-cerca-de-198.000-tutelas-durante-el-2023
- Ámbito Jurídico — Informe 2018: negación de tecnologías **ya incluidas en el PBS**:
  https://www.ambitojuridico.com/noticias/general/administrativo-y-contratacion/defensoria-del-pueblo-revela-cifras-de-tutela-y
- El Tiempo — Informe 2020: **89,03 % de las negaciones eran de servicios ya incluidos en el PBS**:
  https://www.eltiempo.com/salud/tutelas-por-el-derecho-a-la-salud-informe-de-la-defensoria-del-pueblo-638692
- Así Vamos en Salud — Informe 2013: los medicamentos concentraron el **59,65 % de las negaciones**:
  https://www.asivamosensalud.org/actualidad/defensoria-presenta-informe-la-tutela-y-los-derechos-la-salud-y-la-seguridad-social-2013
- El País — la tasa de tutelas pasó de 3,04 a 4,75 por cada 1.000 afiliados (2022–2024):
  https://www.elpais.com.co/colombia/tutelas-por-salud-se-disparan-en-colombia-corte-constitucional-alerta-crisis-0353.html
- ConsultorSalud — Auto 1280 de 2025: bajo cumplimiento en la medición de tutelas, +150 % en tres años:
  https://consultorsalud.com/corte-bajo-cumplimiento-tutelas-en-salud/

## Estudios y gasto de bolsillo

- Afidro / Algebra Labs — *Gasto de bolsillo y barreras de atención en salud 2019–2025* (PDF, **fuente original del +57,3 %, del corte rural/urbano y del desglose por ingresos**):
  https://afidro.org/wp-content/uploads/2026/04/Gasto-de-bolsillo-y-barreras-de-atencion-en-Salud-2019%E2%80%932025-.pdf
- CEPAL — Análisis comparativo de los precios de los medicamentos en América Latina:
  https://repositorio.cepal.org/bitstreams/0ecc4046-2e6a-4d68-b0c1-e2a9a2d043ee/download

---

# Cobertura de prensa

Sirve para dos cosas: confirmar cifras que están en informes en PDF, y fechar cuándo se
hizo público cada dato.

## Tutelas en salud

- El Espectador — las tutelas en salud aumentaron 17,92 % en 2025:
  https://www.elespectador.com/salud/tutelas-en-salud-aumentaron-en-un-1792-en-2025-defensoria/
- El País — **312.500 tutelas en 2025**:
  https://www.elpais.com.co/colombia/defensoria-alerta-por-aumento-de-tutelas-en-salud-en-18-312500-se-presentaron-en-2025-2304.html
- Semana — aumento del 18 % y fallas estructurales:
  https://www.semana.com/politica/articulo/defensoria-del-pueblo-alerta-sobre-el-aumento-de-18-de-las-tutelas-por-salud-en-colombia-y-evidencia-fallas-estructurales-del-sistema/202615/
- El Colombiano — **serie histórica 2020–2025** y quejas ante Supersalud:
  https://www.elcolombiano.com/colombia/salud/tutelas-salud-subieron-342024-subir-182025-defensoria-OP30592419
- El Colombiano — "sin tutela no atienden":
  https://www.elcolombiano.com/inicio/tutelas-salud-colombia-aumento-2025-defensoria-MP35811805
- ConsultorSalud — Defensoría alerta por aumento de tutelas:
  https://consultorsalud.com/defensoria-alerta-por-aumento-de-tutelas-salud/
- Qhubo — las tutelas por salud incrementaron 18 %:
  https://www.qhubobogota.com/asi-paso/tutelas-salud-incremento/
- Colombia.com — las tutelas rompen récords:
  https://www.colombia.com/actualidad/nacionales/tutelas-por-salud-en-instauradas-en-colombia-alcanzan-cifras-historicas-578778

## Acceso a medicamentos

- Infobae — **36,82 % de tutelas por entrega inoportuna** y 18.451 tutelas acompañadas:
  https://www.infobae.com/colombia/2025/11/05/defensoria-del-pueblo-expuso-las-graves-barreras-de-acceso-a-medicamentos-que-enfrentan-miles-de-pacientes-en-colombia/
- ConsultorSalud — **90 % de los pacientes no recibe sus medicamentos**:
  https://consultorsalud.com/defensoria-del-pueblo-pacientes-medicamentos/
- El Heraldo — presentación del informe y **encuesta a 3.449 personas**:
  https://www.elheraldo.co/colombia/2025/11/05/defensoria-presento-informe-sobre-vulneraciones-a-la-salud-en-colombia-recomienda-una-reforma-a-la-salud-consensuada/
- Asuntos Legales — **584 medicamentos no entregados, 48 % de casos sin resolver, top 3 (metformina, valsartán, losartán)**:
  https://www.asuntoslegales.com.co/actualidad/defensoria-preve-que-el-ano-finalizara-con-315-000-quejas-por-falta-de-medicamentos-4264026
- La FM — **685.000 reclamos por medicamentos; la nota reporta un promedio de 1.600 diarios**:
  https://www.lafm.com.co/sociedad/defensoria-alerta-por-crisis-en-acceso-a-medicamentos-y-vulneracion-del-derecho-a-la-salud-381799
- Emisora Atlántico — **dato de la ECV DANE 2024: ~40 % sin acceso pleno**:
  https://emisoraatlantico.com.co/local/defensoria-del-pueblo-alerta-sobre-crisis-en-el-acceso-a-medicamentos-en-colombia/
- ConsultorSalud — medicamentos desabastecidos y sus causas:
  https://consultorsalud.com/invima-medicamentos-desabastecidos-en-colombia/
- ConsultorSalud — el listado del INVIMA reporta escasez:
  https://consultorsalud.com/listado-invima-reporta-escasez-9-medicamentos/

## Gasto de bolsillo

- Portafolio — el gasto de bolsillo creció 57 % y golpea a hogares pobres y rurales:
  https://www.portafolio.co/economia/gobierno/gasto-de-bolsillo-en-salud-crecio-57-y-golpea-mas-a-hogares-pobres-y-rurales-en-colombia-493111
- La Patria — **desglose por ingresos y por zona rural/urbana**:
  https://www.lapatria.com/salud/aumento-del-gasto-de-bolsillo-en-salud-como-afecta-las-familias-en-colombia-esto-dicen-en
- La FM — gasto de bolsillo y disponibilidad de medicamentos:
  https://www.lafm.com.co/sociedad/medicamentos-pacientes-crisis-salud-gastos-informe-hogares-colombianos-398307
- Telecafé — aumento del 57,3 % en hogares colombianos:
  https://telecafe.gov.co/gasto-en-salud-de-los-hogares-colombianos-aumento-573-y-afecta-mas-a-los-sectores-de-bajos-ingresos/
- Portafolio — **$70,2 billones en salud en 2025 (6,9 % del PIB)**:
  https://www.portafolio.co/economia/gobierno/en-2025-los-hogares-gastaron-10-5-billones-mas-en-salud-que-al-inicio-del-gobierno-petro-488534
- El Tiempo — gasto en salud de los hogares en 2025:
  https://www.eltiempo.com/economia/sectores/el-gasto-en-salud-de-los-hogares-colombianos-siguio-creciendo-en-2025-cuanto-destina-cada-hogar-al-ano-3533064

## Supersalud y quejas

- ⚠️ **Contra-evidencia.** El Heraldo, julio 2026 — la Supersalud reporta una
  **disminución** de quejas por entrega de medicamentos y atención en salud. Va acá a
  propósito: es el dato que corta en contra de la tesis del README y esconderlo sería
  peor que citarlo.
  https://www.elheraldo.co/colombia/2026/07/11/supersalud-reporta-disminucion-de-quejas-por-entrega-de-medicamentos-y-atencion-en-salud/
- El Colombiano — plan de choque nacional por no entrega de medicamentos:
  https://www.elcolombiano.com/colombia/salud/supersalud-plan-choque-medicamentos-eps-colombia-CI31391517
- La FM — más de 514.000 reclamaciones atendidas en 2026:
  https://lafm.com.co/sociedad/crisis-medicamentos-salud-nueva-eps-supersalud-atencion-medica-quejas-reclamos-394315
- Vanguardia — medicamentos sin entregar en Nueva EPS:
  https://www.vanguardia.com/colombia/2026/05/23/supersalud-encontro-mas-medicamentos-sin-entregar-a-usuarios-de-nueva-eps/
- Infobae — quejas más comunes de los pacientes:
  https://www.infobae.com/colombia/2025/01/16/conozca-las-quejas-mas-comunes-de-los-pacientes-en-colombia-el-sistema-de-salud-esta-bajo-la-lupa/
- ConsultorSalud — reclamaciones y PQRS ante la Supersalud:
  https://consultorsalud.com/reclamaciones-sistema-salud-aumentan-supersalud/

## Canal digital y WhatsApp

Sostienen la decisión de canal: por qué WhatsApp y no una app.

- Aurora Inbox — estadísticas de WhatsApp Business 2026 (**94 % de penetración en Colombia**):
  https://www.aurorainbox.com/en/2026/03/01/whatsapp-business-2025-statistics/
- Blip — estadísticas de WhatsApp Business en LATAM 2026 (**62–80 % ya escriben a empresas**):
  https://www.blip.ai/blog/es/whatsapp/estadisticas-whatsapp-marketing-latam/
- Branch — situación digital de Colombia 2025 (**41,1 M usuarios de internet, 97,7 % con smartphone**):
  https://branch.com.co/marketing-digital/situacion-digital-de-colombia-en-el-2025/
- ITSitio — informe DataReportal Colombia 2025:
  https://www.itsitio.com/co/informes/informe-datareportal-colombia-2025-como-y-cuanto-usan-los-colombianos-internet-y-redes-sociales/
- La República — redes sociales más usadas en Colombia:
  https://www.larepublica.co/internet-economy/whatsapp-facebook-e-instagram-lideran-el-listado-de-redes-sociales-mas-usadas-en-el-pais-4256298
- Marketing4ecommerce — estado de la conexión a internet en Colombia:
  https://marketing4ecommerce.co/estado-conexion-a-internet-en-colombia/
- Portafolio — WhatsApp como canal de comercio en Colombia:
  https://www.portafolio.co/tecnologia/whatsapp-se-consolida-como-aliado-clave-del-comercio-electronico-en-colombia-segun-informe-de-e-commerce-489757

---

## Dos notas sobre el uso de estas cifras

Están arriba, con las cifras que califican, para no repetirlas: los **denominadores que no
coinciden** entre la Defensoría y el registro de la Corte, en
[Por qué se cae una tutela](#por-qué-se-cae-una-tutela); los **porcentajes territoriales
que no cuadran** con el total anual, en [Y termina en un juzgado](#y-termina-en-un-juzgado).
