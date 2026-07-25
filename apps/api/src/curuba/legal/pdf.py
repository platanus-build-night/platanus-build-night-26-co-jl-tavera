"""Del texto marcado al PDF.

Solo sabe de tipografía: no conoce campos, ni rutas, ni jurisprudencia. Recibe el texto
que arma una plantilla y lo maqueta.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

from curuba.legal.documentos import AVISO

FUENTE = Path(__file__).with_name("DejaVuSans.ttf")
FUENTE_BOLD = Path(__file__).with_name("DejaVuSans-Bold.ttf")

MARCADOR = re.compile(r"\[COMPLETAR: [^\]]+\]")


def marcadores(texto: str) -> list[str]:
    """Los [COMPLETAR: …] que quedaron, sin repetir y en orden de aparición.

    El agente se los lee en voz alta por WhatsApp: enterrados en el PDF no sirven de
    nada, porque quien va a radicar no siempre lo abre antes de llegar a la ventanilla.
    """
    vistos: list[str] = []
    for encontrado in MARCADOR.findall(texto):
        if encontrado not in vistos:
            vistos.append(encontrado)
    return vistos


class _Documento(FPDF):
    """FPDF con el aviso legal al pie de cada página."""

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(110, 110, 110)
        self.multi_cell(0, 3.2, AVISO, align="C")
        self.set_text_color(0, 0, 0)


def render_pdf(texto: str) -> bytes:
    """Convierte el texto marcado a PDF.

    El marcado es mínimo a propósito: `# ` es el título, `## ` un encabezado de sección,
    y lo demás es cuerpo.

    Trampa: **`add_font(..., uni=True)` ya no existe.** En fpdf2 2.8 el parámetro
    desapareció y pasarlo revienta con TypeError. Basta con registrar el .ttf — el
    soporte Unicode viene de la fuente, no de la bandera. Sin registrarla, las tildes y
    la ñ salen dañadas.
    """
    pdf = _Documento(format="letter")
    pdf.add_font("DejaVu", "", str(FUENTE))
    pdf.add_font("DejaVu", "B", str(FUENTE_BOLD))
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.set_margins(25, 20, 25)
    pdf.add_page()

    for bloque in texto.split("\n\n"):
        bloque = bloque.strip()
        if not bloque:
            continue
        if bloque.startswith("# "):
            pdf.set_font("DejaVu", "B", 13)
            pdf.multi_cell(0, 7, bloque[2:], align="C")
            pdf.ln(4)
        elif bloque.startswith("## "):
            pdf.ln(2)
            pdf.set_font("DejaVu", "B", 10.5)
            pdf.multi_cell(0, 5.5, bloque[3:], align="L")
            pdf.ln(1)
        else:
            pdf.set_font("DejaVu", "", 10)
            # Los bloques con saltos simples (encabezado, notificaciones, firma) van
            # alineados a la izquierda: justificarlos estira las líneas sueltas.
            alineacion = "L" if "\n" in bloque else "J"
            pdf.multi_cell(0, 5, bloque, align=alineacion)
            pdf.ln(2.5)

    return bytes(pdf.output())
