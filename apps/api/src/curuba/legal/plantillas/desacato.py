"""Incidente de desacato.

Arts. 27 y 52 del Decreto 2591 de 1991. Va cuando ya hubo fallo de tutela y la EPS no
cumple: **no** se pone otra tutela por los mismos hechos, eso es temeridad y se cae.
Lo tramita el mismo juez que falló, que conserva competencia hasta que el derecho quede
restablecido.
"""

from __future__ import annotations

from curuba.legal.fechas import fecha_larga
from curuba.legal.plantillas.comun import (
    bloques,
    encabezado_persona,
    fecha,
    notificaciones,
    valor,
)


def armar(campos: dict) -> str:
    return bloques(
        "# INCIDENTE DE DESACATO",
        f"{valor(campos, 'ciudad')}, {fecha_larga()}",
        f"Señor\nJUEZ {valor(campos, 'tutela_juzgado')}\nE.  S.  D.",
        "Referencia: Solicitud de apertura de INCIDENTE DE DESACATO.\n"
        f"Acción de tutela radicado No. {valor(campos, 'tutela_numero')}.\n"
        f"Accionante: {valor(campos, 'nombre')}.\n"
        f"Accionada: {valor(campos, 'eps')}.",
        f"{encabezado_persona(campos)}, actuando en nombre propio dentro de la acción de "
        "tutela de la referencia, solicito respetuosamente al despacho que ABRA INCIDENTE "
        "DE DESACATO contra la entidad accionada, con fundamento en los artículos 27 y 52 "
        "del Decreto 2591 de 1991 y en los siguientes",
        "## I. HECHOS",
        f"PRIMERO. Mediante fallo del {fecha(campos, 'tutela_fecha_fallo')}, este despacho "
        f"tuteló mis derechos fundamentales y ordenó a {valor(campos, 'eps')} garantizar "
        f"la entrega de {valor(campos, 'medicamento')}.",
        "SEGUNDO. La entidad accionada NO ha dado cumplimiento a lo ordenado. "
        f"Concretamente: {valor(campos, 'tutela_incumplimiento')}.",
        "TERCERO. El término fijado en el fallo se encuentra vencido y a la fecha persiste "
        "la vulneración de mis derechos fundamentales, en las mismas condiciones que "
        "motivaron la acción de tutela.",
        "## II. FUNDAMENTOS DE DERECHO",
        "El artículo 27 del Decreto 2591 de 1991 dispone que el juez mantendrá la "
        "competencia hasta que esté completamente restablecido el derecho o eliminadas las "
        "causas de la amenaza, y que podrá adoptar las medidas necesarias para el "
        "cumplimiento del fallo.",
        "El artículo 52 del mismo decreto establece que quien incumpla una orden de tutela "
        "incurre en desacato, sancionable por el mismo juez con arresto hasta de seis (6) "
        "meses y multa hasta de veinte (20) salarios mínimos legales mensuales, sin "
        "perjuicio de las sanciones penales a que haya lugar.",
        "La Corte Constitucional precisó en la sentencia C-367 de 2014 que el trámite "
        "incidental debe resolverse en un término máximo de diez (10) días.",
        "## III. PETICIÓN",
        "PRIMERO: ABRIR INCIDENTE DE DESACATO contra el representante legal de "
        f"{valor(campos, 'eps')} y contra el funcionario responsable del cumplimiento.",
        "SEGUNDO: REQUERIR a la entidad accionada para que cumpla de forma inmediata la "
        "orden impartida, y a su superior jerárquico para que haga cumplir el fallo y abra "
        "el correspondiente procedimiento disciplinario, conforme al artículo 27 del "
        "Decreto 2591 de 1991.",
        "TERCERO: En caso de persistir el incumplimiento, SANCIONAR al responsable en los "
        "términos del artículo 52 del Decreto 2591 de 1991.",
        "## IV. PRUEBAS",
        "Solicito tener como pruebas la copia del fallo de tutela, la copia de mi "
        "documento de identidad y los soportes de las gestiones adelantadas ante la "
        "accionada con posterioridad al fallo.",
        notificaciones(campos),
    )
