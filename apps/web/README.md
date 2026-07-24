# Curuba — Landing

La página pública. Explica qué hace Curuba y manda a la gente al WhatsApp. Es una sola
página: no hay login, ni dashboard, ni backend propio — todo el producto vive en el chat.

> **Estado: sin implementar.** Esta carpeta es el spec.

## Stack

Next.js (App Router) + Tailwind, desplegado en Vercel. No consume la API: el único
"llamado a la acción" es un enlace `wa.me`.

## Estructura planeada

```
apps/web/
├── package.json
├── next.config.ts
├── .env.local
└── app/
    ├── layout.tsx      # metadata, og:image con project-logo.png, fuente
    ├── page.tsx        # la página entera
    └── globals.css     # Tailwind
```

## Secciones de la página

1. **Hero** — el nombre, la frase de una línea ("Sabé cuánto debería costar tu fórmula") y
   el botón de WhatsApp. El botón es lo único que importa arriba del fold.
2. **Las tres funciones** — una tarjeta por función, cada una con un intercambio real de
   WhatsApp como ejemplo. Los ejemplos convencen más que la descripción:
   - foto de la fórmula → lista de medicamentos con precios
   - "¿el losartán está desabastecido?" → declaratoria del INVIMA
   - "me negaron el medicamento" → entrevista → PDF de la tutela
3. **De dónde salen los datos** — SISMED (MinSalud, corte 2026-07-24) e INVIMA (mayo
   2026). Esto es lo que hace creíbles los precios; no esconderlo en un pie de página.
   Y decir con precisión **qué precio es**: el techo regulado del canal institucional, no
   lo que cobra la droguería. El precio de venta final al público está regulado en 4
   medicamentos de 38.731, así que prometer eso sería mentira. Vale más ser exacto aquí
   que sonar bien.
4. **Aviso legal** — visible, no en letra chiquita.

El diseño puede reusar los ejemplos de conversación que ya están escritos en el
[README raíz](../../README.md).

## Variables de entorno

| Variable | Para qué |
|---|---|
| `NEXT_PUBLIC_WHATSAPP_URL` | El enlace `wa.me` con el número y un texto prellenado |

El número no va hardcodeado en el JSX: durante el hackathon puede cambiar, y si está en
el entorno se cambia en Vercel sin volver a desplegar código.

## Cómo correrlo

```bash
cd apps/web
npm install
npm run dev
```

## Deploy en Vercel

**Vercel no se puede conectar a este repo.** Es de la organización
`platanus-build-night` y las plataformas de deploy solo acceden a repos propios. Hay que
espejar a un repo personal y conectar Vercel a ese — las instrucciones de doble remote
están en el [README raíz](../../README.md#deploying-vercel-render-etc).

En el proyecto de Vercel, poner el **Root Directory** en `apps/web`; si no, el build
falla porque no encuentra el `package.json` en la raíz.

## Aviso legal

El aviso tiene que aparecer **en la página**, no solo en el repo: Curuba no da asesoría
médica ni jurídica, los precios son de referencia del SISMED, y la tutela que genera es
un borrador que debe revisarse antes de radicarse.
