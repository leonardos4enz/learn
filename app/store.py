"""Datos de Mi Tutor: SQLite en un solo archivo (en producción vive en el volumen /data).

Tablas
  kv        valores sueltos: el árbol de estudios, el secreto de sesiones, el estado del bot
  cursos    por curso: datos (JSON con misiones, banco, hojas…) y plan (Markdown)
  hojas     hojas imprimibles (HTML)
  pantalla  lo que el tutor muestra en vivo
  tarjetas  tarjetas de repaso espaciado (estado FSRS en JSON)
  repasos   cada respuesta a una tarjeta
  lecciones una lección por misión (pasos JSON); su avance (completada, predicciones) no se pisa al reescribirla
  mejoras   errores y propuestas que registran Leo o el tutor
Las imágenes de las lecciones viven como archivos en DATA_DIR/imagenes/<curso>/.
"""
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fsrs import Card, Rating, Scheduler

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DB_PATH = DATA_DIR / "tutor.db"
IMG_DIR = DATA_DIR / "imagenes"
IMG_MAX = int(os.environ.get("IMAGEN_MAX_KB", "1500")) * 1024
TZ = ZoneInfo(os.environ.get("TZ_NAME", "America/Mexico_City"))
NUEVAS_POR_DIA = int(os.environ.get("NUEVAS_POR_DIA", "20"))
DOMINADA_DIAS = 21  # como Anki: una tarjeta es "madura" cuando su intervalo pasa de 21 días
PANTALLA_MAX = 60

SCHEDULER = Scheduler(desired_retention=0.9)
RATINGS = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}

_lock = threading.Lock()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


_con = _connect()
_con.executescript("""
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS cursos (id TEXT PRIMARY KEY, datos TEXT, plan TEXT, actualizado TEXT);
CREATE TABLE IF NOT EXISTS hojas (curso TEXT, archivo TEXT, titulo TEXT, html TEXT, creada TEXT, PRIMARY KEY (curso, archivo));
CREATE TABLE IF NOT EXISTS pantalla (id INTEGER PRIMARY KEY, curso TEXT, ts TEXT, titulo TEXT, tipo TEXT, contenido TEXT,
  notas TEXT, resaltar TEXT, respuesta TEXT);
CREATE TABLE IF NOT EXISTS tarjetas (id INTEGER PRIMARY KEY AUTOINCREMENT, curso TEXT, modulo TEXT, mision TEXT,
  frente TEXT, reverso TEXT, creada TEXT, fsrs TEXT, due TEXT, nueva INTEGER DEFAULT 1, suspendida INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS tarjetas_curso ON tarjetas (curso, suspendida, due);
CREATE TABLE IF NOT EXISTS repasos (id INTEGER PRIMARY KEY AUTOINCREMENT, tarjeta_id INTEGER REFERENCES tarjetas(id) ON DELETE CASCADE,
  curso TEXT, rating INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS lecciones (curso TEXT, mision_id TEXT, modulo TEXT, titulo TEXT, pasos TEXT, fuentes TEXT,
  tarjetas TEXT, actualizado TEXT, completada TEXT, predicciones TEXT, PRIMARY KEY (curso, mision_id));
CREATE TABLE IF NOT EXISTS mejoras (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, reporta TEXT, curso TEXT,
  descripcion TEXT, estado TEXT DEFAULT 'nueva', nota TEXT, actualizado TEXT);
""")


def now_utc():
    return datetime.now(timezone.utc)


def hoy_local():
    return datetime.now(TZ).date()


def _q(sql, args=(), one=False):
    with _lock:
        cur = _con.execute(sql, args)
        rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def _x(sql, args=()):
    with _lock:
        cur = _con.execute(sql, args)
        _con.commit()
        return cur.lastrowid


# ---------- kv ----------
def kv_get(k, default=None):
    r = _q("SELECT v FROM kv WHERE k=?", (k,), one=True)
    return json.loads(r["v"]) if r else default


def kv_set(k, v):
    _x("INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v, ensure_ascii=False)))


def secret():
    s = kv_get("secret")
    if not s:
        s = secrets.token_hex(32)
        kv_set("secret", s)
    return s


# ---------- árbol y cursos ----------
def arbol():
    return kv_get("arbol", [])


def guardar_arbol(nodos):
    if not isinstance(nodos, list):
        raise ValueError("El árbol debe ser una lista de nodos.")
    ids = []

    def check(ns):
        for n in ns:
            if not isinstance(n, dict) or not n.get("id") or not n.get("nombre"):
                raise ValueError("Cada nodo necesita 'id' y 'nombre'.")
            ids.append(n["id"])
            if "hijos" in n:
                check(n["hijos"])
    check(nodos)
    if len(ids) != len(set(ids)):
        raise ValueError("Hay ids repetidos en el árbol.")
    kv_set("arbol", nodos)


def iter_cursos(nodos=None, ruta=()):
    for n in (arbol() if nodos is None else nodos):
        if n.get("curso") or ("hijos" not in n):
            yield ruta, n
        else:
            yield from iter_cursos(n["hijos"], ruta + (n["nombre"],))


def curso_existe(cid):
    return any(n["id"] == cid for _, n in iter_cursos())


def leer_datos(cid):
    r = _q("SELECT datos FROM cursos WHERE id=?", (cid,), one=True)
    return json.loads(r["datos"]) if r and r["datos"] else None


def leer_plan(cid):
    r = _q("SELECT plan FROM cursos WHERE id=?", (cid,), one=True)
    return r["plan"] if r else None


def guardar_datos(cid, datos):
    if not isinstance(datos, dict):
        raise ValueError("'datos' debe ser un objeto JSON.")
    for k in ("misiones", "sesiones", "banco", "examenes", "modulos"):
        if k in datos and not isinstance(datos[k], list):
            raise ValueError(f"'{k}' debe ser una lista.")
    if "hojas" in datos and not isinstance(datos["hojas"], dict):
        raise ValueError("'hojas' debe ser un objeto {archivo: {...}}.")
    ids = {m.get("id") for m in datos.get("misiones", [])}
    if datos.get("siguiente") and datos["siguiente"] not in ids:
        raise ValueError(f"'siguiente' ({datos['siguiente']}) no es el id de ninguna misión.")
    datos["curso"] = cid
    datos["actualizado"] = hoy_local().isoformat()
    _x("""INSERT INTO cursos (id, datos, actualizado) VALUES (?, ?, ?)
          ON CONFLICT(id) DO UPDATE SET datos=excluded.datos, actualizado=excluded.actualizado""",
       (cid, json.dumps(datos, ensure_ascii=False), now_utc().isoformat()))


def guardar_plan(cid, plan):
    _x("""INSERT INTO cursos (id, plan, actualizado) VALUES (?, ?, ?)
          ON CONFLICT(id) DO UPDATE SET plan=excluded.plan, actualizado=excluded.actualizado""",
       (cid, plan, now_utc().isoformat()))


def resumen(cid):
    d = leer_datos(cid)
    t = stats_tarjetas(cid)
    if not d:
        return {"tiene_plan": False, "tarjetas": t}
    ms = d.get("misiones", [])
    return {"tiene_plan": True, "hechas": sum(1 for m in ms if m.get("estado") == "hecha"), "total": len(ms),
            "siguiente": d.get("siguiente"), "banco": len(d.get("banco", [])), "tarjetas": t}


def arbol_con_resumen():
    def anotar(ns):
        out = []
        for n in ns:
            m = dict(n)
            if n.get("curso") or "hijos" not in n:
                m["curso"] = True
                m["resumen"] = resumen(n["id"])
            else:
                m["hijos"] = anotar(n["hijos"])
            out.append(m)
        return out
    return anotar(arbol())


# ---------- hojas ----------
def guardar_hoja(cid, archivo, html):
    import re
    if not re.fullmatch(r"[\w.-]+\.html", archivo):
        raise ValueError("El nombre de la hoja debe ser algo como '01-mision.html'.")
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    _x("""INSERT INTO hojas (curso, archivo, titulo, html, creada) VALUES (?, ?, ?, ?, ?)
          ON CONFLICT(curso, archivo) DO UPDATE SET titulo=excluded.titulo, html=excluded.html""",
       (cid, archivo, m.group(1).strip() if m else archivo, html, now_utc().isoformat()))


def listar_hojas(cid):
    return [dict(r) for r in _q("SELECT archivo, titulo, creada FROM hojas WHERE curso=? ORDER BY archivo", (cid,))]


def leer_hoja(cid, archivo):
    r = _q("SELECT html FROM hojas WHERE curso=? AND archivo=?", (cid, archivo), one=True)
    return r["html"] if r else None


# ---------- pantalla ----------
def mostrar(cid, titulo, tipo, contenido, notas=None, resaltar=None, respuesta=None):
    if tipo not in ("mermaid", "codigo", "markdown", "html", "predice"):
        raise ValueError("tipo debe ser mermaid, codigo, markdown, html o predice.")
    if tipo == "predice" and not respuesta:
        raise ValueError("El tipo 'predice' necesita 'respuesta'.")
    iid = int(now_utc().timestamp() * 1000)
    _x("INSERT INTO pantalla (id, curso, ts, titulo, tipo, contenido, notas, resaltar, respuesta) VALUES (?,?,?,?,?,?,?,?,?)",
       (iid, cid, datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), titulo, tipo, contenido, notas,
        json.dumps(resaltar or []), respuesta))
    _x("DELETE FROM pantalla WHERE id NOT IN (SELECT id FROM pantalla ORDER BY id DESC LIMIT ?)", (PANTALLA_MAX,))
    return iid


def pantalla():
    rows = _q("SELECT * FROM pantalla ORDER BY id")
    out = []
    for r in rows:
        d = dict(r)
        d["resaltar"] = json.loads(d["resaltar"] or "[]")
        out.append({k: v for k, v in d.items() if v is not None})
    return out


# ---------- tarjetas (FSRS) ----------
def crear_tarjetas(cid, lista):
    existentes = {r["frente"].strip().lower() for r in _q("SELECT frente FROM tarjetas WHERE curso=?", (cid,))}
    creadas, repetidas = [], []
    for t in lista:
        frente, reverso = (t.get("frente") or "").strip(), (t.get("reverso") or "").strip()
        if not frente or not reverso:
            raise ValueError("Cada tarjeta necesita 'frente' y 'reverso'.")
        if frente.lower() in existentes:
            repetidas.append(frente)
            continue
        c = Card()
        tid = _x("""INSERT INTO tarjetas (curso, modulo, mision, frente, reverso, creada, fsrs, due, nueva)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                 (cid, str(t.get("modulo") or ""), str(t.get("mision") or ""), frente, reverso,
                  now_utc().isoformat(), c.to_json(), c.due.isoformat()))
        existentes.add(frente.lower())
        creadas.append(tid)
    return {"creadas": len(creadas), "ids": creadas, "repetidas": repetidas}


def _fin_de_hoy_utc():
    fin = datetime.combine(hoy_local() + timedelta(days=1), datetime.min.time(), TZ)
    return fin.astimezone(timezone.utc)


def _inicio_de_hoy_utc():
    return datetime.combine(hoy_local(), datetime.min.time(), TZ).astimezone(timezone.utc)


def nuevas_hoy(cid):
    r = _q("""SELECT COUNT(DISTINCT r.tarjeta_id) n FROM repasos r
              WHERE r.curso=? AND r.ts>=? AND r.tarjeta_id IN
              (SELECT tarjeta_id FROM repasos GROUP BY tarjeta_id HAVING MIN(ts)>=?)""",
           (cid, _inicio_de_hoy_utc().isoformat(), _inicio_de_hoy_utc().isoformat()), one=True)
    return r["n"] if r else 0


def cursos_con_tarjetas():
    return [r["curso"] for r in _q("SELECT DISTINCT curso FROM tarjetas WHERE suspendida=0")]


def cola(cid):
    """Tarjetas para repasar ahora: las vencidas (hasta el fin del día) y nuevas hasta el límite diario."""
    cursos = cursos_con_tarjetas() if cid == "todos" else [cid]
    out = []
    for c in cursos:
        vencidas = _q("SELECT * FROM tarjetas WHERE curso=? AND suspendida=0 AND nueva=0 AND due<=? ORDER BY due",
                      (c, _fin_de_hoy_utc().isoformat()))
        cupo = max(0, NUEVAS_POR_DIA - nuevas_hoy(c))
        nuevas = _q("SELECT * FROM tarjetas WHERE curso=? AND suspendida=0 AND nueva=1 ORDER BY id LIMIT ?", (c, cupo))
        out += [_tarjeta_publica(r) for r in list(vencidas) + list(nuevas)]
    ahora = now_utc().isoformat()
    # primero lo que ya venció, luego lo que vence más tarde hoy (pasos de aprendizaje)
    out.sort(key=lambda t: (t["due"] > ahora, t["nueva"], t["due"]))
    return out


def _intervalo_texto(desde, hasta):
    s = (hasta - desde).total_seconds()
    if s < 3600:
        return f"{max(1, round(s / 60))} min"
    if s < 86400:
        return f"{round(s / 3600)} h"
    d = s / 86400
    if d < 30:
        return f"{round(d)} d"
    if d < 365:
        return f"{round(d / 30)} mes"
    return f"{d / 365:.1f} años"


def _tarjeta_publica(r):
    card = Card.from_json(r["fsrs"])
    ahora = now_utc()
    previews = {}
    for n, rating in RATINGS.items():
        c2, _ = SCHEDULER.review_card(Card.from_json(r["fsrs"]), rating, ahora)
        previews[n] = _intervalo_texto(ahora, c2.due)
    return {"id": r["id"], "curso": r["curso"], "modulo": r["modulo"], "mision": r["mision"], "frente": r["frente"],
            "reverso": r["reverso"], "due": r["due"], "nueva": r["nueva"], "estabilidad": card.stability,
            "intervalos": previews}


def repasar(tid, rating):
    if rating not in RATINGS:
        raise ValueError("rating debe ser 1 (Otra vez), 2 (Difícil), 3 (Bien) o 4 (Fácil).")
    r = _q("SELECT * FROM tarjetas WHERE id=?", (tid,), one=True)
    if not r:
        raise ValueError("No existe esa tarjeta.")
    card, _ = SCHEDULER.review_card(Card.from_json(r["fsrs"]), RATINGS[rating], now_utc())
    _x("UPDATE tarjetas SET fsrs=?, due=?, nueva=0 WHERE id=?", (card.to_json(), card.due.isoformat(), tid))
    _x("INSERT INTO repasos (tarjeta_id, curso, rating, ts) VALUES (?, ?, ?, ?)", (tid, r["curso"], rating, now_utc().isoformat()))
    return {"id": tid, "proxima": card.due.isoformat(), "en": _intervalo_texto(now_utc(), card.due)}


def editar_tarjeta(tid, frente=None, reverso=None, suspendida=None):
    r = _q("SELECT id FROM tarjetas WHERE id=?", (tid,), one=True)
    if not r:
        raise ValueError("No existe esa tarjeta.")
    if frente is not None:
        _x("UPDATE tarjetas SET frente=? WHERE id=?", (frente, tid))
    if reverso is not None:
        _x("UPDATE tarjetas SET reverso=? WHERE id=?", (reverso, tid))
    if suspendida is not None:
        _x("UPDATE tarjetas SET suspendida=? WHERE id=?", (1 if suspendida else 0, tid))


def listar_tarjetas(cid):
    rows = _q("SELECT * FROM tarjetas WHERE curso=? ORDER BY id", (cid,))
    out = []
    for r in rows:
        card = Card.from_json(r["fsrs"])
        fallos = _q("SELECT COUNT(*) n FROM repasos WHERE tarjeta_id=? AND rating=1", (r["id"],), one=True)["n"]
        out.append({"id": r["id"], "modulo": r["modulo"], "mision": r["mision"], "frente": r["frente"], "reverso": r["reverso"],
                    "nueva": bool(r["nueva"]), "suspendida": bool(r["suspendida"]), "due": r["due"],
                    "estabilidad_dias": round(card.stability or 0, 1), "fallos": fallos})
    return out


def stats_tarjetas(cid):
    rows = _q("SELECT modulo, fsrs, due, nueva FROM tarjetas WHERE curso=? AND suspendida=0", (cid,))
    fin = _fin_de_hoy_utc().isoformat()
    total = len(rows)
    nuevas = sum(1 for r in rows if r["nueva"])
    vencen = sum(1 for r in rows if not r["nueva"] and r["due"] <= fin)
    por_mod = {}
    dominadas = 0
    for r in rows:
        st = Card.from_json(r["fsrs"]).stability or 0
        dom = (not r["nueva"]) and st >= DOMINADA_DIAS
        dominadas += dom
        m = por_mod.setdefault(r["modulo"] or "", {"total": 0, "dominadas": 0})
        m["total"] += 1
        m["dominadas"] += dom
    hoy = _q("SELECT COUNT(*) n FROM repasos WHERE curso=? AND ts>=?", (cid, _inicio_de_hoy_utc().isoformat()), one=True)["n"]
    return {"total": total, "nuevas": nuevas, "para_hoy": vencen + min(nuevas, max(0, NUEVAS_POR_DIA - nuevas_hoy(cid))),
            "vencidas": vencen, "dominadas": dominadas, "dominio": round(100 * dominadas / total) if total else 0,
            "por_modulo": por_mod, "repasadas_hoy": hoy}


def repasos_hoy_total():
    return _q("SELECT COUNT(*) n FROM repasos WHERE ts>=?", (_inicio_de_hoy_utc().isoformat(),), one=True)["n"]


# ---------- lecciones ----------
TIPOS_PASO = ("markdown", "codigo", "mermaid", "predice", "imagen")
_ID_CURSO = re.compile(r"[a-z0-9][a-z0-9_-]{0,40}")


def _validar_pasos(pasos):
    if not isinstance(pasos, list) or not pasos:
        raise ValueError("'pasos' debe ser una lista con al menos un paso.")
    out = []
    for i, p in enumerate(pasos, 1):
        if not isinstance(p, dict):
            raise ValueError(f"Paso {i}: debe ser un objeto.")
        tipo = p.get("tipo")
        if tipo not in TIPOS_PASO:
            raise ValueError(f"Paso {i}: 'tipo' debe ser uno de {', '.join(TIPOS_PASO)}.")
        if tipo == "imagen":
            if not str(p.get("url", "")).startswith("/imagenes/") or not str(p.get("alt") or "").strip():
                raise ValueError(f"Paso {i}: una imagen necesita 'url' (la que devuelve subir_imagen) y 'alt'.")
        elif not str(p.get("contenido") or "").strip():
            raise ValueError(f"Paso {i}: falta 'contenido'.")
        if tipo == "predice" and not str(p.get("respuesta") or "").strip():
            raise ValueError(f"Paso {i}: un paso 'predice' necesita 'respuesta'.")
        if "resaltar" in p and not (isinstance(p["resaltar"], list) and all(isinstance(n, int) for n in p["resaltar"])):
            raise ValueError(f"Paso {i}: 'resaltar' es una lista de números de línea.")
        out.append({k: p[k] for k in ("tipo", "titulo", "contenido", "notas", "resaltar", "respuesta", "url", "alt")
                    if p.get(k) not in (None, "", [])})
    return out


def guardar_leccion(cid, mision_id, titulo, pasos, fuentes=None, tarjetas=None, modulo=None):
    mision_id = str(mision_id or "").strip()
    if not mision_id or not str(titulo or "").strip():
        raise ValueError("La lección necesita 'mision_id' y 'titulo'.")
    pasos = _validar_pasos(pasos)
    fuentes = [str(f) for f in (fuentes or [])]
    tarjetas = tarjetas or []
    for t in tarjetas:
        if not isinstance(t, dict) or not str(t.get("frente") or "").strip() or not str(t.get("reverso") or "").strip():
            raise ValueError("Cada tarjeta sugerida necesita 'frente' y 'reverso'.")
    if modulo is None:
        m = next((m for m in (leer_datos(cid) or {}).get("misiones", []) if str(m.get("id")) == mision_id), None)
        modulo = m.get("modulo") if m else ""
    _x("""INSERT INTO lecciones (curso, mision_id, modulo, titulo, pasos, fuentes, tarjetas, actualizado)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT(curso, mision_id) DO UPDATE SET modulo=excluded.modulo, titulo=excluded.titulo, pasos=excluded.pasos,
          fuentes=excluded.fuentes, tarjetas=excluded.tarjetas, actualizado=excluded.actualizado""",
       (cid, mision_id, str(modulo or ""), titulo.strip(), json.dumps(pasos, ensure_ascii=False),
        json.dumps(fuentes, ensure_ascii=False), json.dumps(tarjetas, ensure_ascii=False), now_utc().isoformat()))
    return {"pasos": len(pasos), "predice": sum(1 for p in pasos if p["tipo"] == "predice"), "tarjetas": len(tarjetas)}


def _leccion_dict(r, completa=True):
    pasos = json.loads(r["pasos"] or "[]")
    d = {"curso": r["curso"], "mision_id": r["mision_id"], "modulo": r["modulo"], "titulo": r["titulo"],
         "actualizado": r["actualizado"], "completada": r["completada"], "n_pasos": len(pasos)}
    if completa:
        d.update(pasos=pasos, fuentes=json.loads(r["fuentes"] or "[]"), tarjetas=json.loads(r["tarjetas"] or "[]"),
                 predicciones=json.loads(r["predicciones"] or "[]"))
    return d


def leer_leccion(cid, mision_id):
    r = _q("SELECT * FROM lecciones WHERE curso=? AND mision_id=?", (cid, str(mision_id)), one=True)
    return _leccion_dict(r) if r else None


def listar_lecciones(cid):
    return [_leccion_dict(r, completa=False) for r in _q("SELECT * FROM lecciones WHERE curso=? ORDER BY mision_id", (cid,))]


def completar_leccion(cid, mision_id, predicciones=None):
    """Marca la lección como leída y mete sus tarjetas sugeridas al mazo FSRS (las repetidas se ignoran)."""
    r = _q("SELECT * FROM lecciones WHERE curso=? AND mision_id=?", (cid, str(mision_id)), one=True)
    if not r:
        raise ValueError("No existe esa lección.")
    preds = []
    for p in (predicciones or [])[:50]:
        if isinstance(p, dict):
            preds.append({"paso": int(p.get("paso") or 0), "texto": str(p.get("texto") or "")[:2000],
                          "acerto": p.get("acerto") if p.get("acerto") in ("si", "casi", "no") else None})
    _x("UPDATE lecciones SET completada=?, predicciones=? WHERE curso=? AND mision_id=?",
       (now_utc().isoformat(), json.dumps(preds, ensure_ascii=False), cid, str(mision_id)))
    sugeridas = json.loads(r["tarjetas"] or "[]")
    res = {"creadas": 0, "repetidas": []}
    if sugeridas:
        res = crear_tarjetas(cid, [{**t, "modulo": t.get("modulo") or r["modulo"], "mision": t.get("mision") or r["mision_id"]}
                                   for t in sugeridas])
    return {"completada": True, "tarjetas_creadas": res["creadas"], "repetidas": len(res["repetidas"])}


# ---------- imágenes ----------
_FIRMAS = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg", b"GIF87a": "gif", b"GIF89a": "gif"}
MIME = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}


def _tipo_imagen(data):
    for firma, ext in _FIRMAS.items():
        if data.startswith(firma):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def guardar_imagen(cid, nombre, data):
    if not _ID_CURSO.fullmatch(cid or ""):
        raise ValueError("Curso inválido.")
    if len(data) > IMG_MAX:
        raise ValueError(f"La imagen pesa {len(data) // 1024} KB; el máximo es {IMG_MAX // 1024} KB. Redúcela antes de subirla.")
    ext = _tipo_imagen(data)
    if not ext:
        raise ValueError("Solo se aceptan PNG, JPG, GIF o WEBP (SVG no, por seguridad).")
    base = re.sub(r"[^a-z0-9_-]+", "-", Path(nombre or "imagen").stem.lower()).strip("-")[:60] or "imagen"
    carpeta = IMG_DIR / cid
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = f"{base}.{ext}"
    (carpeta / archivo).write_bytes(data)
    return {"url": f"/imagenes/{cid}/{archivo}", "kb": round(len(data) / 1024, 1)}


def ruta_imagen(cid, archivo):
    if not _ID_CURSO.fullmatch(cid) or not re.fullmatch(r"[a-z0-9_-]+\.(png|jpg|gif|webp)", archivo):
        return None
    p = IMG_DIR / cid / archivo
    return p if p.is_file() else None


# ---------- mejoras ----------
ESTADOS_MEJORA = ("nueva", "aceptada", "hecha", "descartada")


def registrar_mejora(descripcion, reporta="tutor", curso=None):
    descripcion = str(descripcion or "").strip()
    if not descripcion:
        raise ValueError("Falta la descripción.")
    if reporta not in ("leo", "tutor"):
        raise ValueError("'reporta' debe ser 'leo' o 'tutor'.")
    ya = _q("SELECT id FROM mejoras WHERE lower(descripcion)=lower(?) AND estado IN ('nueva','aceptada')", (descripcion,), one=True)
    if ya:
        return {"id": ya["id"], "repetida": True}
    ts = now_utc().isoformat()
    mid = _x("INSERT INTO mejoras (ts, reporta, curso, descripcion, estado, actualizado) VALUES (?, ?, ?, ?, 'nueva', ?)",
             (ts, reporta, curso or None, descripcion[:4000], ts))
    return {"id": mid, "repetida": False}


def listar_mejoras(estado=None, curso=None):
    sql, args = "SELECT * FROM mejoras WHERE 1=1", []
    if estado == "abiertas":
        sql += " AND estado IN ('nueva','aceptada')"
    elif estado:
        sql += " AND estado=?"
        args.append(estado)
    if curso:
        sql += " AND (curso=? OR curso IS NULL)"
        args.append(curso)
    return [dict(r) for r in _q(sql + " ORDER BY id DESC", args)]


def actualizar_mejora(mid, estado=None, nota=None):
    if estado is not None and estado not in ESTADOS_MEJORA:
        raise ValueError("estado debe ser nueva, aceptada, hecha o descartada.")
    if not _q("SELECT id FROM mejoras WHERE id=?", (mid,), one=True):
        raise ValueError("No existe esa mejora.")
    if estado is not None:
        _x("UPDATE mejoras SET estado=?, actualizado=? WHERE id=?", (estado, now_utc().isoformat(), mid))
    if nota is not None:
        _x("UPDATE mejoras SET nota=?, actualizado=? WHERE id=?", (str(nota)[:2000], now_utc().isoformat(), mid))


# ---------- exportar / importar ----------
def exportar():
    return {
        "arbol": arbol(),
        "cursos": [dict(r) for r in _q("SELECT id, datos, plan FROM cursos")],
        "hojas": [dict(r) for r in _q("SELECT curso, archivo, html FROM hojas")],
        "tarjetas": [dict(r) for r in _q("SELECT * FROM tarjetas")],
        "repasos": [dict(r) for r in _q("SELECT * FROM repasos")],
        "lecciones": [dict(r) for r in _q("SELECT * FROM lecciones")],
        "mejoras": [dict(r) for r in _q("SELECT * FROM mejoras")],
    }
