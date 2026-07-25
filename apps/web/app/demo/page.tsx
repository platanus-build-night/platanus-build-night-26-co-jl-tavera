"use client";

// El panel de tarima. A la izquierda el mapa del agente prendiéndose tool por tool; a la
// derecha el celular con la conversación de verdad, foto de la fórmula y PDF incluidos.
//
// Este es el PRIMER "use client" del proyecto y rompe a propósito el presupuesto técnico
// de DESIGN.md §10 ("la página no manda JavaScript de aplicación"). Ese presupuesto es de
// la landing y sigue en pie: `/` compila estática. Una pantalla que pinta una corrida en
// vivo no puede existir sin estado.
//
// Todo lo que se ve acá llega por un solo EventSource contra GET /demo/eventos de la API.
// El primer evento es el estado completo, así que reconectar es idempotente: cuando llega
// un `estado`, se reemplaza todo y no hay que reconciliar nada.

import { useEffect, useRef, useState } from "react";

import Grafo, { RIO_ABAJO, type Contadores, type EstadoNodo } from "./grafo";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const WHATSAPP =
  process.env.NEXT_PUBLIC_WHATSAPP_URL ?? "https://wa.me/12603057633?text=Hola%20Curuba";

// Los mismos cuatro de legal.NOMBRES, para ponerle nombre a la tarjeta del adjunto.
const NOMBRES: Record<string, string> = {
  peticion: "Derecho de petición",
  tutela: "Acción de tutela",
  desacato: "Incidente de desacato",
  supersalud: "Demanda ante la Supersalud",
};

type Burbuja = {
  de: "tu" | "curuba";
  texto: string;
  foto?: string | null;
  documento?: { url: string; nombre: string } | null;
};

type Paso = { id: string; tool: string; args: string; resultado?: string; reintento?: boolean };

const VACIO: Record<string, EstadoNodo> = {};

export default function Demo() {
  const [burbujas, setBurbujas] = useState<Burbuja[]>([]);
  // Lo que el modelo va escribiendo en este instante. Se reemplaza por la burbuja
  // definitiva cuando llega el evento `agente`, que es el texto que salió a WhatsApp.
  const [parcial, setParcial] = useState("");
  const [estados, setEstados] = useState<Record<string, EstadoNodo>>(VACIO);
  const [args, setArgs] = useState<Record<string, string>>({});
  const [pasos, setPasos] = useState<Paso[]>([]);
  const [contadores, setContadores] = useState<Contadores | null>(null);
  const [respondiendo, setRespondiendo] = useState(false);
  const [conectado, setConectado] = useState(false);
  const [numero, setNumero] = useState("");
  const [activo, setActivo] = useState(true);

  // El tipo del último documento pedido, para nombrar la tarjeta del adjunto: el evento
  // `agente` trae la URL pero no qué escrito es — eso venía en los args de la tool.
  const tipoDoc = useRef<string | null>(null);
  const fin = useRef<HTMLDivElement>(null);
  const traza = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource(`${API}/demo/eventos`);
    es.onopen = () => setConectado(true);
    es.onerror = () => setConectado(false);

    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      switch (ev.tipo) {
        case "estado": {
          setConectado(true);
          setNumero(ev.numero);
          setActivo(ev.activo);
          setBurbujas(ev.burbujas);
          // Las tools de TODA la conversación, no solo del último turno: el camino que ya
          // se recorrió queda pintado para que la pantalla no arranque vacía.
          const previos: Record<string, EstadoNodo> = {};
          for (const t of ev.tools_usadas as string[]) {
            previos[t] = "listo";
            for (const d of RIO_ABAJO[t] ?? []) previos[d] = "listo";
          }
          if (ev.burbujas.length) {
            previos.whatsapp = "listo";
            previos.agente = "listo";
            previos.modelo = "listo";
          }
          setEstados(previos);
          setParcial("");
          setPasos([]);
          setArgs({});
          setContadores(null);
          setRespondiendo(false);
          break;
        }

        case "usuario": {
          setBurbujas((b) => [...b, { de: "tu", texto: ev.texto ?? "", foto: ev.foto }]);
          // Turno nuevo, camino limpio: si no, el grafo acumula y deja de contar qué pasó
          // en ESTE mensaje, que es lo único que el jurado está mirando.
          setEstados({ whatsapp: "listo", agente: "corriendo" });
          setArgs({});
          setPasos([]);
          setParcial("");
          setContadores(null);
          setRespondiendo(false);
          break;
        }

        case "parte": {
          setEstados((s) => ({ ...s, modelo: "corriendo" }));
          if (ev.clase === "texto") setParcial(ev.texto ?? "");
          break;
        }

        case "texto":
          setParcial((p) => p + ev.delta);
          break;

        case "tool_inicio": {
          if (ev.tool === "generar_documento") {
            tipoDoc.current = /"tipo"\s*:\s*"([a-z]+)"/.exec(ev.args)?.[1] ?? null;
          }
          setEstados((s) => {
            const n: Record<string, EstadoNodo> = { ...s, modelo: "listo", [ev.tool]: "corriendo" };
            for (const d of RIO_ABAJO[ev.tool] ?? []) n[d] = "corriendo";
            return n;
          });
          setArgs((a) => ({ ...a, [ev.tool]: ev.args }));
          setPasos((p) => [...p, { id: ev.id, tool: ev.tool, args: ev.args }]);
          break;
        }

        case "tool_fin": {
          setEstados((s) => {
            const n: Record<string, EstadoNodo> = {
              ...s,
              [ev.tool]: ev.reintento ? "reintento" : "listo",
            };
            // Un reintento es el candado de la tool disparándose ANTES de consultar nada,
            // así que lo de río abajo no se tocó: se apaga otra vez.
            for (const d of RIO_ABAJO[ev.tool] ?? []) n[d] = ev.reintento ? "inactivo" : "listo";
            return n;
          });
          setPasos((p) =>
            p.map((x) =>
              x.id === ev.id ? { ...x, resultado: ev.resultado, reintento: ev.reintento } : x,
            ),
          );
          break;
        }

        case "turno_fin":
          setContadores(ev);
          break;

        case "agente": {
          setParcial("");
          setBurbujas((b) => [
            ...b,
            {
              de: "curuba",
              texto: ev.texto,
              documento: ev.adjunto
                ? {
                    url: ev.adjunto,
                    nombre: NOMBRES[tipoDoc.current ?? ""] ?? "Documento",
                  }
                : null,
            },
          ]);
          setEstados((s) => ({ ...s, agente: "listo", modelo: "listo" }));
          setRespondiendo(true);
          break;
        }

        case "reiniciar":
          setBurbujas([]);
          setEstados(VACIO);
          setArgs({});
          setPasos([]);
          setParcial("");
          setContadores(null);
          setRespondiendo(false);
          break;
      }
    };

    return () => es.close();
  }, []);

  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [burbujas, parcial]);

  useEffect(() => {
    if (traza.current) traza.current.scrollTop = traza.current.scrollHeight;
  }, [pasos]);

  return (
    <main className="flex h-svh flex-col gap-3 bg-monte p-3 lg:p-4">
      {/* ── Encabezado ───────────────────────────────────────────────────── */}
      {/* Dos elementos y ya: el título y el estado. Lo memorable de esta pantalla es el
          grafo prendiéndose, así que acá arriba nada compite con él.
          El estado va como pastilla con trazo y sombra porque en este sistema el trazo va
          a los objetos, nunca al texto; y el número va en mono, que es la regla del
          DESIGN.md — la mono marca un dato, no un adorno. */}
      {/* El encabezado usa la MISMA grilla que el cuerpo, así la celda de la derecha cae
          exactamente encima del celular y la pastilla del estado queda de su ancho. */}
      <header className="grid shrink-0 items-center gap-3 lg:grid-cols-[2.2fr_1fr]">
        <h1 className="font-display text-[clamp(1.6rem,2.4vw,2.4rem)] font-semibold leading-none tracking-[-0.035em] text-curuba">
          Curuba <span className="text-crema/75">· la corrida del agente, en vivo</span>
        </h1>
        {/* Contorno crema sin relleno: es un rótulo de estado, no un objeto de la página,
            así que no lleva sombra sólida —no tiene de qué colgar— ni compite con el
            amarillo del grafo. El punto sí es de color, que es lo único que hay que leer
            de un vistazo. */}
        <p className="flex w-full items-center justify-center gap-2 rounded-full border-[3px] border-crema px-4 py-2 font-mono text-[12px] font-medium text-crema">
          <span
            className={`h-2.5 w-2.5 shrink-0 rounded-full ${
              conectado && activo ? "bg-hoja" : "bg-pulpa"
            }`}
          />
          {!activo
            ? "falta CURUBA_DEMO_WA en la API"
            : conectado
              ? `escuchando ${numero}`
              : "reconectando…"}
        </p>
      </header>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[2.2fr_1fr]">
        {/* ── El grafo y la traza ────────────────────────────────────────── */}
        <section className="flex min-h-0 min-w-0 flex-col gap-3">
          <div className="trazo sombra min-h-0 flex-1 overflow-hidden rounded-[28px] bg-monte p-3">
            <Grafo
              estados={estados}
              args={args}
              contadores={contadores}
              respondiendo={respondiendo}
            />
          </div>

          {/* Lo que devolvió cada tool, en crudo. Es el sitio donde se ven los DATOS —
              que es la mitad del argumento: los precios y las coberturas salen de tres
              datasets públicos, no del modelo. */}
          <div
            ref={traza}
            className="trazo sombra sin-barra h-[16vh] shrink-0 overflow-y-auto rounded-[28px] bg-curuba px-5 py-4"
          >
            {pasos.length === 0 ? (
              // En cuerpo y no en mono: es una instrucción, y en este sistema la mono está
              // reservada para lo que es un dato rastreable a una fuente.
              <p className="text-[14px] leading-snug text-monte/70">
                Escríbele al bot y acá aparece lo que devolvió cada tool.
              </p>
            ) : (
              <ol className="space-y-1.5">
                {pasos.map((p) => (
                  <li key={p.id} className="font-mono text-[12px] leading-snug text-monte">
                    <span className="font-medium">
                      {p.reintento ? "↻" : "→"} {p.tool}
                    </span>{" "}
                    <span className="text-monte/70">{p.args}</span>
                    {p.resultado ? (
                      // El reintento se distingue con el glifo ↻ y tinta plena, NO con
                      // color: sobre el amarillo, el naranja de `pulpa` da ~1,4:1 y
                      // desaparece — es el caso que DESIGN.md ya descartó para el blanco
                      // sobre naranja.
                      <span className={p.reintento ? "font-medium text-monte" : "text-monte/80"}>
                        {" ⟶ "}
                        {p.resultado}
                      </span>
                    ) : (
                      <span className="text-monte/50"> ⟶ …</span>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>

        {/* ── El celular ─────────────────────────────────────────────────── */}
        {/* Sin aviso legal acá abajo: el CLAUDE.md lo exige en el pie del PDF, en la
            respuesta de WhatsApp y en la landing, y esta es una pantalla de tarima que no
            es ninguna de las tres. Sigue saliendo donde toca. */}
        <section className="trazo sombra flex min-h-0 flex-col rounded-[2rem] bg-monte p-2.5">
          <div className="trazo flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.5rem] bg-crema">
            <div className="flex shrink-0 items-center gap-2.5 border-b-[3px] border-monte bg-hoja px-4 py-3">
              <IconoWhatsApp className="h-6 w-6 shrink-0 text-monte" />
              <div className="min-w-0">
                <p className="truncate font-semibold leading-none text-monte">Curuba</p>
                <p className="mt-1.5 truncate font-mono text-[11px] leading-none text-monte/80">
                  {numero || "sin número"}
                </p>
              </div>
            </div>

            <div className="sin-barra min-h-0 flex-1 space-y-2.5 overflow-y-auto p-4">
              {burbujas.length === 0 && !parcial ? (
                <div className="flex h-full flex-col items-center justify-center gap-4 px-3 text-center">
                  <p className="text-[15px] leading-snug text-monte/70">
                    Escríbele al bot y este panel se mueve solo.
                  </p>
                  <a
                    href={WHATSAPP}
                    className="trazo sombra-sm rounded-full bg-hoja px-4 py-2 font-mono text-[12px] font-medium text-monte"
                  >
                    abrir WhatsApp
                  </a>
                </div>
              ) : null}

              {burbujas.map((b, i) => (
                <Burbuja key={i} b={b} />
              ))}

              {parcial ? <Burbuja b={{ de: "curuba", texto: parcial }} escribiendo /> : null}

              <div ref={fin} />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Burbuja({ b, escribiendo = false }: { b: Burbuja; escribiendo?: boolean }) {
  return (
    <div className={`flex ${b.de === "tu" ? "justify-end" : "justify-start"}`}>
      {/* 15px y no 13: esto se proyecta en una pantalla y se lee desde el fondo del salón. */}
      <div
        className={`trazo max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[15px] leading-snug text-monte ${
          b.de === "tu" ? "bg-hoja" : "bg-white"
        }`}
      >
        {typeof b.foto === "string" ? (
          // Un <img> pelado y no next/image: el host sale de una variable de entorno en
          // runtime, así que no se puede declarar en remotePatterns, y optimizar una foto
          // que se ve una vez en una demo no compra nada.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={b.foto}
            alt="Foto de la fórmula médica que mandó el paciente"
            className="trazo mb-1.5 max-h-52 w-full rounded-lg object-cover"
          />
        ) : null}

        {b.texto ? <p className="whitespace-pre-line">{b.texto}</p> : null}

        {escribiendo ? (
          <span className="ml-0.5 inline-block h-3.5 w-[2px] animate-pulse bg-monte align-middle" />
        ) : null}

        {b.documento ? (
          <a
            href={b.documento.url}
            target="_blank"
            rel="noreferrer"
            className="trazo mt-2.5 flex items-center gap-2.5 rounded-lg bg-crema px-2.5 py-2"
          >
            <span aria-hidden="true" className="text-lg leading-none">
              📄
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-medium">{b.documento.nombre}</span>
              <span className="block font-mono text-[10px] uppercase tracking-wide text-monte/70">
                pdf · borrador
              </span>
            </span>
          </a>
        ) : null}
      </div>
    </div>
  );
}

function IconoWhatsApp({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor">
      <path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 18.15h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 2.2 0 4.27.86 5.83 2.42a8.2 8.2 0 0 1 2.41 5.83c0 4.54-3.7 8.23-8.24 8.23Zm4.52-6.17c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.24-.64.8-.78.97-.15.16-.29.18-.53.06-.25-.13-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.5.11-.11.25-.29.37-.44.13-.15.17-.25.25-.42.08-.16.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48c-.16 0-.43.06-.65.31-.22.25-.85.84-.85 2.04 0 1.2.87 2.36.99 2.52.12.16 1.71 2.61 4.14 3.66.58.25 1.03.4 1.38.51.58.19 1.11.16 1.53.1.47-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.22-.16-.47-.29Z" />
    </svg>
  );
}
