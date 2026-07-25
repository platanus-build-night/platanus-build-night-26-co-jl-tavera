"""Demanda ante la función jurisdiccional de la Superintendencia Nacional de Salud.

Art. 41 de la Ley 1122 de 2007, modificado por el art. 126 de la Ley 1438 de 2011 y el
art. 6 de la Ley 1949 de 2019. La Supersalud falla en derecho y con carácter definitivo.

**Solo para cobertura y reembolsos.** Para *entrega* de medicamentos no tiene competencia
—T-243 de 2016 y T-163 de 2018—, y por eso `decidir_ruta` nunca manda un caso de entrega
para acá. Si esta plantilla se está usando para un caso de entrega, el bug está en el
ruteo, no aquí.
"""

from __future__ import annotations

from curuba.legal.campos import es_si, respondido
from curuba.legal.documentos import NOMBRES
from curuba.legal.fechas import fecha_larga
from curuba.legal.plantillas.comun import (
    bloques,
    encabezado_persona,
    fecha,
    notificaciones,
    valor,
)
from curuba.legal.texto import normalizar


def armar(campos: dict) -> str:
    if normalizar(campos.get("tipo_problema", "")) == "reembolso":
        objeto = (
            "el reconocimiento y pago de los gastos médicos en que incurrí con recursos "
            "propios, ante la negativa de la entidad a garantizar el servicio."
        )
    else:
        objeto = (
            "la cobertura del servicio o tecnología en salud que la entidad me negó, pese "
            "a estar prescrito por mi médico tratante."
        )

    monto = (
        "CUARTO. Como consecuencia de la negativa debí adquirir el medicamento con "
        f"recursos propios, por un valor de {campos.get('monto_reembolso')}."
        if respondido(campos, "monto_reembolso")
        else ""
    )
    pretension_monto = (
        f"\n\nTERCERO: ORDENAR el reconocimiento y pago de {campos.get('monto_reembolso')}, "
        "correspondiente a lo que debí sufragar con recursos propios."
        if respondido(campos, "monto_reembolso")
        else ""
    )
    especial = (
        "QUINTO. Soy sujeto de especial protección constitucional, condición que refuerza "
        "la obligación de garantizar el acceso efectivo al servicio."
        if es_si(campos, "sujeto_especial")
        else ""
    )
    enfermedad = (
        f" para el manejo de {campos['enfermedad']}"
        if respondido(campos, "enfermedad")
        else ""
    )

    return bloques(
        "# DEMANDA ANTE LA FUNCIÓN JURISDICCIONAL",
        f"{valor(campos, 'ciudad')}, {fecha_larga()}",
        "Señores\nSUPERINTENDENCIA NACIONAL DE SALUD\n"
        "Delegada para la Función Jurisdiccional y de Conciliación\nE.  S.  D.",
        "Referencia: Demanda en ejercicio de la función jurisdiccional.\n"
        f"Demandante: {valor(campos, 'nombre')}.\n"
        f"Demandada: {valor(campos, 'eps')}.\n"
        f"Asunto: {NOMBRES['supersalud']}.",
        f"{encabezado_persona(campos)}, actuando en nombre propio, presento DEMANDA contra "
        f"{valor(campos, 'eps')} para que, en ejercicio de la función jurisdiccional "
        "prevista en el artículo 41 de la Ley 1122 de 2007 —modificado por el artículo 126 "
        "de la Ley 1438 de 2011 y por el artículo 6 de la Ley 1949 de 2019—, esa "
        f"Superintendencia conozca y falle sobre {objeto}",
        "## I. HECHOS",
        f"PRIMERO. Me encuentro afiliado(a) a {valor(campos, 'eps')}.",
        f"SEGUNDO. Mi médico tratante me prescribió {valor(campos, 'medicamento')}"
        f"{enfermedad}.",
        f"TERCERO. El {fecha(campos, 'negativa_fecha')} la entidad me negó la cobertura. "
        f"La negativa me fue comunicada de la siguiente manera: "
        f"{valor(campos, 'negativa_medio')}.",
        monto,
        especial,
        "## II. PRETENSIONES",
        f"PRIMERO: DECLARAR que {valor(campos, 'eps')} está obligada a garantizar la "
        f"cobertura de {valor(campos, 'medicamento')}.",
        "SEGUNDO: ORDENAR a la demandada que autorice y garantice la prestación de forma "
        "inmediata y completa, incluyendo lo necesario para la continuidad del "
        f"tratamiento.{pretension_monto}",
        "## III. FUNDAMENTOS DE DERECHO Y COMPETENCIA",
        "El artículo 41 de la Ley 1122 de 2007, modificado por el artículo 126 de la Ley "
        "1438 de 2011 y por el artículo 6 de la Ley 1949 de 2019, atribuye a la "
        "Superintendencia Nacional de Salud función jurisdiccional para conocer y fallar "
        "en derecho, con carácter definitivo, sobre la cobertura de servicios y "
        "tecnologías y sobre el reconocimiento económico de gastos médicos. El "
        "procedimiento es preferente y sumario.",
        "La Ley Estatutaria 1751 de 2015 reconoce la salud como derecho fundamental "
        "autónomo y consagra en su artículo 8 el principio de integralidad.",
        "Esta competencia es concurrente y a prevención con la jurisdicción ordinaria "
        "laboral, y no excluye la procedencia de la acción de tutela cuando exista un "
        "perjuicio irremediable.",
        "## IV. PRUEBAS",
        "Solicito tener como pruebas la copia de la fórmula médica o de la orden de "
        "servicio, la copia de mi documento de identidad, los soportes de la negativa y, "
        "si es del caso, las facturas de lo pagado con recursos propios.",
        notificaciones(campos),
    )
