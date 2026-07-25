"""Acción de tutela.

Art. 86 CP y Decreto 2591 de 1991. Es la plantilla más larga porque es la que más
bloques condicionales tiene: la medida provisional, las pretensiones de municipio y
copagos, y sobre todo **el argumento de subsidiariedad, que cambia según qué se agotó**.
"""

from __future__ import annotations

from curuba.legal.campos import es_si, respondido
from curuba.legal.fechas import fecha_larga
from curuba.legal.plantillas.comun import (
    bloques,
    dispensador,
    encabezado_persona,
    fecha,
    hechos_del_mostrador,
    notificaciones,
    valor,
)


def _subsidiariedad(campos: dict) -> str:
    """El párrafo que decide si la tutela sobrevive al primer filtro del juez.

    Las dos versiones citan T-243/2016 y T-163/2018 porque son las que sacan la entrega
    de medicamentos de la competencia de la Supersalud — sin eso, el juez puede declarar
    improcedente por no haber ido allá primero.
    """
    if es_si(campos, "peticion_radicada"):
        return (
            "Subsidiariedad. Agoté el mecanismo ordinario ante la entidad mediante "
            "derecho de petición, sin obtener respuesta de fondo dentro del término "
            "legal. Además, la Corte Constitucional precisó en las sentencias T-243 de "
            "2016 y T-163 de 2018 que la función jurisdiccional de la Superintendencia "
            "Nacional de Salud NO comprende las controversias sobre suministro, "
            "distribución y entrega de medicamentos, de modo que para este caso la acción "
            "de tutela es el mecanismo idóneo. La sentencia SU-508 de 2020 reiteró que "
            "agotar esa vía no es un requisito ineludible y que el juez no puede declarar "
            "la improcedencia de forma automática."
        )
    return (
        "Subsidiariedad. No existe otro mecanismo judicial idóneo y eficaz para la "
        "protección invocada. La Corte Constitucional precisó en las sentencias T-243 de "
        "2016 y T-163 de 2018 que la función jurisdiccional de la Superintendencia "
        "Nacional de Salud NO comprende las controversias sobre suministro, distribución "
        "y entrega de medicamentos. La sentencia SU-508 de 2020 reiteró que agotar esa "
        "vía no es un requisito ineludible, y la T-343 de 2025 que la Superintendencia "
        "carece de competencia cuando hay omisión o silencio de la EPS."
    )


def _medida_provisional(campos: dict) -> str:
    """Art. 7 del Decreto 2591: la herramienta más rápida de todo el sistema.

    Solo se pide si hay riesgo. El juez puede ordenar la entrega en horas, antes de
    fallar el fondo.
    """
    if not es_si(campos, "riesgo_vital"):
        return ""
    return bloques(
        "## IV. SOLICITUD DE MEDIDA PROVISIONAL",
        "Con fundamento en el artículo 7 del Decreto 2591 de 1991, solicito "
        "respetuosamente al despacho que, desde el auto admisorio y antes de proferir el "
        "fallo, ORDENE como medida provisional la entrega inmediata del medicamento, en "
        "un término no superior a cuarenta y ocho (48) horas.",
        "La medida es necesaria y urgente: la interrupción del tratamiento amenaza de "
        "forma inminente mi vida y mi integridad, y el daño que se produciría no sería "
        "reparable con el fallo posterior.",
    )


def armar(campos: dict) -> str:
    constancia, incumplimiento = hechos_del_mostrador(campos)
    accionado = valor(campos, "eps")
    gestor = str(campos.get("gestor_farmaceutico", "") or "").strip()
    # Vincular al gestor farmacéutico no es adorno: es quien dispensa, y sin él la
    # orden se queda sin destinatario operativo.
    vinculado = f" y a {gestor}, en calidad de gestor farmacéutico" if gestor else ""

    enfermedad = (
        f" El medicamento hace parte del tratamiento de {campos['enfermedad']}."
        if respondido(campos, "enfermedad")
        else ""
    )
    prescrito = (
        f", el {fecha(campos, 'fecha_prescripcion')}"
        if respondido(campos, "fecha_prescripcion")
        else ""
    )

    hecho_peticion = (
        f"CUARTO. El {fecha(campos, 'peticion_fecha')} radiqué ante la entidad accionada "
        f"un derecho de petición con número de radicado "
        f"{valor(campos, 'peticion_radicado')}, sin que a la fecha se me haya resuelto de "
        "fondo ni entregado el medicamento. El término del artículo 14 de la Ley 1755 de "
        "2015 se encuentra vencido."
        if es_si(campos, "peticion_radicada")
        else ""
    )
    hecho_riesgo = (
        "QUINTO. La interrupción del tratamiento compromete de forma grave e inminente "
        "mi vida, mi integridad personal y mi salud."
        if es_si(campos, "riesgo_vital")
        else ""
    )
    hecho_municipio = (
        "SEXTO. Se me exige desplazarme a un municipio distinto al de mi residencia para "
        "reclamar el medicamento, barrera que la Corte Constitucional ha considerado "
        "violatoria del acceso efectivo (T-195 de 2021 y T-377 de 2024)."
        if es_si(campos, "otro_municipio")
        else ""
    )
    hecho_copago = (
        "SÉPTIMO. Se me exige el pago de cuotas moderadoras o copagos que no estoy en "
        "capacidad de asumir, lo que se convierte en una barrera económica de acceso "
        "(T-252 de 2024 y T-264 de 2024)."
        if es_si(campos, "copagos")
        else ""
    )
    hecho_especial = (
        "OCTAVO. Soy sujeto de especial protección constitucional, por lo que me asiste "
        "una protección reforzada en el acceso a los servicios de salud."
        if es_si(campos, "sujeto_especial")
        else ""
    )

    pretension_municipio = (
        "\n\nCUARTO: ORDENAR que la entrega se realice en mi municipio de residencia, o "
        "que la accionada asuma los costos de desplazamiento cuando solo dispense en otra "
        "ciudad, conforme a las sentencias T-195 de 2021 y T-377 de 2024."
        if es_si(campos, "otro_municipio")
        else ""
    )
    pretension_copago = (
        "\n\nQUINTO: ORDENAR la exoneración del cobro de cuotas moderadoras y copagos que "
        "operen como barrera de acceso, conforme a las sentencias T-252 de 2024 y T-264 "
        "de 2024."
        if es_si(campos, "copagos")
        else ""
    )

    return bloques(
        "# ACCIÓN DE TUTELA",
        f"{valor(campos, 'ciudad')}, {fecha_larga()}",
        "Señor\nJUEZ CONSTITUCIONAL (REPARTO)\nE.  S.  D.",
        "Referencia: Acción de tutela.\n"
        f"Accionante: {valor(campos, 'nombre')}.\n"
        f"Accionada: {accionado}.\n"
        "Derechos invocados: salud, vida, integridad personal y petición.",
        f"{encabezado_persona(campos)}, actuando en nombre propio, promuevo ACCIÓN DE "
        "TUTELA con fundamento en el artículo 86 de la Constitución Política y en el "
        f"Decreto 2591 de 1991, contra {accionado}{vinculado}, por la vulneración de mis "
        "derechos fundamentales, con base en los siguientes",
        "## I. HECHOS",
        f"PRIMERO. Me encuentro afiliado(a) a {accionado}.{enfermedad}",
        f"SEGUNDO. Mi médico tratante me prescribió {valor(campos, 'medicamento')}"
        f"{prescrito}.",
        f"TERCERO. El {fecha(campos, 'fecha_reclamacion')} lo reclamé en "
        f"{dispensador(campos)} y no me fue entregado, o me fue entregado de forma "
        "incompleta. A la fecha continúo sin recibirlo.",
        constancia,
        incumplimiento,
        hecho_peticion,
        hecho_riesgo,
        hecho_municipio,
        hecho_copago,
        hecho_especial,
        "## II. DERECHOS FUNDAMENTALES VULNERADOS",
        "Considero vulnerados los derechos fundamentales a la SALUD (artículo 49 de la "
        "Constitución Política y Ley Estatutaria 1751 de 2015), a la VIDA y a la "
        "INTEGRIDAD PERSONAL (artículo 11), a la DIGNIDAD HUMANA (artículo 1) y, en lo "
        "pertinente, al derecho de PETICIÓN (artículo 23).",
        "El artículo 8 de la Ley 1751 de 2015 consagra la integralidad: los servicios y "
        "tecnologías deben suministrarse de manera completa, sin fragmentar la atención. "
        "La sentencia T-092 de 2018 precisó que la EPS debe garantizar la entrega "
        "oportuna y eficiente y remover las barreras injustificadas de acceso.",
        "## III. PRETENSIONES",
        f"PRIMERO: TUTELAR mis derechos fundamentales y ORDENAR a {accionado} que, en un "
        "término no superior a cuarenta y ocho (48) horas, me entregue de forma completa "
        f"{valor(campos, 'medicamento')}.",
        "SEGUNDO: ORDENAR el tratamiento integral, de manera que se garantice la entrega "
        "continua y oportuna de este y de los demás medicamentos, insumos y servicios que "
        "mi médico tratante prescriba con ocasión de la misma patología, sin necesidad de "
        "acudir a una nueva acción judicial.",
        "TERCERO: ORDENAR que se me informe por escrito el trámite adelantado y el "
        f"responsable de su cumplimiento.{pretension_municipio}{pretension_copago}",
        _medida_provisional(campos),
        "## V. FUNDAMENTOS DE DERECHO Y PROCEDIBILIDAD",
        "Legitimación por activa. Actúo en nombre propio, como titular de los derechos "
        "fundamentales cuya protección invoco (artículo 86 de la Constitución Política y "
        "artículo 10 del Decreto 2591 de 1991).",
        f"Legitimación por pasiva. {accionado} es una entidad particular que presta un "
        "servicio público y frente a la cual me encuentro en estado de subordinación, "
        "supuesto expresamente previsto en el artículo 42 del Decreto 2591 de 1991.",
        _subsidiariedad(campos),
        "Inmediatez. Los hechos que motivan esta acción son actuales y la vulneración se "
        "mantiene al día de hoy, por lo que la solicitud se formula en un término "
        "razonable.",
        "## VI. JURAMENTO",
        "Bajo la gravedad del juramento manifiesto que no he presentado otra acción de "
        "tutela por los mismos hechos y derechos ante ninguna otra autoridad judicial "
        "(artículo 37 del Decreto 2591 de 1991).",
        "## VII. PRUEBAS",
        "Solicito tener como pruebas la copia de la fórmula médica o de la orden de "
        "servicio, la copia de mi documento de identidad, la historia clínica en lo "
        "pertinente y los soportes de las reclamaciones adelantadas ante la accionada. "
        "Solicito además OFICIAR a la accionada para que allegue el registro de las "
        "entregas y no entregas asociadas a mi afiliación.",
        notificaciones(campos),
    )
