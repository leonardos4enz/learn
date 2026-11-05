"""La imagen del plan de hoy que el bot manda por Telegram en la mañana: el plan, la racha, el tiempo de la semana
contra el tiempo hábil y la gráfica de avance con la predicción. Se dibuja con Pillow y la fuente Nunito (OFL),
al doble de tamaño y luego se reduce, para que las líneas salgan suaves. Telegram no acepta SVG como foto, por eso PNG.
"""
import io
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import store, tiempo

FUENTE = Path(__file__).resolve().parent / "static" / "fuentes" / "Nunito.ttf"
S = 2                     # se dibuja al doble y se reduce (antialiasing)
W, H = 1080, 1350

C = {"bg": "#F5F6F7", "panel": "#FFFFFF", "panel2": "#F3F5F6", "ink": "#16191D", "muted": "#59636E", "faint": "#8A939C",
     "line": "#E2E5E9", "acc": "#0B7D67", "acc_soft": "#E2F2EE", "acc_ink": "#095E4E", "warn": "#9A5B00",
     "naranja": "#FF8A1F", "naranja2": "#FFD23F", "naranja_ink": "#C25A00", "azul": "#2F6BE0"}
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MESES_L = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
_cache = {}


def fuente(tam, peso=400):
    k = (tam, peso)
    if k not in _cache:
        f = ImageFont.truetype(str(FUENTE), tam * S)
        try:
            f.set_variation_by_axes([peso])
        except Exception:
            pass
        _cache[k] = f
    return _cache[k]


def _rgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def fecha_corta(iso):
    if not iso:
        return "—"
    d = datetime.strptime(iso[:10], "%Y-%m-%d").date()
    return f"{d.day} {MESES[d.month - 1]}" + (f" {d.year}" if d.year != store.hoy_local().year else "")


def duracion(mins):
    mins = int(round(mins or 0))
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h} h {m:02d}" if m else f"{h} h"


class Lienzo:
    def __init__(self):
        self.img = Image.new("RGBA", (W * S, H * S), _rgb(C["bg"]))
        self.d = ImageDraw.Draw(self.img)

    def p(self, *xy):
        return [v * S for v in xy]

    def caja(self, x, y, w, h, color="panel", r=28, borde="line"):
        self.d.rounded_rectangle(self.p(x, y, x + w, y + h), r * S, fill=_rgb(C[color]), outline=_rgb(C[borde]) if borde else None, width=2 * S if borde else 0)

    def texto(self, x, y, s, tam, peso=400, color="ink", ancla="la"):
        self.d.text((x * S, y * S), s, font=fuente(tam, peso), fill=_rgb(C.get(color, color)), anchor=ancla)

    def ancho(self, s, tam, peso=400):
        return self.d.textlength(s, font=fuente(tam, peso)) / S

    def etiqueta(self, x, y, s):
        # rótulo en mayúsculas con espaciado, como los .k de la app
        for ch in s.upper():
            self.texto(x, y, ch, 19, 800, "muted")
            x += self.ancho(ch, 19, 800) + 2.2

    def recortar(self, s, tam, peso, maxw):
        if self.ancho(s, tam, peso) <= maxw:
            return s
        while s and self.ancho(s + "…", tam, peso) > maxw:
            s = s[:-1]
        return s + "…"

    def linea(self, pts, color, grosor=3, guion=None, alpha=255):
        pts = [(x * S, y * S) for x, y in pts]
        if not guion:
            self.d.line(pts, fill=_rgb(C.get(color, color), alpha), width=grosor * S, joint="curve")
            return
        on, off = guion[0] * S, guion[1] * S
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            largo = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** .5
            t = 0
            while t < largo:
                t1 = min(t + on, largo)
                a, b = t / largo, t1 / largo
                self.d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                            fill=_rgb(C.get(color, color), alpha), width=grosor * S)
                t = t1 + off

    def poligono(self, pts, color, alpha):
        capa = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(capa).polygon([(x * S, y * S) for x, y in pts], fill=_rgb(C[color], alpha))
        self.img.alpha_composite(capa)
        self.d = ImageDraw.Draw(self.img)

    def circulo(self, cx, cy, r, fill, borde=None, grosor=3):
        self.d.ellipse(self.p(cx - r, cy - r, cx + r, cy + r), fill=_rgb(C.get(fill, fill)) if fill else None,
                       outline=_rgb(C.get(borde, borde)) if borde else None, width=grosor * S)

    def check(self, cx, cy, r, color="panel"):
        self.linea([(cx - r * .45, cy + r * .02), (cx - r * .1, cy + r * .38), (cx + r * .5, cy - r * .35)], color, 4)

    def fuego(self, x, y, h, on=True):
        # la llama de la app (mismo trazo, simplificado en polígonos)
        k = h / 48
        def pt(px, py):
            return (x + px * k, y + py * k)
        ext = [pt(20.5, 1.5), pt(27, 10), pt(33, 18.5), pt(35, 27), pt(33, 35), pt(26, 41), pt(20, 42.3), pt(12, 41),
               pt(6, 35.5), pt(4.6, 26), pt(7, 18), pt(11.2, 13.3), pt(12.5, 17.5), pt(15.5, 20), pt(15.5, 12), pt(18, 6)]
        nuc = [pt(20.8, 21.6), pt(25, 25.5), pt(27.3, 31), pt(26, 37), pt(20, 40.8), pt(15, 39), pt(13.1, 33.5),
               pt(14.5, 29.5), pt(16.8, 27), pt(18, 29.5), pt(19.3, 30.7), pt(19.4, 26)]
        self.poligono(ext, "naranja" if on else "line", 255)
        self.poligono(nuc, "naranja2" if on else "panel2", 255)

    def png(self):
        out = self.img.resize((W, H), Image.LANCZOS).convert("RGB")
        buf = io.BytesIO()
        out.save(buf, "PNG", optimize=True)
        return buf.getvalue()


def _grafica(L, x, y, w, h, pred):
    """Misiones hechas (acumuladas) contra fecha: real, proyección con su banda y la línea según el tiempo hábil."""
    serie, fin, N = pred["serie"], pred["fin"], pred["total"]
    hoy = store.hoy_local()
    d = lambda s: datetime.strptime(s[:10], "%Y-%m-%d").date()
    x0 = d(serie[0]["fecha"]) if serie else hoy - timedelta(days=7)
    finales = [d(v) for v in (fin.get("pesimista"), fin.get("estimado"), fin.get("habil"), fin.get("optimista")) if v]
    x1 = max([hoy + timedelta(days=14)] + finales)
    if (x1 - x0).days > 400:
        x1 = x0 + timedelta(days=400)
    dias = max(1, (x1 - x0).days)
    pl, pr, pt_, pb = 56, 20, 16, 46
    gx, gy, gw, gh = x + pl, y + pt_, w - pl - pr, h - pt_ - pb
    X = lambda f: gx + gw * min(1, max(0, (f - x0).days / dias))
    Y = lambda v: gy + gh - gh * (v / max(1, N))
    # rejilla
    for v in (0, N // 2, N):
        L.linea([(gx, Y(v)), (gx + gw, Y(v))], "line", 2)
        L.texto(gx - 12, Y(v), str(v), 20, 700, "faint", "rm")
    H_ = pred["hechas"]
    # banda optimista/pesimista
    if fin.get("optimista") and fin.get("pesimista"):
        L.poligono([(X(hoy), Y(H_)), (X(d(fin["optimista"])), Y(N)), (X(d(fin["pesimista"])), Y(N))], "acc", 46)
    if fin.get("habil"):
        L.linea([(X(hoy), Y(H_)), (X(d(fin["habil"])), Y(N))], "azul", 3, guion=(3, 7))
    if fin.get("estimado"):
        L.linea([(X(hoy), Y(H_)), (X(d(fin["estimado"])), Y(N))], "acc", 3, guion=(12, 8))
        L.circulo(X(d(fin["estimado"])), Y(N), 7, "panel", "acc", 3)
    # real
    pts = []
    for i, p in enumerate(serie):
        if i:
            pts.append((X(d(p["fecha"])), pts[-1][1]))
        pts.append((X(d(p["fecha"])), Y(p["hechas"])))
    if pts:
        pts.append((X(hoy), pts[-1][1]))
        L.linea(pts, "acc", 5)
        for p in serie[1:]:
            L.circulo(X(d(p["fecha"])), Y(p["hechas"]), 6, "acc")
    # hoy
    L.linea([(X(hoy), gy - 4), (X(hoy), gy + gh)], "ink", 2, guion=(4, 5), alpha=150)
    L.texto(X(hoy), gy + gh + 14, "hoy", 19, 800, "ink", "ma")
    if X(hoy) - gx > 90:
        L.texto(gx, gy + gh + 14, fecha_corta(x0.isoformat()), 19, 600, "faint", "la")
    L.texto(gx + gw, gy + gh + 14, fecha_corta(x1.isoformat()), 19, 600, "faint", "ra")


def plan_de_hoy_png(cid=None):
    hoy = store.hoy_local()
    if not cid:
        cid = next((n["id"] for _, n in store.iter_cursos() if n.get("estado") == "actual"), None)
    nombre = next((n["nombre"] for _, n in store.iter_cursos() if n["id"] == cid), "")
    plan = store.plan_de_hoy(cid) if cid else {"pasos": [], "siguiente": None}
    rch = store.racha()
    pred = tiempo.prediccion()
    pc = next((c for c in pred["cursos"] if c["id"] == cid), None)
    ayer = hoy - timedelta(days=1)
    min_ayer = sum(store.minutos_por_dia(ayer, ayer).get(ayer.isoformat(), {}).values())
    sem = tiempo.resumen_tiempo(hoy - timedelta(days=hoy.weekday()), hoy)["esta_semana"]
    habil_hoy = store.minutos_habiles(hoy)

    L = Lienzo()
    M = 52
    # encabezado
    titulo = f"Hoy, {store.DIAS_SEMANA[hoy.weekday()]} {hoy.day} de {MESES_L[hoy.month - 1]}"
    tam = 50
    while tam > 34 and L.ancho(titulo, tam, 800) > W - 2 * M - 350:
        tam -= 2
    L.texto(M, 54 + (50 - tam) * .6, titulo, tam, 800)
    L.texto(M, 122, L.recortar(f"Plan de hoy · {nombre}" if nombre else "Plan de hoy", 27, 600, 600), 27, 600, "muted")
    # racha
    rx, ry, rw = W - M - 330, 46, 330
    L.caja(rx, ry, rw, 118, r=22)
    L.fuego(rx + 22, ry + 22, 70, rch["hoy_hecho"] or rch["dias"] > 0)
    L.texto(rx + 92, ry + 22, str(rch["dias"]), 40, 800, "naranja_ink")
    L.texto(rx + 100 + L.ancho(str(rch["dias"]), 40, 800), ry + 36, "día de racha" if rch["dias"] == 1 else "días de racha", 22, 700, "muted")
    for i, s in enumerate(rch["semana"]):
        cx, cy = rx + 104 + i * 32, ry + 90
        hecho = s["hecho"]
        L.circulo(cx, cy, 12, "naranja" if hecho else "panel2", "naranja_ink" if hecho else ("ink" if s["fecha"] == hoy.isoformat() else "line"), 2)
        L.texto(cx, cy, "LMMJVSD"[i], 14, 800, "#3A1A00" if hecho else "faint", "mm")

    # plan
    y = 196
    pasos = plan["pasos"]
    alto = 92 + max(1, len(pasos)) * 92
    L.caja(M, y, W - 2 * M, alto)
    hechos = sum(p["hecho"] for p in pasos)
    L.etiqueta(M + 30, y + 30, f"Plan de hoy · {hechos} de {len(pasos)}")
    sig = plan.get("siguiente")
    if sig:
        L.texto(W - M - 30, y + 26, L.recortar(f"{sig['id']} · {sig.get('titulo', '')}", 22, 800, 520), 22, 800, "acc_ink", "ra")
    yy = y + 76
    primero = next((i for i, p in enumerate(pasos) if not p["hecho"]), -1)
    if not pasos:
        L.texto(M + 30, yy + 20, "Sin plan para hoy: abre una sesión con el tutor.", 26, 600, "muted")
    for i, p in enumerate(pasos):
        now = i == primero
        L.caja(M + 22, yy, W - 2 * M - 44, 80, "acc_soft" if now else "panel2", r=18, borde="acc" if now else None)
        cx, cy = M + 64, yy + 40
        if p["hecho"]:
            L.circulo(cx, cy, 20, "acc")
            L.check(cx, cy, 20, "panel")
        else:
            L.circulo(cx, cy, 20, "panel", "acc" if now else "line", 3)
            L.texto(cx, cy, str(i + 1), 21, 800, "acc_ink" if now else "muted", "mm")
        L.texto(M + 102, yy + 14, L.recortar(p["titulo"], 27, 800, W - 2 * M - 150), 27, 800, "faint" if p["hecho"] else "ink")
        L.texto(M + 102, yy + 48, L.recortar(p["detalle"], 20, 600, W - 2 * M - 150), 20, 600, "muted")
        yy += 92

    # tiempo
    y = y + alto + 22
    L.caja(M, y, W - 2 * M, 150)
    L.etiqueta(M + 30, y + 28, "Tu tiempo")
    col = (W - 2 * M - 60) / 3
    datos = [("Ayer", duracion(min_ayer)), ("Esta semana", duracion(sem["minutos"])),
             ("Hábil hoy", duracion(habil_hoy) if habil_hoy else "libre")]
    for i, (k, v) in enumerate(datos):
        L.texto(M + 30 + i * col, y + 62, v, 34, 800)
        L.texto(M + 30 + i * col, y + 106, k, 20, 600, "muted")
    if sem["habiles"]:
        pct = min(1, sem["minutos"] / sem["habiles"])
        bx, by, bw = M + 30 + col, y + 140, col - 40
        L.d.rounded_rectangle(L.p(bx, by - 6, bx + bw, by), 3 * S, fill=_rgb(C["panel2"]))
        if pct > 0:
            L.d.rounded_rectangle(L.p(bx, by - 6, bx + max(6, bw * pct), by), 3 * S, fill=_rgb(C["acc"]))
        L.texto(bx + L.ancho("Esta semana", 20, 600) + 8, y + 107, f"de {duracion(sem['habiles'])}", 18, 700, "faint")

    # predicción
    y = y + 150 + 22
    alto = H - y - 70
    L.caja(M, y, W - 2 * M, alto)
    L.etiqueta(M + 30, y + 28, "¿Cuándo terminas?")
    if pc:
        f = pc["fin"]
        L.texto(M + 30, y + 58, L.recortar(f"{pc['hechas']} de {pc['total']} misiones", 22, 700, 400), 22, 700, "muted")
        if f.get("estimado"):
            L.texto(W - M - 30, y + 22, f"~ {fecha_corta(f['estimado'])}", 40, 800, "acc_ink", "ra")
            L.texto(W - M - 30, y + 74, f"entre {fecha_corta(f['optimista'])} y {fecha_corta(f['pesimista'])}", 20, 700, "muted", "ra")
        else:
            L.texto(W - M - 30, y + 30, "Falta ritmo para predecir", 26, 800, "muted", "ra")
        _grafica(L, M + 18, y + 110, W - 2 * M - 40, alto - 170, pc)
        ly = y + alto - 42
        lx = M + 30
        for color, guion, txt in (("acc", None, "real"), ("acc", (12, 8), "tu ritmo"), ("azul", (3, 7), "según tiempo hábil")):
            L.linea([(lx, ly + 11), (lx + 34, ly + 11)], color, 4 if not guion else 3, guion=guion)
            L.texto(lx + 42, ly, txt, 19, 700, "muted")
            lx += 42 + L.ancho(txt, 19, 700) + 30
        if f.get("habil"):
            L.texto(W - M - 30, ly, f"hábil: {fecha_corta(f['habil'])}", 19, 800, "azul", "ra")
    else:
        L.texto(M + 30, y + 70, "Este curso todavía no tiene plan en la app.", 26, 600, "muted")
    L.circulo(M + 8, H - 38, 7, "acc")
    L.texto(M + 24, H - 38, "Mi Tutor", 20, 800, "muted", "lm")
    L.texto(W - M, H - 38, "Abre la app para ver el detalle", 18, 600, "faint", "rm")
    return L.png()
