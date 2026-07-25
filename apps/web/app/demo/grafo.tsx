// El mapa del agente. Los nodos son los de verdad: los dos toolsets, las siete tools,
// las tres tablas, Sonar, la tabla de ruteo en Python y el PDF. Están todos desde el
// primer momento —antes de que llegue un mensaje— porque la mitad del argumento es lo
// que el agente PODRÍA hacer; la corrida solo prende el camino que tomó.
//
// Las cajas son HTML posicionado en porcentajes y las aristas un SVG del mismo tamaño
// debajo: en SVG el texto no se corta ni se envuelve, y acá hay que meter el nombre de la
// tool, lo que hace y los argumentos con los que la llamó el modelo. Los dos sistemas
// comparten la tabla de coordenadas de abajo, así que quedan alineados.
//
// Las letras van en `cqw` (ancho del contenedor) y no en px: el grafo se proyecta en una
// pantalla que no sabemos qué tamaño tiene, y así escala completo sin medir nada con JS.

export type EstadoNodo = "inactivo" | "corriendo" | "listo" | "reintento";

// El lienzo. Todo lo de abajo está en estas unidades.
const W = 1200;
const H = 700;

type Nodo = {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  titulo: string;
  sub?: string;
  /** Lo pinta como tool: caja más chica, y muestra los args con los que la llamaron. */
  tool?: boolean;
  /** El nodo del argumento del producto. Se pinta aparte. */
  destacado?: boolean;
};

export const NODOS: Nodo[] = [
  // "entra y sale" y no "el paciente escribe": este nodo tiene dos aristas —el mensaje que
  // llega y la respuesta que vuelve— y el rótulo tiene que decir eso. De paso cabe en una
  // línea, que con la caja angosta era el otro problema.
  { id: "whatsapp", x: 24, y: 300, w: 170, h: 96, titulo: "WhatsApp", sub: "Twilio · entra y sale" },
  { id: "agente", x: 246, y: 262, w: 210, h: 172, titulo: "curuba", sub: "Pydantic AI Agent\n7 tools · 2 toolsets" },
  { id: "modelo", x: 246, y: 40, w: 210, h: 140, titulo: "Claude Sonnet 5", sub: "OpenRouter" },

  { id: "consultar_cobertura", x: 512, y: 62, w: 286, h: 62, titulo: "consultar_cobertura", sub: "¿lo paga la EPS?", tool: true },
  { id: "buscar_medicamento", x: 512, y: 138, w: 286, h: 62, titulo: "buscar_medicamento", sub: "techo de precio regulado", tool: true },
  { id: "consultar_desabastecimiento", x: 512, y: 214, w: 286, h: 62, titulo: "consultar_desabastecimiento", sub: "estado INVIMA", tool: true },
  { id: "identificar_medicamento", x: 512, y: 290, w: 286, h: 62, titulo: "identificar_medicamento", sub: "marca → principio activo", tool: true },
  { id: "precio_en_drogueria", x: 512, y: 366, w: 286, h: 62, titulo: "precio_en_drogueria", sub: "precio de mostrador", tool: true },

  { id: "guardar_dato_caso", x: 512, y: 496, w: 286, h: 62, titulo: "guardar_dato_caso", sub: "la entrevista legal", tool: true },
  { id: "generar_documento", x: 512, y: 572, w: 286, h: 62, titulo: "generar_documento", sub: "arma el escrito", tool: true },

  { id: "postgres", x: 872, y: 130, w: 304, h: 116, titulo: "Postgres · pg_trgm", sub: "coverage 2.067 · sismed 38.731\nshortages 783" },
  { id: "perplexity", x: 872, y: 286, w: 304, h: 100, titulo: "Perplexity Sonar", sub: "3 sub-agentes · web_cache" },
  { id: "decidir_ruta", x: 872, y: 460, w: 304, h: 98, titulo: "decidir_ruta()", sub: "cuál de los 4 escritos procede\nlo decide Python, no el modelo", destacado: true },
  { id: "pdf", x: 872, y: 590, w: 304, h: 84, titulo: "fpdf2 → documents", sub: "el PDF, servido en /f/{uuid}" },
];

// Qué prende cada tool río abajo. No es decorativo: es lo que hace el código —
// `_con_invima` le pega el estado del INVIMA a cobertura y a precio, y por eso esas dos
// también tocan `shortages`.
export const RIO_ABAJO: Record<string, string[]> = {
  consultar_cobertura: ["postgres"],
  buscar_medicamento: ["postgres"],
  consultar_desabastecimiento: ["postgres"],
  identificar_medicamento: ["perplexity", "postgres"],
  precio_en_drogueria: ["perplexity"],
  guardar_dato_caso: ["decidir_ruta"],
  generar_documento: ["pdf"],
};

export const TOOLS = Object.keys(RIO_ABAJO);

// Los dos toolsets, como cajas punteadas alrededor de sus tools. La separación entre las
// dos no es estética: el rótulo se dibuja ENCIMA del borde de arriba —como el legend de un
// fieldset— y con las cajas pegadas el de `ruta_legal` caía sobre el borde de
// `medicamentos` y se perdía.
const GRUPOS = [
  { titulo: "medicamentos", x: 496, y: 36, w: 318, h: 404 },
  { titulo: "ruta_legal", x: 496, y: 470, w: 318, h: 176 },
];

type Arista = { de: string; a: string };

const ARISTAS: Arista[] = [
  { de: "whatsapp", a: "agente" },
  { de: "agente", a: "modelo" },
  ...TOOLS.map((t) => ({ de: "agente", a: t })),
  ...Object.entries(RIO_ABAJO).flatMap(([tool, destinos]) =>
    destinos.map((d) => ({ de: tool, a: d })),
  ),
];

const POR_ID = new Map(NODOS.map((n) => [n.id, n]));

/** El punto por donde sale o entra una arista: el borde derecho o izquierdo, a media altura. */
function ancla(id: string, lado: "sale" | "entra"): [number, number] {
  const n = POR_ID.get(id)!;
  // El agente y el modelo están uno encima del otro, así que ese par se conecta por arriba.
  if (id === "modelo") return [n.x + n.w / 2, n.y + n.h];
  return [lado === "sale" ? n.x + n.w : n.x, n.y + n.h / 2];
}

function curva(de: string, a: string): string {
  if (a === "modelo") {
    const [x1, y1] = [POR_ID.get("agente")!.x + POR_ID.get("agente")!.w / 2, POR_ID.get("agente")!.y];
    const [x2, y2] = ancla("modelo", "entra");
    return `M ${x1} ${y1} L ${x2} ${y2}`;
  }
  const [x1, y1] = ancla(de, "sale");
  const [x2, y2] = ancla(a, "entra");
  const mitad = (x2 - x1) / 2;
  return `M ${x1} ${y1} C ${x1 + mitad} ${y1}, ${x2 - mitad} ${y2}, ${x2} ${y2}`;
}

// La respuesta volviendo al paciente: sale del agente por abajo y devuelve a WhatsApp.
const VUELTA = `M ${246 + 105} ${262 + 172} C ${300} ${520}, ${60} ${500}, ${24 + 85} ${300 + 96}`;

// El nodo apagado es un wireframe sobre el verde —tinta crema, relleno casi transparente—
// y el encendido es un bloque sólido con tinta oscura. La primera versión pintaba los dos
// rellenos (crema apagado, curuba encendido) y proyectados se parecían demasiado: el camino
// encendido casi no se distinguía. Invertir el esquema es gratis en esta paleta porque pasa
// AA en las dos direcciones, y es lo que hace que prenderse SE VEA.
const PINTA: Record<EstadoNodo, string> = {
  inactivo: "border-crema/30 bg-crema/[0.07] text-crema",
  corriendo: "border-monte bg-pulpa text-monte pulso",
  listo: "border-monte bg-curuba text-monte",
  reintento: "border-monte bg-curuba text-monte",
};

function corta(texto: string, tope: number): string {
  return texto.length <= tope ? texto : texto.slice(0, tope - 1) + "…";
}

export type Contadores = {
  ms: number;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
};

export default function Grafo({
  estados,
  args,
  contadores,
  respondiendo,
}: {
  estados: Record<string, EstadoNodo>;
  args: Record<string, string>;
  contadores: Contadores | null;
  /** La respuesta ya salió: prende la arista de vuelta a WhatsApp. */
  respondiendo: boolean;
}) {
  const de = (id: string): EstadoNodo => estados[id] ?? "inactivo";
  const encendida = (a: string) => de(a) !== "inactivo";

  return (
    <div className="@container relative h-full w-full">
      {/* `preserveAspectRatio="none"` a propósito: así el SVG se estira EXACTAMENTE como
          los porcentajes de las cajas HTML y las aristas quedan pegadas a los nodos en
          cualquier proporción de la caja. Lo que costaría eso —un trazo deformado— se paga
          con `vectorEffect="non-scaling-stroke"`, que fija el grosor en píxeles de
          pantalla. Sin esto, el grafo se recortaba arriba y abajo por unos pocos píxeles
          en cuanto la ventana no daba la proporción exacta. */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="absolute inset-0 h-full w-full"
        aria-hidden="true"
      >
        {GRUPOS.map((g) => (
          <g key={g.titulo}>
            <rect
              x={g.x}
              y={g.y}
              width={g.w}
              height={g.h}
              rx={22}
              fill="none"
              stroke="var(--color-curuba)"
              strokeWidth={2}
              strokeDasharray="8 8"
              opacity={0.5}
              vectorEffect="non-scaling-stroke"
            />
          </g>
        ))}

        {ARISTAS.map((ar) => {
          const viva = encendida(ar.a);
          return (
            <path
              key={`${ar.de}→${ar.a}`}
              d={curva(ar.de, ar.a)}
              fill="none"
              stroke={viva ? "var(--color-curuba)" : "var(--color-crema)"}
              strokeWidth={viva ? 4 : 2}
              strokeLinecap="round"
              opacity={viva ? 1 : 0.22}
              vectorEffect="non-scaling-stroke"
              className={de(ar.a) === "corriendo" ? "fluir" : undefined}
            />
          );
        })}

        <path
          d={VUELTA}
          fill="none"
          stroke={respondiendo ? "var(--color-hoja)" : "var(--color-crema)"}
          strokeWidth={respondiendo ? 4 : 2}
          strokeLinecap="round"
          strokeDasharray="10 6"
          opacity={respondiendo ? 1 : 0.18}
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {/* El rótulo del toolset va montado SOBRE el borde de arriba de su caja, con fondo
          monte que corta la línea punteada: es el truco del legend de un fieldset. Puesto
          arriba del borde —como estaba— el de `ruta_legal` aterrizaba encima de la caja de
          `medicamentos` y no se leía. Así no puede chocar con nada: siempre cae en el
          canal que separa los dos grupos. */}
      {GRUPOS.map((g) => (
        <p
          key={g.titulo}
          className="absolute -translate-y-1/2 whitespace-nowrap bg-monte px-[0.7cqw] font-mono text-[clamp(8px,0.85cqw,13px)] font-medium tracking-[0.06em] text-curuba"
          style={{ left: `${((g.x + 24) / W) * 100}%`, top: `${(g.y / H) * 100}%` }}
        >
          {g.titulo} · FunctionToolset
        </p>
      ))}

      {NODOS.map((n) => {
        const estado = de(n.id);
        const arg = args[n.id];
        return (
          <div
            key={n.id}
            // `border-[3px]` y no la utilidad `trazo`: el color del borde cambia con el
            // estado —monte cuando el nodo está sólido, crema cuando es wireframe sobre el
            // verde—, y `trazo` lo fija en monte, que sobre el fondo desaparece.
            // La sombra sólida también: colgada de un nodo apagado no tiene de qué colgar.
            className={`absolute flex flex-col justify-center overflow-hidden rounded-2xl border-[3px] px-[1.1cqw] transition-colors duration-200 ${
              estado === "inactivo" ? "" : "sombra-sm"
            } ${PINTA[estado]} ${
              // El nodo del argumento del producto no se apaga del todo: es el que hay que
              // ver aunque la corrida no haya pasado por la ruta legal.
              n.destacado && estado === "inactivo" ? "border-curuba/60 bg-curuba/15" : ""
            }`}
            style={{
              left: `${(n.x / W) * 100}%`,
              top: `${(n.y / H) * 100}%`,
              width: `${(n.w / W) * 100}%`,
              height: `${(n.h / H) * 100}%`,
            }}
          >
            <p
              className={`${n.tool ? "font-mono" : "font-display"} font-semibold leading-tight ${
                n.tool ? "text-[clamp(10px,1.05cqw,16px)]" : "text-[clamp(13px,1.5cqw,23px)]"
              }`}
            >
              {n.titulo}
              {estado === "reintento" ? (
                <span className="ml-[0.5cqw] font-mono text-[clamp(7px,0.75cqw,11px)] uppercase tracking-wide">
                  ↻ reintento
                </span>
              ) : null}
            </p>

            {/* Los args reemplazan al subtítulo en vez de sumarse: en una caja de tool no
                caben los dos, y mientras la corrida pasa por ahí lo que importa es con qué
                la llamó el modelo, no lo que la tool hace en general. */}
            {/* Estos tres van con `opacity` y no con un color fijo: la tinta del nodo cambia
                con el estado (monte cuando está sólido, crema cuando es wireframe), así que
                un `text-monte/75` quemado desaparecía en los apagados. */}
            {arg ? (
              <p className="mt-[0.3cqw] truncate font-mono text-[clamp(8px,0.8cqw,12px)] opacity-85">
                {corta(arg, 40)}
              </p>
            ) : n.sub ? (
              <p className="mt-[0.25cqw] whitespace-pre-line text-[clamp(8px,0.88cqw,13px)] leading-tight opacity-70">
                {n.sub}
              </p>
            ) : null}

            {n.id === "modelo" && contadores ? (
              <p className="mt-[0.3cqw] font-mono text-[clamp(8px,0.82cqw,12px)] leading-tight opacity-80">
                {contadores.input_tokens.toLocaleString("es-CO")} tok in ·{" "}
                {contadores.output_tokens.toLocaleString("es-CO")} out
                <br />
                {contadores.requests} llamada{contadores.requests === 1 ? "" : "s"} ·{" "}
                {(contadores.ms / 1000).toLocaleString("es-CO", {
                  minimumFractionDigits: 1,
                  maximumFractionDigits: 1,
                })}{" "}
                s
              </p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
