from datetime import datetime, date, time, timedelta


# ============================================================
# 🎯 CONFIGURACIÓN BASE
# ============================================================

DEFAULT_DURATION_MINUTES = {
    "llamada": 10,
    "email": 5,
    "whatsapp": 5,
    "visita": 30,
}

DEFAULT_HORARIO_INICIO = time(9, 0)
DEFAULT_HORARIO_FIN = time(14, 0)


# ============================================================
# 🧠 AGENDA INTELIGENTE — PLANIFICADOR PROFESIONAL
# ============================================================
def generar_agenda_inteligente(
    clientes: list,
    comerciales: list,
    tipo_accion: str,
    fecha_inicio: date,
    fecha_fin: date,
    duracion_minutos: int = None,
    hora_inicio: time = None,
    hora_fin: time = None
):
    """
    Devuelve actuaciones *planificadas* pero NO insertadas aún.

    Cada actuación generada:
        clienteid
        trabajador_creadorid
        tipo_accion
        fecha_accion (datetime)
        fecha_vencimiento (date)
        titulo
        descripcion
    """

    # --------------------------------------------------------
    # CONFIGURACIÓN HORARIA
    # --------------------------------------------------------
    duracion = duracion_minutos or DEFAULT_DURATION_MINUTES.get(tipo_accion, 10)
    inicio_jornada = hora_inicio or DEFAULT_HORARIO_INICIO
    fin_jornada = hora_fin or DEFAULT_HORARIO_FIN

    minutos_jornada = (
        datetime.combine(date.today(), fin_jornada)
        - datetime.combine(date.today(), inicio_jornada)
    ).seconds // 60

    if minutos_jornada <= 0:
        raise ValueError("El rango horario es inválido.")

    slots_por_dia = minutos_jornada // duracion
    if slots_por_dia < 1:
        slots_por_dia = 1

    # --------------------------------------------------------
    # ROUND ROBIN DE COMERCIALES
    # --------------------------------------------------------
    asignacion_rr = []
    for i, cli in enumerate(clientes):
        asignacion_rr.append(comerciales[i % len(comerciales)])

    # --------------------------------------------------------
    # GENERACIÓN DIARIA DE ACTUACIONES
    # --------------------------------------------------------
    dias = (fecha_fin - fecha_inicio).days + 1
    if dias < 1:
        dias = 1

    actuaciones_plan = []
    cliente_idx = 0
    total_clientes = len(clientes)

    fecha_actual = fecha_inicio

    for _ in range(dias):
        hora_ptr = datetime.combine(fecha_actual, inicio_jornada)

        for _ in range(slots_por_dia):
            if cliente_idx >= total_clientes:
                break

            cliente = clientes[cliente_idx]
            trabajadorid = asignacion_rr[cliente_idx]

            actuacion = {
                "clienteid": cliente["clienteid"],
                "trabajador_creadorid": trabajadorid,
                "tipo_accion": tipo_accion,
                "fecha_accion": hora_ptr.isoformat(),
                "fecha_vencimiento": fecha_actual.isoformat(),
                "titulo": f"Campaña: {tipo_accion.capitalize()}",
                "descripcion": "Tarea generada automáticamente",
            }

            actuaciones_plan.append(actuacion)

            hora_ptr += timedelta(minutes=duracion)
            cliente_idx += 1

        fecha_actual += timedelta(days=1)

        if cliente_idx >= total_clientes:
            break

    # --------------------------------------------------------
    # RESULTADO FINAL
    # --------------------------------------------------------
    huecos = dias * slots_por_dia
    faltan = max(0, total_clientes - huecos)

    return {
        "actuaciones": actuaciones_plan,
        "huecos_disponibles": huecos,
        "total_clientes": total_clientes,
        "faltan_huecos": faltan,
    }
