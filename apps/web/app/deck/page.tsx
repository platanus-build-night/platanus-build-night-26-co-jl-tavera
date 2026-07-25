"use client";

// El pitch de tarima: la misma copia de la landing, partida en nueve pantallas que
// se mueven con las flechas. Segundo "use client" del proyecto — el presupuesto de
// "cero JS de aplicación" de DESIGN.md §10 es de `/`, que sigue compilando estática.
//
// Los helpers y los arrays están copiados de `app/page.tsx`, no importados: esa
// página no los exporta y traerlos arrastraría un server component al bundle del
// cliente. Misma decisión que el marco del celular de /demo — si se toca el texto
// de un lado, mirar el otro.

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

const WHATSAPP =
  process.env.NEXT_PUBLIC_WHATSAPP_URL ?? "https://wa.me/12603057633?text=Hola%20Curuba";

type Burbuja = {
  de: "tu" | "curuba";
  texto?: string;
  lineas?: string[];
  foto?: boolean;
};

const CIFRAS = [
  {
    valor: "90 %",
    texto: "de los pacientes no recibe sus medicamentos, o los recibe a medias y con demoras",
  },
  {
    valor: "57,3 %",
    texto: "creció el gasto de bolsillo en salud entre 2022 y 2025 — 61,7 % en zonas rurales",
  },
  {
    valor: "312.500",
    texto: "tutelas en salud en 2025, un 17,8 % más que en 2024",
  },
];

const FUNCIONES: {
  situacion: string;
  titulo: string;
  chat: Burbuja[];
  nota: string;
}[] = [
  {
    situacion: "Si tienes una fórmula",
    titulo: "Qué te toca pagar y qué no",
    chat: [
      { de: "tu", foto: true },
      {
        de: "curuba",
        texto:
          "Leí 3 medicamentos. El losartán y el acetaminofén están financiados con la UPC: los reclamas en el dispensador de tu EPS pagando solo la cuota moderadora, no los compras. El omeprazol no aparece en el listado — confírmalo con tu EPS antes de pagarlo. Si te toca comprarlo, el techo regulado del canal institucional es:",
        lineas: ["Omeprazol 20 mg — oral x 14 → $6.100"],
      },
    ],
    nota: "Cifras ilustrativas. La cobertura sale del PBS y el techo del corte de SISMED, por presentación y no por unidad.",
  },
  {
    situacion: "Si estás esperando",
    titulo: "Qué dice el INVIMA, no tu EPS",
    chat: [
      { de: "tu", texto: "¿el losartán está desabastecido?" },
      {
        de: "curuba",
        texto:
          "El INVIMA lo tiene en seguimiento con estado desabastecido desde el último corte. Si en tu droguería no lo consiguen, tu EPS sigue obligada a garantizarte el tratamiento — puede ser con otra presentación o por otro proveedor.",
      },
    ],
    nota: "Esta es la consulta que define si el problema es del país o es de tu EPS.",
  },
  {
    situacion: "Si te lo negaron o te demoran",
    titulo: "El escrito que procede, en PDF",
    chat: [
      {
        de: "tu",
        texto:
          "llevo tres semanas yendo a la farmacia y no me entregan el losartán, quiero poner una tutela ya",
      },
      {
        de: "curuba",
        texto:
          "Si no recibes el losartán ya, ¿corre riesgo tu vida o tu salud de forma grave?",
      },
      { de: "tu", texto: "no, es para la tensión. no he radicado nada" },
      {
        de: "curuba",
        texto:
          "Entonces lo que procede es un derecho de petición ante tu EPS, no la tutela: como todavía no le has pedido nada por escrito, este es el paso que toca primero y deja el radicado con fecha que sostiene la tutela después.",
      },
      {
        de: "curuba",
        texto:
          "Aquí está tu derecho de petición 📎 La ley le da a la EPS 15 días hábiles; si no responde, ya con esa constancia sí procede la tutela.",
      },
    ],
    nota: "Cuatro escritos: derecho de petición, tutela, incidente de desacato y demanda ante la Supersalud. Cuál procede lo decide una tabla en Python, no el modelo (Ley 1755 de 2015, art. 14 · art. 86 C.P. · Decreto 2591 de 1991).",
  },
];

const FUENTES = [
  {
    nombre: "PBS",
    entidad: "Resolución 2808 de 2022",
    aporta: "Qué está financiado con la UPC — o sea qué no te toca pagar",
    corte: "corte 2026-07-24",
    filas: "2.067 medicamentos",
  },
  {
    nombre: "SISMED",
    entidad: "MinSalud / SISPRO",
    aporta: "Techos de precio de la Circular CNPMDM",
    corte: "corte 2026-07-24",
    filas: "38.731 medicamentos",
  },
  {
    nombre: "INVIMA",
    entidad: "Listado de abastecimiento",
    aporta: "Estado de seguimiento por principio activo",
    corte: "corte mayo 2026",
    filas: "783 medicamentos",
  },
];

const PRECISIONES = [
  {
    titulo: "«No lo encontré» no es «no está cubierto»",
    texto:
      "El listado del PBS no es exhaustivo y el cruce por principio activo con SISMED solo alcanza el 72,5 %. Si Curuba no lo encuentra lo dice así y manda a confirmar con la EPS, nunca que hay que comprarlo: ese falso negativo es el que hace que alguien pague de su bolsillo algo que le correspondía.",
  },
  {
    titulo: "Es el techo institucional, no el precio del mostrador",
    texto:
      "El precio de venta final al público está regulado en 4 de las 38.731 filas del SISMED; en el resto dice «No regulado». Curuba dice cuál es el techo del canal institucional, que sí está respaldado, y sirve para saber si lo que te están pidiendo está fuera de rango.",
  },
  {
    titulo: "«No desabastecido» no es lo mismo que «no aparece»",
    texto:
      "Al primero el INVIMA le hizo seguimiento y lo cerró — son 373 de las 783 filas. Al que no aparece nunca lo miró. Que no esté en la lista no significa que haya en tu barrio, y Curuba sostiene esa diferencia al responder.",
  },
];

function IconoWhatsApp({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor">
      <path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 18.15h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 2.2 0 4.27.86 5.83 2.42a8.2 8.2 0 0 1 2.41 5.83c0 4.54-3.7 8.23-8.24 8.23Zm4.52-6.17c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.24-.64.8-.78.97-.15.16-.29.18-.53.06-.25-.13-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.5.11-.11.25-.29.37-.44.13-.15.17-.25.25-.42.08-.16.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48c-.16 0-.43.06-.65.31-.22.25-.85.84-.85 2.04 0 1.2.87 2.36.99 2.52.12.16 1.71 2.61 4.14 3.66.58.25 1.03.4 1.38.51.58.19 1.11.16 1.53.1.47-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.22-.16-.47-.29Z" />
    </svg>
  );
}

function FotoFormula() {
  return (
    <div className="trazo w-32 rounded-lg bg-crema p-2">
      <div className="space-y-1">
        <div className="h-1 w-full rounded-full bg-monte/70" />
        <div className="h-1 w-4/5 rounded-full bg-monte/70" />
        <div className="h-1 w-full rounded-full bg-monte/70" />
        <div className="h-1 w-2/3 rounded-full bg-monte/70" />
      </div>
      <p className="mt-2 font-mono text-[9px] uppercase tracking-wide text-monte/70">
        fórmula.jpg
      </p>
    </div>
  );
}

function Burbujas({ chat, animada = false }: { chat: Burbuja[]; animada?: boolean }) {
  return (
    <div className="space-y-2">
      {chat.map((b, i) => (
        <div
          key={i}
          className={`flex ${b.de === "tu" ? "justify-end" : "justify-start"} ${
            animada ? "entra" : ""
          }`}
          style={animada ? { animationDelay: `${700 + i * 400}ms` } : undefined}
        >
          <div
            className={`trazo max-w-[85%] rounded-2xl px-3 py-2 text-[13px] leading-snug text-monte ${
              b.de === "tu" ? "bg-hoja" : "bg-white"
            }`}
          >
            {b.foto ? <FotoFormula /> : null}
            {b.texto ? <p>{b.texto}</p> : null}
            {b.lineas ? (
              <ul className="mt-1.5 space-y-0.5 font-mono text-[11px]">
                {b.lineas.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function Telefono({ chat, animada = false }: { chat: Burbuja[]; animada?: boolean }) {
  return (
    <div className="trazo sombra flex h-[clamp(15rem,50svh,30rem)] w-[300px] shrink-0 flex-col rounded-[2rem] bg-monte p-2">
      <div className="trazo flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.5rem] bg-crema">
        <div className="flex shrink-0 items-center gap-2 border-b-[3px] border-monte bg-hoja px-3 py-2">
          <IconoWhatsApp className="h-5 w-5 text-monte" />
          <div>
            <p className="text-sm font-semibold leading-none text-monte">Curuba</p>
            <p className="mt-1 font-mono text-[10px] leading-none text-monte/80">en línea</p>
          </div>
        </div>
        <div className="min-h-0 flex-1 p-3">
          <Burbujas chat={chat} animada={animada} />
        </div>
      </div>
    </div>
  );
}

// Rótulo mono de cada lámina. Toma la tinta del fondo en que cae: sobre monte la
// tinta es crema, sobre curuba y crema es monte.
function Rotulo({ children, claro = false }: { children: React.ReactNode; claro?: boolean }) {
  return (
    <p
      className={`font-mono text-xs uppercase tracking-[0.18em] ${
        claro ? "text-crema/70" : "text-monte/70"
      }`}
    >
      {children}
    </p>
  );
}

const CTA = (
  <a
    href={WHATSAPP}
    className="cta trazo sombra inline-flex items-center gap-3 rounded-full bg-monte px-7 py-4 text-lg font-semibold text-white transition-transform hover:-translate-y-0.5"
  >
    <IconoWhatsApp className="h-5 w-5" />
    Escríbele por WhatsApp
  </a>
);

// Nueve láminas. El fondo alterna porque la paleta pasa AA en las dos direcciones
// (globals.css) — un deck de nueve pantallas del mismo color no se sostiene.
//
// Los tamaños grandes van con `min(Nvw, Msvh)` adentro del clamp, no con `vw` a
// secas como en la landing. La landing crece hacia abajo y el alto le da igual;
// acá cada lámina tiene que caber entera en la ventana, y un proyector de 1280
// de ancho puede traer 720 de alto o menos. Con `vw` solo, el titular se pasa de
// largo justo en la pantalla donde nadie lo puede arreglar.
const SLIDES: { fondo: string; nodo: React.ReactNode }[] = [
  // 1 · Portada
  {
    fondo: "bg-curuba",
    nodo: (
      <div className="flex h-full flex-col justify-center">
        <div className="flex items-center gap-3">
          <Image src="/project-logo.png" alt="" width={56} height={56} priority className="h-10 w-10" />
          <span className="font-display text-2xl font-extrabold tracking-tight text-monte">
            Curuba
          </span>
        </div>
        <div className="mt-8">
          <Rotulo>Agente de WhatsApp · Colombia</Rotulo>
        </div>
        <h1 className="mt-4 max-w-[19ch] text-balance font-display text-[clamp(2rem,min(5.8vw,9.4svh),5rem)] font-extrabold leading-[0.94] tracking-[-0.035em] text-monte">
          Reducimos el gasto de bolsillo de los colombianos en medicamentos.
          <span className="mt-3 block text-[0.42em] text-monte/75">Gratis, por WhatsApp.</span>
        </h1>
        <div className="mt-8">{CTA}</div>
      </div>
    ),
  },

  // 2 · Qué hace
  {
    fondo: "bg-curuba",
    nodo: (
      <div className="flex h-full flex-col items-center justify-center gap-10 lg:flex-row lg:gap-16">
        <div className="max-w-[34ch]">
          <Rotulo>Qué hace</Rotulo>
          <p className="mt-5 text-[clamp(1rem,min(2.1vw,3.4svh),1.9rem)] leading-tight text-monte">
            ¿Cuánto debería costar tu medicamento? ¿Y qué hacer si tu EPS no te lo entrega?
            Manda una foto de tu fórmula o del producto: te decimos si te toca pagarlo y
            cuánto, si está desabastecido, y te armamos el reclamo listo para radicar.
            Gratis.
          </p>
        </div>
        <Telefono
          animada
          chat={[
            { de: "tu", foto: true },
            {
              de: "curuba",
              texto: "Leí 3 medicamentos. Dos los cubre tu EPS: esos no los compras.",
              lineas: [
                "Acetaminofén 500 mg → cubierto",
                "Losartán 50 mg → cubierto",
                "Omeprazol 20 mg → $6.100",
              ],
            },
          ]}
        />
      </div>
    ),
  },

  // 3 · El problema
  {
    fondo: "bg-monte",
    nodo: (
      <div className="flex h-full flex-col justify-center">
        <Rotulo claro>El problema</Rotulo>
        <div className="mt-10 grid gap-10 sm:grid-cols-3 sm:gap-8">
          {CIFRAS.map((c) => (
            <div key={c.valor}>
              <p className="font-display text-[clamp(2.4rem,min(7.5vw,15svh),6rem)] font-extrabold leading-none tracking-tight text-curuba">
                {c.valor}
              </p>
              <p className="mt-4 max-w-[32ch] text-lg leading-snug text-white">{c.texto}</p>
            </div>
          ))}
        </div>
        <p className="mt-12 max-w-[76ch] font-mono text-[11px] uppercase leading-relaxed tracking-[0.14em] text-crema/70">
          Defensoría del Pueblo, 2025 — encuesta en puntos de dispensación (n=3.449) ·
          Afidro / Algebra Labs sobre datos DANE. La variación de 2025 es 17,8 % contra la
          serie de 265.173 tutelas, no el 17,92 % que titula la prensa sobre una base
          redondeada.
        </p>
      </div>
    ),
  },

  // 4 · Titular de las tres funciones
  {
    fondo: "bg-monte",
    nodo: (
      <div className="flex h-full flex-col justify-center">
        <h2 className="max-w-[20ch] font-display text-[clamp(1.9rem,min(5.6vw,10svh),4.6rem)] font-extrabold leading-[1.02] tracking-[-0.03em] text-white">
          Tres caminos, uno por cada salida que te queda
        </h2>
        <p className="mt-6 max-w-[52ch] text-[clamp(1rem,min(2.2vw,3.6svh),1.6rem)] leading-snug text-crema/90">
          El medicamento está formulado, está cubierto y su entrega es un derecho. Cuando
          no llega, Curuba responde en el único canal que ya tienes abierto.
        </p>
      </div>
    ),
  },

  // 5-7 · Una por función
  ...FUNCIONES.map((f) => ({
    fondo: "bg-crema",
    nodo: (
      <div className="flex h-full flex-col justify-center gap-8 lg:flex-row lg:items-center lg:gap-16">
        <div className="lg:max-w-[26ch]">
          <Rotulo>{f.situacion}</Rotulo>
          <h2 className="mt-4 font-display text-[clamp(1.6rem,min(4.6vw,8svh),3.6rem)] font-extrabold leading-[1.02] tracking-[-0.03em] text-monte">
            {f.titulo}
          </h2>
          <p className="mt-6 max-w-[46ch] border-t border-monte/20 pt-4 font-mono text-xs leading-relaxed text-monte/70">
            {f.nota}
          </p>
        </div>
        <div className="trazo sombra w-full max-w-[26rem] shrink-0 rounded-3xl bg-white/60 p-4">
          <Burbujas chat={f.chat} />
        </div>
      </div>
    ),
  })),

  // 8 · Los datos
  {
    fondo: "bg-monte",
    nodo: (
      <div className="flex h-full flex-col justify-center">
        <h2 className="max-w-[18ch] font-display text-[clamp(1.6rem,min(4vw,7svh),3.25rem)] font-extrabold leading-[1.02] tracking-[-0.03em] text-white">
          De dónde salen los datos
        </h2>
        <p className="mt-3 max-w-[52ch] text-sm leading-snug text-crema/90">
          De tres fuentes públicas, congeladas en un corte que queda escrito. Ningún precio
          sale de un modelo.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {FUENTES.map((f) => (
            <article key={f.nombre} className="trazo sombra rounded-3xl bg-curuba p-4">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="font-display text-2xl font-extrabold tracking-tight text-monte">
                  {f.nombre}
                </h3>
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-monte/70">
                  {f.corte}
                </p>
              </div>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-monte/70">
                {f.entidad}
              </p>
              <p className="mt-2 text-sm leading-snug text-monte">{f.aporta}</p>
              <p className="mt-2 font-display text-lg font-bold text-monte">{f.filas}</p>
            </article>
          ))}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {PRECISIONES.map((p) => (
            <article key={p.titulo} className="rounded-3xl border-[3px] border-crema/30 px-4 py-3">
              <h3 className="font-display text-base font-bold leading-tight text-curuba">
                {p.titulo}
              </h3>
              <p className="mt-2 text-xs leading-snug text-crema/90">{p.texto}</p>
            </article>
          ))}
        </div>
      </div>
    ),
  },

  // 9 · Aviso legal y cierre
  {
    fondo: "bg-curuba",
    nodo: (
      <div className="flex h-full flex-col justify-center">
        <Rotulo>Aviso legal</Rotulo>
        <p className="mt-4 max-w-[68ch] text-[clamp(0.95rem,min(2vw,3.2svh),1.5rem)] leading-snug text-monte">
          Curuba <strong>no da asesoría médica ni jurídica</strong>. Los precios son techos
          regulados del SISMED para el canal institucional, no lo que cobra un punto de
          venta. El estado de desabastecimiento es el del último corte publicado por el
          INVIMA y puede haber cambiado. Que un medicamento no aparezca en el listado del
          PBS no significa que no esté cubierto. Los escritos legales que genera son{" "}
          <strong>borradores que deben revisarse antes de radicarse</strong>.
        </p>
        <div className="mt-10">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-monte/70">
            Con datos públicos de
          </p>
          <p className="mt-1.5 font-display text-xl font-bold text-monte">
            PBS <span className="font-normal text-monte/60">(MinSalud)</span> · SISMED ·
            INVIMA
          </p>
        </div>
        <div className="mt-10 flex flex-wrap items-center gap-6">
          {CTA}
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-monte/70">
            Curuba · Platanus Build Night 2026 · Bogotá
          </p>
        </div>
      </div>
    ),
  },
];

export default function Deck() {
  const [i, setI] = useState(0);
  const ultima = SLIDES.length - 1;

  // Se corta en los extremos, no da la vuelta: en tarima uno no quiere volver a la
  // portada por pasarse una flecha.
  const mover = useCallback(
    (paso: number) => setI((n) => Math.min(ultima, Math.max(0, n + paso))),
    [ultima],
  );

  useEffect(() => {
    function tecla(e: KeyboardEvent) {
      // Los mandos de presentación mandan PageDown/PageUp, no flechas.
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
        e.preventDefault();
        mover(1);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        mover(-1);
      } else if (e.key === "Home") {
        setI(0);
      } else if (e.key === "End") {
        setI(ultima);
      }
    }
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [mover, ultima]);

  const slide = SLIDES[i];

  return (
    <main className="grid h-svh place-items-center bg-monte p-3 sm:p-6">
      <section
        className={`trazo sombra flex h-full w-full max-w-[1400px] flex-col overflow-hidden rounded-[28px] ${slide.fondo}`}
        aria-live="polite"
      >
        {/* `key` remonta la lámina para que `entra` corra en cada cambio. */}
        <div key={i} className="entra sin-barra min-h-0 flex-1 overflow-y-auto px-6 py-6 sm:px-12">
          {slide.nodo}
        </div>

        <nav className="flex shrink-0 items-center justify-between gap-4 px-6 pb-5 sm:px-12">
          <div className="flex items-center gap-2">
            {SLIDES.map((_, n) => (
              <button
                key={n}
                onClick={() => setI(n)}
                aria-label={`Ir a la lámina ${n + 1}`}
                aria-current={n === i}
                className={`h-2.5 w-2.5 rounded-full border-2 border-current ${
                  slide.fondo === "bg-monte" ? "text-crema" : "text-monte"
                } ${n === i ? "bg-current" : ""}`}
              />
            ))}
          </div>
          <div className="flex items-center gap-4">
            <p
              className={`font-mono text-xs tracking-[0.14em] ${
                slide.fondo === "bg-monte" ? "text-crema/70" : "text-monte/70"
              }`}
            >
              {String(i + 1).padStart(2, "0")} / {String(SLIDES.length).padStart(2, "0")}
            </p>
            <button
              onClick={() => mover(-1)}
              disabled={i === 0}
              aria-label="Lámina anterior"
              className="trazo sombra-sm grid h-11 w-11 place-items-center rounded-full bg-crema text-2xl leading-none text-monte disabled:opacity-35 disabled:shadow-none"
            >
              ‹
            </button>
            <button
              onClick={() => mover(1)}
              disabled={i === ultima}
              aria-label="Lámina siguiente"
              className="trazo sombra-sm grid h-11 w-11 place-items-center rounded-full bg-curuba text-2xl leading-none text-monte disabled:opacity-35 disabled:shadow-none"
            >
              ›
            </button>
          </div>
        </nav>
      </section>
    </main>
  );
}
