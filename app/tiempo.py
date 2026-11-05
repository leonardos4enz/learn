"""Predicción de cuándo termina Leo cada curso (y todos), con su ritmo real y con su tiempo hábil.

Por qué así (ver FILOSOFIA.md):
- La fecha principal sale del RITMO REAL (misiones hechas por día en las últimas 4 semanas), no del plan: la gente
  subestima sistemáticamente cuánto tarda aunque sepa que antes se tardó (falacia de la planificación, Buehler,
  Griffin y Ross 1994). Usar el propio historial como referencia es el "reference class forecasting"
  (Kahneman y Lovallo 1993; Flyvbjerg 2006).
- La fecha "según tu tiempo hábil" se muestra para COMPARAR el plan contra lo real.
- El rango optimista/pesimista es una banda del 80 % suponiendo que las misiones llegan al azar a un ritmo fijo
  (Poisson): el error relativo del ritmo es ~1/√n, así que con pocas misiones medidas el rango es ancho y se angosta
  solo. Es un modelo simple, decisión nuestra, no un estudio.
"""
import math
from datetime import datetime, timedelta

from . import store

VENTANA_DIAS = 28        # ritmo de las últimas 4 semanas
MIN_DIAS_RITMO = 7       # con menos de una semana de historia, se divide entre 7 para no inflar el ritmo
Z80 = 1.2816             # banda del 80 %
MIN_POR_MISION_SUPUESTO = 75   # hasta medir una misión completa; hipótesis, se marca como "supuesto"
MIN_MISION_MEDIDA = 10   # una misión cuenta como medida si tiene al menos 10 min registrados
HORIZONTE = 3 * 365


def _f(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _cursos_con_plan():
    """Cursos con misiones en la app, el 'actual' primero y luego en el orden del árbol. Los que no tienen plan
    (o ya están terminados) quedan fuera hasta que se ingesten."""
    out = []
    for ruta, n in store.iter_cursos():
        d = store.leer_datos(n["id"]) or {}
        ms = d.get("misiones") or []
        if not ms or n.get("estado") == "terminado":
            continue
        out.append((n, d))
    out.sort(key=lambda x: 0 if x[0].get("estado") == "actual" else 1)
    return out


def _ritmo(fechas, hoy):
    """Misiones por día en la ventana, con su banda del 80 %."""
    if not fechas:
        return None
    inicio = max(min(fechas), hoy - timedelta(days=VENTANA_DIAS - 1))
    n = sum(1 for f in fechas if f >= inicio)
    dias = max(MIN_DIAS_RITMO, (hoy - inicio).days + 1)
    if n == 0:
        return {"por_dia": 0, "opt": 0, "pes": 0, "n": 0, "dias": dias}
    k = Z80 / math.sqrt(n)
    r = n / dias
    return {"por_dia": r, "opt": r * (1 + k), "pes": r / (1 + k), "n": n, "dias": dias}


def _fin_con_ritmo(restantes, por_dia, hoy):
    if restantes <= 0:
        return hoy
    if not por_dia:
        return None
    dias = math.ceil(restantes / por_dia)
    return hoy + timedelta(days=dias) if dias <= HORIZONTE else None


def _fin_con_habil(minutos_necesarios, hoy, habil, ya_hoy, reserva_dia):
    """Recorre los días desde hoy gastando el tiempo hábil de cada uno (menos lo que se va en tarjetas y hojas)."""
    if minutos_necesarios <= 0:
        return hoy
    d, falta = hoy, minutos_necesarios
    for i in range(HORIZONTE):
        disp = store.minutos_habiles(d, habil) - reserva_dia
        if i == 0:
            disp -= ya_hoy
        falta -= max(0, disp)
        if falta <= 0:
            return d
        d += timedelta(days=1)
    return None


def _serie_real(ms):
    """Misiones hechas acumuladas por fecha. Las hechas sin fecha (antes del tutor) son el punto de partida."""
    hechas = [m for m in ms if m.get("estado") == "hecha"]
    fechas = sorted(f for f in (_f(m.get("fecha")) for m in hechas) if f)
    base = len(hechas) - len(fechas)
    serie, acc = [], base
    if fechas:
        serie.append({"fecha": (fechas[0] - timedelta(days=1)).isoformat(), "hechas": base})
    for f in sorted(set(fechas)):
        acc += fechas.count(f)
        serie.append({"fecha": f.isoformat(), "hechas": acc})
    return serie, fechas


def _minutos_por_mision(cid, ms):
    hechas = {str(m["id"]) for m in ms if m.get("estado") == "hecha"}
    por = {}
    for r in store._q("SELECT mision, minutos FROM tiempo WHERE curso=? AND mision IS NOT NULL AND minutos IS NOT NULL", (cid,)):
        if r["mision"] in hechas:
            por[r["mision"]] = por.get(r["mision"], 0) + r["minutos"]
    medidas = [v for v in por.values() if v >= MIN_MISION_MEDIDA]
    if medidas:
        return {"minutos": round(sum(medidas) / len(medidas)), "medidas": len(medidas), "supuesto": False}
    return {"minutos": MIN_POR_MISION_SUPUESTO, "medidas": 0, "supuesto": True}


def _uso_semanal(hoy, habil, curso=None):
    """Minutos reales por semana (promedio de las últimas 4, o desde el primer registro) contra los hábiles."""
    desde = hoy - timedelta(days=VENTANA_DIAS - 1)
    filas = store.listar_tiempo(desde, hoy, curso)
    reales = sum(r.get("minutos") or 0 for r in filas)
    if filas:
        desde = max(desde, _f(filas[0]["fecha"]))
    dias = max(MIN_DIAS_RITMO, (hoy - desde).days + 1)
    habiles = sum(store.minutos_habiles(hoy + timedelta(days=i), habil) for i in range(7))
    sin_mision = sum(r.get("minutos") or 0 for r in filas if not r.get("mision"))  # tarjetas, hojas sueltas
    return {"reales_semana": round(reales * 7 / dias), "habiles_semana": habiles, "dias_medidos": dias,
            "reserva_dia": round(sin_mision / dias, 1)}


def _iso(d):
    return d.isoformat() if d else None


def prediccion():
    hoy = store.hoy_local()
    habil = store.tiempo_habil()
    hoy_min = sum(store.minutos_por_dia(hoy, hoy).get(hoy.isoformat(), {}).values())
    uso_total = _uso_semanal(hoy, habil)
    cursos, todas_fechas, total_n, total_h, total_min = [], [], 0, 0, 0
    sin_plan = []
    for ruta, n in store.iter_cursos():
        d = store.leer_datos(n["id"]) or {}
        if not d.get("misiones") and n.get("estado") != "terminado":
            sin_plan.append({"id": n["id"], "nombre": n["nombre"]})
    for n, d in _cursos_con_plan():
        ms = d["misiones"]
        N = len(ms)
        H = sum(1 for m in ms if m.get("estado") == "hecha")
        R = N - H
        serie, fechas = _serie_real(ms)
        rit = _ritmo(fechas, hoy)
        mpm = _minutos_por_mision(n["id"], ms)
        fin = {k: _iso(_fin_con_ritmo(R, rit[k] if rit else 0, hoy)) for k in ("por_dia", "opt", "pes")}
        fin_habil = _fin_con_habil(R * mpm["minutos"], hoy, habil, hoy_min, uso_total["reserva_dia"])
        cursos.append({
            "id": n["id"], "nombre": n["nombre"], "total": N, "hechas": H, "faltan": R,
            "serie": serie, "ritmo": None if not rit else {
                "misiones_semana": round(rit["por_dia"] * 7, 1), "opt_semana": round(rit["opt"] * 7, 1),
                "pes_semana": round(rit["pes"] * 7, 1), "misiones_medidas": rit["n"], "dias": rit["dias"]},
            "min_por_mision": mpm,
            "fin": {"estimado": fin["por_dia"], "optimista": fin["opt"], "pesimista": fin["pes"], "habil": _iso(fin_habil)},
            "uso": _uso_semanal(hoy, habil, n["id"]),
        })
        todas_fechas += fechas
        total_n += N
        total_h += H
        total_min += R * mpm["minutos"]
    # total: los cursos uno tras otro, con el ritmo global
    rit = _ritmo(sorted(todas_fechas), hoy)
    R = total_n - total_h
    serie_total = []
    if cursos:
        base = total_h - len(todas_fechas)
        acc = base
        fs = sorted(todas_fechas)
        if fs:
            serie_total.append({"fecha": (fs[0] - timedelta(days=1)).isoformat(), "hechas": base})
        for f in sorted(set(fs)):
            acc += fs.count(f)
            serie_total.append({"fecha": f.isoformat(), "hechas": acc})
    total = {
        "total": total_n, "hechas": total_h, "faltan": R, "serie": serie_total,
        "ritmo": None if not rit else {"misiones_semana": round(rit["por_dia"] * 7, 1), "opt_semana": round(rit["opt"] * 7, 1),
                                       "pes_semana": round(rit["pes"] * 7, 1), "misiones_medidas": rit["n"], "dias": rit["dias"]},
        "fin": {"estimado": _iso(_fin_con_ritmo(R, rit["por_dia"] if rit else 0, hoy)),
                "optimista": _iso(_fin_con_ritmo(R, rit["opt"] if rit else 0, hoy)),
                "pesimista": _iso(_fin_con_ritmo(R, rit["pes"] if rit else 0, hoy)),
                "habil": _iso(_fin_con_habil(total_min, hoy, habil, hoy_min, uso_total["reserva_dia"]))},
        "uso": uso_total, "orden": [c["id"] for c in cursos],
    }
    return {"hoy": hoy.isoformat(), "cursos": cursos, "total": total, "sin_plan": sin_plan,
            "habil_configurado": any(habil["semana"][str(i)] for i in range(7)),
            "metodo": ("Ritmo real: misiones hechas por día en las últimas 4 semanas (mínimo 7 días). Rango del 80 %: "
                       "ritmo × (1 ± 1.28/√n), con n = misiones con fecha en la ventana. Según tiempo hábil: misiones que "
                       "faltan × minutos por misión, gastando cada día sus minutos hábiles menos lo que se va en tarjetas y hojas.")}


def resumen_tiempo(desde=None, hasta=None, curso=None):
    hoy = store.hoy_local()
    filas = store.listar_tiempo(desde, hasta, curso)
    por_tipo, por_curso = {}, {}
    for r in filas:
        m = r.get("minutos") or 0
        por_tipo[r["tipo"]] = round(por_tipo.get(r["tipo"], 0) + m, 1)
        k = r.get("curso") or "general"
        por_curso[k] = round(por_curso.get(k, 0) + m, 1)
    semana0 = hoy - timedelta(days=hoy.weekday())
    sem = store.minutos_por_dia(semana0, hoy)
    habil = store.tiempo_habil()
    return {
        "ratos": filas, "por_tipo": por_tipo, "por_curso": por_curso,
        "sin_cerrar": [r for r in filas if r["estado"] == "sin_cerrar"],
        "abiertas": [r for r in filas if r["estado"] == "abierta"],
        "esta_semana": {"minutos": round(sum(v for d in sem.values() for v in d.values())),
                        "habiles": sum(store.minutos_habiles(semana0 + timedelta(days=i), habil) for i in range(7))},
    }
