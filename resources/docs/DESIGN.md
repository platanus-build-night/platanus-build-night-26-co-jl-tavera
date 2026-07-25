# Diseño de Curuba

El sistema visual de la landing: de dónde sale cada color, qué hace cada tipografía y por
qué se descartó lo obvio. Escrito para que una segunda pantalla —el PDF de la tutela, un
mensaje de WhatsApp— se pueda dibujar igual sin adivinar.

Los tokens viven en [`apps/web/app/globals.css`](../../apps/web/app/globals.css) y su uso
en [`apps/web/app/page.tsx`](../../apps/web/app/page.tsx). Este documento explica el
porqué; ese código es la verdad. Cada sección marcada con ⚠️ es una trampa que ya costó
tiempo una vez.

---

## 1. De dónde sale todo: el logo

[`project-logo.png`](../../project-logo.png) es una curuba dibujada estilo sticker: verde
oscuro delineando rellenos planos, amarillo en la cáscara, y la fruta partida mostrando
corona clara con centro naranja.

Las tres decisiones que sostienen la página salen de ahí y de nada más:

| Del logo | A la página |
|---|---|
| Contorno verde oscuro sobre relleno plano | La paleta y el trazo de 3 px |
| Sin degradados, sin sombras difusas | Sombra sólida desplazada, nunca blur |
| El corte transversal de la fruta | Los anillos detrás del teléfono |

No hay ningún color, forma ni recurso inventado por fuera de esa imagen. Cuando haya que
agregar algo, el sitio donde buscarlo es el logo, no una paleta de moda.

---

## 2. Color

Cinco tokens. Van en `@theme` y **no** en `@theme inline`, para que `var(--color-monte)`
sirva también en CSS suelto y no solo en las utilidades de Tailwind.

| Token | Hex | Para qué |
|---|---|---|
| `monte` | `#123d22` | Fondo de página, tinta, contornos |
| `curuba` | `#f5d76e` | Tarjeta del hero, tarjetas de fuentes, aviso legal |
| `pulpa` | `#f5a623` | Centro del corte, acentos |
| `hoja` | `#5cb246` | Chrome de WhatsApp, burbuja saliente |
| `crema` | `#fbf3d9` | Tarjetas de lectura larga, burbujas entrantes |

### Contraste medido

| Par | Ratio | Nivel |
|---|---|---|
| blanco sobre `monte` | 12,24:1 | AAA |
| `monte` sobre `crema` | 11,03:1 | AAA |
| `monte` sobre `curuba` | 8,64:1 | AAA |
| `monte` sobre `pulpa` | 6,04:1 | AA |
| `monte` sobre `hoja` | 4,61:1 | AA |

> ⚠️ **La regla que hace barata esta paleta: pasa AA en las dos direcciones.** Tinta sobre
> relleno y relleno sobre tinta. Por eso se puede invertir el esquema entre secciones —la
> tarjeta amarilla con tinta verde, la banda de cifras con tinta amarilla sobre verde— sin
> volver a medir nada. Si se agrega un sexto color, la condición para aceptarlo es que
> cumpla lo mismo.

Para recalcular al agregar un color, luminancia relativa de WCAG 2.1:

```js
const L = h => {
  const c = [1, 3, 5]
    .map(i => parseInt(h.slice(i, i + 2), 16) / 255)
    .map(v => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => {
  const [x, y] = [L(a), L(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
```

---

## 3. Por qué no es blanco sobre naranja

La referencia visual de la que salió el hero ([turn.io](https://www.turn.io)) usa texto
blanco sobre un naranja fuerte. Con los colores del logo eso **no se puede sostener**, y
los números quedan acá para que no se vuelva a proponer:

| Intento | Ratio | Veredicto |
|---|---|---|
| Blanco sobre `#f5a623` — el naranja del logo | **2,03:1** | Ilegible |
| Blanco sobre `#ff5c33` — el naranja del inspo | 3,07:1 | Falla en cuerpo de texto |
| Blanco sobre `#e2571f` — naranja profundo | 3,74:1 | Solo pasa en titular grande |
| **`monte` sobre `#f5d76e`** | **8,64:1** | **El elegido** |

Las tres primeras filas obligan a bajar el cuerpo de texto a otro color, o a aceptar que no
se lea. Y esa es la consecuencia de producto: **el lector es un paciente con el celular al
sol**, leyendo un párrafo sobre por qué el precio que ve no es el del mostrador. El cuerpo
tiene que pasar AA, no solo el titular.

Invertir la tinta —verde oscuro sobre amarillo— resuelve el contraste y además es
literalmente cómo está dibujado el logo.

---

## 4. Tipografía

Tres roles, tres familias. Todas por `next/font/google`: self-hosted en el build, `display:
swap`, **cero requests a Google en runtime**.

| Rol | Familia | Variable CSS | Dónde |
|---|---|---|---|
| Display | Bricolage Grotesque (variable) | `--font-display` | h1, cifras, títulos de sección |
| Cuerpo | Instrument Sans | `--font-body` | Párrafos, burbujas de chat |
| Datos | IBM Plex Mono | `--font-mono` | Eyebrows, atribuciones, cortes, conteos |

`@theme inline` las convierte en `font-display`, `font-body` y `font-mono`. Va `inline`
—al revés que los colores— porque el valor es una variable que define `next/font` sobre el
`<html>`, y sin `inline` Tailwind emitiría una indirección que no resuelve.

### La monoespaciada no es decorativa

Marca **lo que viene de un dataset público**: el corte de SISMED, las 38.731 filas, las 783
del INVIMA, la atribución de la Defensoría con su `n=3.449`. Separa el dato de la
afirmación, que es la misma distinción que el repo sostiene en todo lo demás.

**Si un texto en mono no es un dato rastreable hasta una fuente, está mal puesto.** Es la
regla de uso; no es una decisión de textura.

### Escala

Todo en `clamp()`, sin breakpoints para el tamaño de letra:

| Elemento | Valor |
|---|---|
| h1 del hero | `clamp(2.4rem, 5vw, 4.5rem)` |
| Cifras de la banda | `clamp(3rem, 6vw, 4.5rem)` |
| Títulos de sección | `clamp(2rem, 4vw, 3.25rem)` |

> ⚠️ **El h1 estuvo en `clamp(2.6rem, 7.5vw, 5.5rem)` y no cabía.** A 1850 px de ancho eso
> da 88 px por línea; con tres líneas más subtítulo y CTA, el hero se pasaba de la altura de
> la ventana. El tope de `4.5rem` no es estético: es lo que permite que la primera pantalla
> cierre.

---

## 5. El trazo de sticker

Tres utilidades en `globals.css`:

| Utilidad | Valor |
|---|---|
| `trazo` | `border: 3px solid var(--color-monte)` |
| `sombra` | `box-shadow: 6px 6px 0 var(--color-monte)` |
| `sombra-sm` | `box-shadow: 3px 3px 0 var(--color-monte)` |

**Regla de aplicación: solo a los objetos.** Teléfono, tarjetas, burbujas y el pill del
CTA. Nunca a texto, divisores, ni a la banda de cifras — esa va suelta sobre el mat verde,
sin tarjeta, y ese respiro es lo que evita que la página entera se sienta encerrada.

Sin blur y sin degradados en ningún lado. El logo no los tiene.

---

## 6. El elemento firma: el corte de la curuba

Detrás del teléfono, dos círculos concéntricos —`crema` por fuera a `34rem`, `pulpa` adentro
a `21rem`, los dos con `trazo`— que leen dos veces: es la fruta partida del logo y es la
onda del mensaje que sale.

Es la única cosa de la que la página se acuerda. Todo lo demás alrededor se mantiene quieto
a propósito.

> ⚠️ **Van anidados, no como dos `absolute` independientes.** La primera versión los tenía
> colgando de un ancla de tamaño cero pegada al borde de la tarjeta, cada uno con su propio
> `bottom` negativo, y salían descuadrados: uno se fugaba por el borde derecho y el otro
> asomaba arriba del teléfono como un arco suelto. Anidando el naranja **dentro** del crema
> con `grid place-items-center`, quedan concéntricos por construcción — no hay dos
> posiciones que mantener de acuerdo cuando cambie el tamaño del teléfono.

---

## 7. Movimiento

Una sola secuencia de entrada, en CSS, sin librería y sin `"use client"`:

| Momento | Retardo |
|---|---|
| Eyebrow → h1 → subtítulo → CTA → fuentes → teléfono | `0 · 60 · 120 · 180 · 240 · 300 ms` |
| Burbujas dentro del teléfono | `700 + i × 400 ms` |

Las burbujas son **el único momento orquestado**: la foto de la fórmula entra y la respuesta
con los precios aparece después. Es el producto haciendo lo suyo, no un adorno.

Los anillos no se mueven. Ya hay una cosa animada en pantalla; dos serían ruido.

> ⚠️ **`animation-fill-mode: both` esconde el contenido hasta que la animación corre.** Por
> eso el bloque de `prefers-reduced-motion` **no** pone `animation: none` —eso dejaría la
> página en blanco para quien pidió menos movimiento, que es el peor resultado posible—
> sino que baja duración y retardo a ~0. El fotograma final queda puesto y la página
> aparece completa de una vez.

---

## 8. Foco

`:focus-visible` usa `currentColor`, que por construcción ya contrasta con su fondo: si el
texto se lee, su anillo de foco también.

> ⚠️ **El CTA es la excepción y necesita una regla propia.** Es texto blanco sobre verde,
> así que `currentColor` sería blanco — y el anillo cae **por fuera** del pill, sobre el
> amarillo de la tarjeta. Blanco sobre `curuba` es 1,42:1: invisible. Por eso `.cta` fuerza
> `outline-color: var(--color-monte)`.

El resto del piso de calidad: objetivos táctiles de 44 px o más, `lang="es-CO"`, y contraste
verificado en la tabla de arriba.

---

## 9. Reglas de estructura que parecen de estilo

Tres decisiones que se ven visuales pero son de contenido. Se documentan porque la próxima
persona que abra la página va a querer "arreglarlas".

**Las tres funciones no van numeradas.** Un `01 / 02 / 03` diría que son pasos de un
proceso, y no lo son: son los tres caminos que le quedan al paciente —comprarlo, esperar,
tutelar— y son independientes. Por eso cada tarjeta rotula la situación en la que está
parado quien lee: *Si vas a comprarlo* · *Si estás esperando* · *Si te lo negaron*.

**No hay barra de navegación.** Es una sola página sin login. Cinco links y un "Sign up"
como los del inspo serían decorado mentiroso. En móvil se cae además el botón de arriba: el
CTA del hero queda a un dedo de distancia y competían entre sí.

**El slot de «In partnership with: Meta · WHO» del inspo** lo ocupa **«Con datos públicos
de: SISMED (MinSalud) · INVIMA»**. Misma jerarquía visual, contenido cierto — y es
justamente la señal de credibilidad que el spec pide no esconder en un pie de página.

---

## 10. Presupuesto técnico

La página **no manda JavaScript de aplicación**. Ni un `"use client"`, ni estado, ni
efectos, ni librería de animación: los datos son arrays a nivel de módulo, el movimiento es
CSS, y la ruta compila `○ (Static)`.

No es purismo. El lector real es un paciente con un Android de gama media y datos móviles,
y esta página existe para mandarlo a WhatsApp lo más rápido posible. **Cualquier cosa que se
agregue debería poder seguir diciendo lo mismo**; si algo obliga a un componente de cliente,
esa es la conversación que hay que tener antes de escribirlo.

---

## Aviso legal

Va **en la página**, visible y no en letra chiquita: Curuba no da asesoría médica ni
jurídica, los precios son techos regulados del canal institucional del SISMED y no lo que
cobra un punto de venta, y la tutela es un borrador que debe revisarse antes de radicarse.
Ese bloque no se quita ni se achica por razones de composición.
