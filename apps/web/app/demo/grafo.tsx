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
  { id: "whatsapp", x: 24, y: 300, w: 170, h: 96, titulo: "WhatsApp", sub: "Twilio · el paciente escribe" },
  { id: "agente", x: 246, y: 262, w: 210, h: 172, titulo: "curuba", sub: "Pydantic AI Agent\n7 tools · 2 toolsets" },
  { id: "modelo", x: 246, y: 40, w: 210, h: 140, titulo: "Claude Sonnet 5", sub: "OpenRouter" },

  { id: "consultar_cobertura", x: 512, y: 62, w: 286, h: 62, titulo: "consultar_cobertura", sub: "¿lo paga la EPS?", tool: true },
  { id: "buscar_medicamento", x: 512, y: 138, w: 286, h: 62, titulo: "buscar_medicamento", sub: "techo de precio regulado", tool: true },
  { id: "consultar_desabastecimiento", x: 512, y: 214, w: 286, h: 62, titulo: "consultar_desabastecimiento", sub: "estado INVIMA", tool: true },
  { id: "identificar_medicamento", x: 512, y: 290, w: 286, h: 62, titulo: "identificar_medicamento", sub: "marca → principio activo", tool: true },
  { id: "precio_en_drogueria", x: 512, y: 366, w: 286, h: 62, titulo: "precio_en_drogueria", sub: "precio de mostrador", tool: true },

  { id: "guardar_dato_caso", x: 512, y: 484, w: 286, h: 62, titulo: "guardar_dato_caso", sub: "la entrevista legal", tool: true },
  { id: "generar_documento", x: 512, y: 560, w: 286, h: 62, titulo: "generar_documento", sub: "arma el escrito", tool: true },

  { id: "postgres", x: 872, y: 130, w: 304, h: 116, titulo: "Postgres · pg_trgm", sub: "coverage 2.067 · sismed 38.731\nshortages 783" },
  { id: "perplexity", x: 872, y: 286, w: 304, h: 100, titulo: "Perplexity Sonar", sub: "3 sub-agentes · web_cache" },
  { id: "decidir_ruta", x: 872, y: 466, w: 304, h: 98, titulo: "decidir_ruta()", sub: "cuál de los 4 escritos procede\nlo decide Python, no el modelo", destacado: true },
  { id: "pdf", x: 872, y: 594, w: 304, h: 84, titulo: "fpdf2 → documents", sub: "el PDF, servido en /f/{uuid}" },
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

const GRUPOS = [
  { titulo: "medicamentos", x: 496, y: 34, w: 318, h: 410 },
  { titulo: "ruta_legal", x: 496, y: 456, w: 318, h: 180 },
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

const PINTA: Record<EstadoNodo, string> = {
  inactivo: "bg-crema text-monte",
  corriendo: "bg-pulpa text-monte pulso",
  listo: "bg-curuba text-monte",
  reintento: "bg-curuba text-monte",
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

      {GRUPOS.map((g) => (
        <p
          key={g.titulo}
          className="absolute font-mono text-[clamp(8px,0.85cqw,13px)] uppercase tracking-[0.18em] text-curuba/70"
          style={{ left: `${(g.x / W) * 100}%`, top: `${((g.y - 22) / H) * 100}%` }}
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
            className={`trazo sombra-sm absolute flex flex-col justify-center overflow-hidden rounded-2xl px-[1.1cqw] transition-colors duration-200 ${PINTA[estado]} ${
              n.destacado && estado === "inactivo" ? "bg-curuba/85" : ""
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
            {arg ? (
              <p className="mt-[0.3cqw] truncate font-mono text-[clamp(8px,0.8cqw,12px)] text-monte/85">
                {corta(arg, 40)}
              </p>
            ) : n.sub ? (
              <p className="mt-[0.25cqw] whitespace-pre-line text-[clamp(8px,0.88cqw,13px)] leading-tight text-monte/75">
                {n.sub}
              </p>
            ) : null}

            {n.id === "modelo" && contadores ? (
              <p className="mt-[0.3cqw] font-mono text-[clamp(8px,0.82cqw,12px)] leading-tight text-monte/80">
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
