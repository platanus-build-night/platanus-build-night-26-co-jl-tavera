import Image from "next/image";

// El botón es lo único que importa arriba del fold, así que no puede depender
// de que la variable esté bien puesta en Railway: si falta, cae al número real.
const WHATSAPP =
  process.env.NEXT_PUBLIC_WHATSAPP_URL ?? "https://wa.me/12603057633?text=Hola%20Curuba";

const REPO = "https://github.com/platanus-build-night/platanus-build-night-26-co-jl-tavera";

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
    valor: "312.500",
    texto: "tutelas en salud en 2025, un 17,8 % más que en 2024",
  },
  {
    valor: "74,3 %",
    texto: "de las tutelas se conceden: el juez le da la razón al paciente",
  },
];

// No van numeradas. No son tres pasos de un proceso: son los tres caminos que
// tiene el paciente cuando no le entregan el medicamento, y el rótulo dice en
// cuál está parado quien lee.
const FUNCIONES: {
  situacion: string;
  titulo: string;
  chat: Burbuja[];
  nota: string;
}[] = [
  {
    situacion: "Si vas a comprarlo",
    titulo: "Fórmula → precio regulado",
    chat: [
      { de: "tu", foto: true },
      {
        de: "curuba",
        texto:
          "Encontré 3 medicamentos en tu fórmula. Estos son los techos de precio regulados del canal institucional (Circular CNPMDM), no lo que te va a cobrar la droguería:",
        lineas: [
          "Acetaminofén 500 mg — oral x 100 → $12.400",
          "Losartán 50 mg — oral x 30 → $8.900",
          "Omeprazol 20 mg — oral x 14 → $6.100",
        ],
      },
    ],
    nota: "Cifras ilustrativas. Los valores reales salen del corte de SISMED, y el techo es por presentación, no por unidad.",
  },
  {
    situacion: "Si estás esperando",
    titulo: "¿Está desabastecido?",
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
    situacion: "Si te lo negaron",
    titulo: "Tutela → PDF",
    chat: [
      { de: "curuba", texto: "¿Contra qué EPS es la tutela?" },
      { de: "tu", texto: "Sanitas" },
      { de: "curuba", texto: "¿Qué medicamento o servicio te negaron?" },
      { de: "tu", texto: "el losartán, llevo 3 semanas yendo" },
      {
        de: "curuba",
        texto:
          "Listo, aquí está tu tutela 📎 Revísala antes de radicarla — sobre todo los datos personales y las fechas.",
      },
    ],
    nota: "Es gratuita, no requiere abogado y el juez falla en 10 días (art. 86 C.P. · Decreto 2591 de 1991, art. 29).",
  },
];

const FUENTES = [
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

// Un rectángulo con cuatro renglones: la foto de la fórmula, sin cargar una
// imagen y sin inventarle los datos a un paciente.
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

function Telefono({
  chat,
  animada = false,
  className = "",
}: {
  chat: Burbuja[];
  animada?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`trazo sombra flex w-[300px] flex-col rounded-[2rem] bg-monte p-2 sm:w-[340px] ${className}`}
    >
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

export default function Home() {
  return (
    <main className="min-h-screen bg-monte p-3 sm:p-4 lg:p-6">
      <div className="mx-auto flex max-w-[1400px] flex-col">
        {/* ── Hero ───────────────────────────────────────────────────────── */}
        {/* La tarjeta llena exactamente la ventana en desktop: 100svh menos el
            padding del mat. En móvil se deja crecer con el contenido — forzar
            la altura ahí solo aprieta el texto. */}
        <section className="trazo sombra relative flex flex-col overflow-hidden rounded-[28px] bg-curuba lg:min-h-[calc(100svh-3rem)]">
          {/* En móvil solo la marca, centrada: el botón de arriba competía con
              el CTA del hero, que queda a un dedo de distancia. */}
          <header className="flex shrink-0 items-center justify-center gap-4 px-5 py-4 sm:justify-between sm:px-8">
            <div className="flex items-center gap-2">
              <Image
                src="/project-logo.png"
                alt=""
                width={40}
                height={40}
                priority
                className="h-9 w-9"
              />
              <span className="font-display text-2xl font-extrabold tracking-tight text-monte">
                Curuba
              </span>
            </div>
            <a
              href={WHATSAPP}
              className="cta trazo sombra-sm hidden items-center gap-2 rounded-full bg-monte px-4 py-2 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 sm:flex"
            >
              <IconoWhatsApp className="h-4 w-4" />
              WhatsApp
            </a>
          </header>

          <div className="grid flex-1 items-end gap-8 px-5 pt-6 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:gap-4 lg:pt-8">
            <div className="pb-8 lg:pb-12">
              <p
                className="entra font-mono text-xs uppercase tracking-[0.18em] text-monte/80"
                style={{ animationDelay: "0ms" }}
              >
                Agente de WhatsApp · Colombia
              </p>
              <h1
                className="entra mt-4 max-w-[14ch] text-balance font-display text-[clamp(2.4rem,5vw,4.5rem)] font-extrabold leading-[0.94] tracking-[-0.035em] text-monte"
                style={{ animationDelay: "60ms" }}
              >
                Averigua cuánto debería costar tu fórmula
              </h1>
              <p
                className="entra mt-4 max-w-[46ch] text-lg leading-snug text-monte/90"
                style={{ animationDelay: "120ms" }}
              >
                Un agente de WhatsApp que te dice cuál es el precio regulado de los
                medicamentos de tu fórmula, si están desabastecidos, y te arma la tutela si
                te los niegan.
              </p>
              <a
                href={WHATSAPP}
                className="cta trazo sombra entra mt-7 inline-flex items-center gap-3 rounded-full bg-monte px-7 py-4 text-lg font-semibold text-white transition-transform hover:-translate-y-0.5"
                style={{ animationDelay: "180ms" }}
              >
                <IconoWhatsApp className="h-5 w-5" />
                Escríbele por WhatsApp
              </a>
              <div className="entra mt-9" style={{ animationDelay: "240ms" }}>
                <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-monte/70">
                  Con datos públicos de
                </p>
                <p className="mt-1.5 font-display text-lg font-bold text-monte">
                  SISMED <span className="font-normal text-monte/60">(MinSalud)</span> ·
                  INVIMA
                </p>
              </div>
            </div>

            {/* El corte de la curuba: contorno verde, corona crema, centro
                naranja. Es la fruta partida y es la onda del mensaje que sale.
                Los dos círculos van anidados y centrados sobre el teléfono —
                concéntricos por construcción, no por dos posiciones que hay
                que mantener de acuerdo. */}
            <div className="relative flex justify-center lg:justify-end">
              <div className="relative -mb-10 lg:-mb-14">
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
                >
                  <div className="trazo grid h-[34rem] w-[34rem] place-items-center rounded-full bg-crema/60">
                    <div className="trazo h-[21rem] w-[21rem] rounded-full bg-pulpa/70" />
                  </div>
                </div>
                <div
                  className="entra relative z-10"
                  style={{ animationDelay: "300ms" }}
                >
                  <Telefono
                    animada
                    className="h-[clamp(25rem,60svh,36rem)]"
                    chat={[
                      { de: "tu", foto: true },
                      {
                        de: "curuba",
                        texto: "Encontré 3 medicamentos. Estos son los techos regulados:",
                        lineas: [
                          "Acetaminofén 500 mg → $12.400",
                          "Losartán 50 mg → $8.900",
                          "Omeprazol 20 mg → $6.100",
                        ],
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Cifras ─────────────────────────────────────────────────────── */}
        <section className="px-2 py-14 sm:px-6 sm:py-20">
          <div className="grid gap-8 sm:grid-cols-3 sm:gap-6">
            {CIFRAS.map((c) => (
              <div key={c.valor}>
                <p className="font-display text-[clamp(3rem,6vw,4.5rem)] font-extrabold leading-none tracking-tight text-curuba">
                  {c.valor}
                </p>
                <p className="mt-3 max-w-[32ch] leading-snug text-white">{c.texto}</p>
              </div>
            ))}
          </div>
          <p className="mt-10 max-w-[76ch] font-mono text-[11px] uppercase leading-relaxed tracking-[0.14em] text-crema/70">
            Defensoría del Pueblo, 2025 — encuesta en puntos de dispensación (n=3.449). La
            variación de 2025 es 17,8 % contra la serie de 265.173 tutelas, no el 17,92 %
            que titula la prensa sobre una base redondeada.
          </p>
        </section>

        {/* ── Las tres funciones ─────────────────────────────────────────── */}
        <section className="px-2 sm:px-6">
          <h2 className="max-w-[20ch] font-display text-[clamp(2rem,4vw,3.25rem)] font-extrabold leading-[1.02] tracking-[-0.03em] text-white">
            Tres caminos, uno por cada salida que te queda
          </h2>
          <p className="mt-4 max-w-[52ch] text-lg leading-snug text-crema/90">
            El medicamento está formulado, está cubierto y su entrega es un derecho. Cuando
            no llega, Curuba responde en el único canal que ya tienes abierto.
          </p>
          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {FUNCIONES.map((f) => (
              <article
                key={f.titulo}
                className="trazo sombra flex flex-col rounded-3xl bg-crema p-5"
              >
                <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-monte/70">
                  {f.situacion}
                </p>
                <h3 className="mt-2 font-display text-2xl font-bold tracking-tight text-monte">
                  {f.titulo}
                </h3>
                <div className="mt-5 flex-1">
                  <Burbujas chat={f.chat} />
                </div>
                <p className="mt-5 border-t border-monte/20 pt-3 font-mono text-[11px] leading-relaxed text-monte/70">
                  {f.nota}
                </p>
              </article>
            ))}
          </div>
        </section>

        {/* ── De dónde salen los datos ───────────────────────────────────── */}
        <section className="px-2 pt-20 sm:px-6">
          <h2 className="max-w-[18ch] font-display text-[clamp(2rem,4vw,3.25rem)] font-extrabold leading-[1.02] tracking-[-0.03em] text-white">
            De dónde salen los datos
          </h2>
          <p className="mt-4 max-w-[52ch] text-lg leading-snug text-crema/90">
            De dos fuentes públicas, congeladas en un corte que queda escrito. Ningún precio
            sale de un modelo.
          </p>

          <div className="mt-10 grid gap-5 sm:grid-cols-2">
            {FUENTES.map((f) => (
              <article key={f.nombre} className="trazo sombra rounded-3xl bg-curuba p-6">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="font-display text-3xl font-extrabold tracking-tight text-monte">
                    {f.nombre}
                  </h3>
                  <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-monte/70">
                    {f.corte}
                  </p>
                </div>
                <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.14em] text-monte/70">
                  {f.entidad}
                </p>
                <p className="mt-4 text-lg leading-snug text-monte">{f.aporta}</p>
                <p className="mt-4 font-display text-xl font-bold text-monte">{f.filas}</p>
              </article>
            ))}
          </div>

          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            {PRECISIONES.map((p) => (
              <article
                key={p.titulo}
                className="rounded-3xl border-[3px] border-crema/30 p-6"
              >
                <h3 className="font-display text-xl font-bold leading-tight text-curuba">
                  {p.titulo}
                </h3>
                <p className="mt-3 leading-snug text-crema/90">{p.texto}</p>
              </article>
            ))}
          </div>
        </section>

        {/* ── Aviso legal ────────────────────────────────────────────────── */}
        <section className="px-2 pt-20 sm:px-6">
          <div className="trazo sombra rounded-3xl bg-curuba p-6 sm:p-8">
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-monte/70">
              Aviso legal
            </p>
            <p className="mt-3 max-w-[68ch] text-lg leading-snug text-monte">
              Curuba <strong>no da asesoría médica ni jurídica</strong>. Los precios son
              techos regulados del SISMED para el canal institucional, no lo que cobra un
              punto de venta. El estado de desabastecimiento es el del último corte
              publicado por el INVIMA y puede haber cambiado. La tutela que genera es un{" "}
              <strong>borrador que debe revisarse antes de radicarse</strong>.
            </p>
          </div>
        </section>

        <footer className="flex flex-col gap-4 px-2 py-12 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-crema/70">
            Curuba · Platanus Build Night 2026 · Bogotá
          </p>
          <a
            href={REPO}
            className="font-mono text-[11px] uppercase tracking-[0.14em] text-curuba underline underline-offset-4"
          >
            Código y fuentes en GitHub
          </a>
        </footer>
      </div>
    </main>
  );
}
