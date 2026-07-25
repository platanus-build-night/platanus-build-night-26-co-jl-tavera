"""Derecho de petición ante la EPS.

Art. 23 CP y Ley 1755 de 2015 — cuyo art. 32 lo hace procedente también ante
particulares, que es lo que lo habilita contra una EPS. Es el primer escalón: gratis,
sin abogado, y deja el radicado con fecha que sostiene la tutela después.
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


def armar(campos: dict) -> str:
    constancia, incumplimiento = hechos_del_mostrador(campos)

    prescripcion = (
        f" El medicamento me fue prescrito el {fecha(campos, 'fecha_prescripcion')}."
        if respondido(campos, "fecha_prescripcion")
        else ""
    )
    enfermedad = (
        f" El tratamiento corresponde a {campos['enfermedad']}."
        if respondido(campos, "enfermedad")
        else ""
    )

    # El art. 20 de la Ley 1755 obliga a medidas de urgencia inmediatas cuando hay
    # peligro para la vida. Solo se invoca si de verdad aplica: pedirlo siempre le
    # quitaría fuerza justo en los casos donde importa.
    urgencia = (
        "CUARTO. La interrupción del tratamiento pone en riesgo grave mi vida y mi "
        "integridad personal, por lo que esta petición debe recibir el trámite "
        "prioritario del artículo 20 de la Ley 1755 de 2015, que obliga a la entidad a "
        "adoptar medidas de urgencia de forma inmediata."
        if es_si(campos, "riesgo_vital")
        else ""
    )

    municipio = (
        "QUINTO. Se me exige desplazarme a un municipio distinto al de mi residencia "
        "para reclamar el medicamento, lo que constituye una barrera de acceso "
        "injustificada."
        if es_si(campos, "otro_municipio")
        else ""
    )

    copago = (
        "SEXTO. Se me está exigiendo el pago de cuotas moderadoras o copagos que no "
        "estoy en capacidad económica de asumir, lo que en la práctica me impide "
        "acceder al medicamento."
        if es_si(campos, "copagos")
        else ""
    )

    pretension_municipio = (
        "\n\nCUARTO: Que la entrega se realice en mi municipio de residencia, sin "
        "exigirme desplazamientos a otra ciudad, o que la EPS asuma los costos del "
        "desplazamiento."
        if es_si(campos, "otro_municipio")
        else ""
    )
    pretension_copago = (
        "\n\nQUINTO: Que se me exonere del cobro de cuotas moderadoras y copagos, o se "
        "me informe el fundamento legal concreto del cobro."
        if es_si(campos, "copagos")
        else ""
    )

    return bloques(
        "# DERECHO DE PETICIÓN",
        f"{valor(campos, 'ciudad')}, {fecha_larga()}",
        f"Señores\n{valor(campos, 'eps')}\nOficina de Atención al Usuario\nE.  S.  D.",
        "Referencia: Derecho de petición — entrega de medicamentos.\n"
        f"Asunto: solicitud de entrega de {valor(campos, 'medicamento')}.",
        f"{encabezado_persona(campos)}, en ejercicio del derecho fundamental de petición "
        "consagrado en el artículo 23 de la Constitución Política y desarrollado por la "
        "Ley 1755 de 2015 —cuyo artículo 32 lo hace procedente también ante "
        "particulares—, formulo respetuosamente la siguiente petición.",
        "## I. HECHOS",
        f"PRIMERO. Me fue prescrito por mi médico tratante el siguiente medicamento: "
        f"{valor(campos, 'medicamento')}.{prescripcion}{enfermedad}",
        f"SEGUNDO. El {fecha(campos, 'fecha_reclamacion')} me presenté a reclamarlo en "
        f"{dispensador(campos)} y no me fue entregado, o me fue entregado de forma "
        "incompleta.",
        "TERCERO. A la fecha de esta petición no he recibido el medicamento completo, "
        "pese a estar prescrito por mi médico tratante y a ser mi entrega un derecho.",
        constancia,
        incumplimiento,
        urgencia,
        municipio,
        copago,
        "## II. FUNDAMENTOS DE DERECHO",
        "Artículo 23 de la Constitución Política y Ley 1755 de 2015, que regulan el "
        "derecho de petición. El artículo 14 fija el término de quince (15) días hábiles "
        "para resolver de fondo, y el artículo 20 el trámite prioritario cuando está en "
        "juego un derecho fundamental o hay riesgo para la vida o la integridad.",
        "Ley Estatutaria 1751 de 2015, que reconoce la salud como derecho fundamental "
        "autónomo. Su artículo 8 consagra la integralidad: los servicios y tecnologías "
        "deben suministrarse de manera completa, sin fragmentar la atención.",
        "Resolución 1604 de 2013 del Ministerio de Salud, que reglamenta el artículo 131 "
        "del Decreto-Ley 019 de 2012: cuando la EPS o el gestor farmacéutico no pueda "
        "entregar completo al momento de la reclamación, debe garantizar la entrega de lo "
        "pendiente en un plazo máximo de cuarenta y ocho (48) horas, en el lugar de "
        "residencia o trabajo del afiliado, si este lo autoriza.",
        "## III. PETICIÓN",
        f"PRIMERO: Que se me entregue de forma inmediata y completa "
        f"{valor(campos, 'medicamento')}.",
        # La autorización de domicilio TIENE que ser expresa: sin ella la EPS puede
        # alegar que el mecanismo de las 48 horas nunca se activó.
        "SEGUNDO: Que en caso de no existir disponibilidad al momento de la reclamación, "
        "se active el mecanismo de la Resolución 1604 de 2013 y se me entregue lo "
        "pendiente dentro de las cuarenta y ocho (48) horas siguientes. Para tal efecto "
        f"AUTORIZO EXPRESAMENTE la entrega a domicilio en la dirección "
        f"{valor(campos, 'direccion')} de {valor(campos, 'ciudad')}.",
        "TERCERO: Que se me informe por escrito la causal concreta de la no entrega y el "
        "registro correspondiente en el sistema de información, así como el nombre del "
        f"responsable del trámite.{pretension_municipio}{pretension_copago}",
        "## IV. TÉRMINO",
        "Solicito que la respuesta se produzca dentro de los quince (15) días hábiles del "
        "artículo 14 de la Ley 1755 de 2015. Advierto que la falta de respuesta oportuna "
        "vulnera el derecho fundamental de petición y habilita la acción de tutela.",
        "## V. ANEXOS",
        "Copia de la fórmula médica o de la orden de servicio. Copia del documento de "
        "identidad. Los demás documentos que soporten los hechos.",
        notificaciones(campos),
    )
