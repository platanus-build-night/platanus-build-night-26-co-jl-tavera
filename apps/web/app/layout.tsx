import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, IBM_Plex_Mono, Instrument_Sans } from "next/font/google";
import "./globals.css";

// Tres roles, no tres adornos. La display lleva la personalidad, la de cuerpo
// lee bien en párrafo, y la monoespaciada marca lo que viene de un dataset
// público: el corte, el conteo de filas, la atribución de la fuente.
const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  display: "swap",
});

const instrument = Instrument_Sans({
  variable: "--font-instrument",
  subsets: ["latin"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

// Sin esto el og:image queda relativo y no lo resuelve ningún cliente de
// WhatsApp — que es justo por donde se comparte esta página. Se hornea en el
// build: cambiar la variable exige redesplegar, no basta con reiniciar.
// `RAILWAY_PUBLIC_DOMAIN` solo existe después de generar el dominio, así que
// `NEXT_PUBLIC_SITE_URL` es la ruta determinista y va primero.
const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.RAILWAY_PUBLIC_DOMAIN
    ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}`
    : "http://localhost:3000");

const descripcion =
  "Un agente de WhatsApp que te dice cuál es el precio regulado de los medicamentos " +
  "de tu fórmula, si están desabastecidos, y te arma la tutela si te los niegan.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "Curuba — Averigua cuánto debería costar tu fórmula",
  description: descripcion,
  icons: { icon: "/project-logo.png" },
  openGraph: {
    type: "website",
    locale: "es_CO",
    siteName: "Curuba",
    title: "Curuba — Averigua cuánto debería costar tu fórmula",
    description: descripcion,
    images: [{ url: "/project-logo.png", width: 1000, height: 1000, alt: "Curuba" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#123d22",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es-CO"
      className={`${bricolage.variable} ${instrument.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}
