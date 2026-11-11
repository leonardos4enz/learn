"""Mi Tutor: app de estudio de Leo (web + MCP para Claude + bot de Telegram).

Variables de entorno (en EasyPanel → Entorno):
  MCP_TOKEN            token que Claude Code manda como "Authorization: Bearer ..." al MCP (/mcp). Sin él, el MCP está apagado.
  ADMIN_PASSWORD       (opcional) contraseña para entrar a la web sin link de Telegram.
  TELEGRAM_BOT_TOKEN   (opcional) token del bot de BotFather. Sin él, no hay bot.
  TELEGRAM_CHAT_ID     (opcional) tu chat id. Si falta, el bot te lo dice al escribirle /start.
  PUBLIC_URL           URL pública de la app, para los links (p. ej. https://learn-tutor.ppnoc4.easypanel.host).
  AVISO_HORA           hora del aviso diario (por defecto 08:00).   RECORDATORIO_HORA  segundo aviso (por defecto 19:00).
  TZ_NAME              zona horaria (por defecto America/Mexico_City).
  DATA_DIR             carpeta de la base SQLite y de las imágenes de las lecciones (en producción, el volumen /data).
  IMAGEN_MAX_KB        tamaño máximo de una imagen subida (por defecto 1500).
  DEV_NOAUTH=1         solo en local: entra a la web sin login.
"""
import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import store, tiempo

STATIC = Path(__file__).resolve().parent / "static"
MCP_TOKEN = os.environ.get("MCP_TOKEN", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://127.0.0.1:3000").rstrip("/")
AVISO_HORA = os.environ.get("AVISO_HORA", "08:00")
RECORDATORIO_HORA = os.environ.get("RECORDATORIO_HORA", "19:00")
DEV_NOAUTH = os.environ.get("DEV_NOAUTH") == "1"
COOKIE = "mt_sesion"


# ======================================================================== sesiones
def _firmar(payload: str) -> str:
    sig = hmac.new(store.secret().encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _verificar(token: str, tipo: str):
    try:
        p64, s64 = token.split(".")
        payload = base64.urlsafe_b64decode(p64 + "=" * (-len(p64) % 4)).decode()
        sig = base64.urlsafe_b64decode(s64 + "=" * (-len(s64) % 4))
        good = hmac.new(store.secret().encode(), payload.encode(), hashlib.sha256).digest()
        t, exp = payload.split("|")[:2]
        return hmac.compare_digest(sig, good) and t == tipo and int(exp) > time.time()
    except Exception:
        return False


def link_de_acceso(vista="hoy", horas=36):
    t = _firmar(f"link|{int(time.time() + horas * 3600)}|{os.urandom(4).hex()}")
    return f"{PUBLIC_URL}/entrar?t={t}&v={urllib.parse.quote(vista)}"


def _logueado(req: Request):
    return DEV_NOAUTH or _verificar(req.cookies.get(COOKIE, ""), "sesion")


def _con_sesion(resp: Response):
    resp.set_cookie(COOKIE, _firmar(f"sesion|{int(time.time() + 90 * 86400)}"), max_age=90 * 86400,
                    httponly=True, samesite="lax", secure=PUBLIC_URL.startswith("https"))
    return resp


def _privado(fn):
    async def wrap(req: Request):
        if not _logueado(req):
            if req.url.path.startswith("/api/"):
                return JSONResponse({"error": "no autorizado"}, status_code=401)
            return RedirectResponse("/login")
        return await fn(req)
    return wrap


# ======================================================================== web
async def entrar(req: Request):
    vista = req.query_params.get("v", "hoy")
    if not _verificar(req.query_params.get("t", ""), "link"):
        return HTMLResponse(_pagina_login("Ese link ya venció. Pide uno nuevo al bot con /link."), status_code=401)
    return _con_sesion(RedirectResponse(f"/app/#{urllib.parse.quote(vista)}", status_code=303))


def _pagina_login(msg=""):
    form = ("""<form method="post"><input type="password" name="pw" placeholder="Contraseña" autofocus>
            <button>Entrar</button></form>""" if ADMIN_PASSWORD else "")
    return (STATIC / "login.html").read_text(encoding="utf-8").replace("{{MSG}}", msg).replace("{{FORM}}", form)


async def login(req: Request):
    if req.method == "POST":
        form = await req.form()
        if ADMIN_PASSWORD and hmac.compare_digest(str(form.get("pw", "")), ADMIN_PASSWORD):
            return _con_sesion(RedirectResponse("/app/", status_code=303))
        return HTMLResponse(_pagina_login("Contraseña incorrecta."), status_code=401)
    if _logueado(req):
        return RedirectResponse("/app/")
    return HTMLResponse(_pagina_login())


async def salir(req: Request):
    r = RedirectResponse("/login", status_code=303)
    r.delete_cookie(COOKIE)
    return r


async def raiz(req: Request):
    return RedirectResponse("/app/")


async def salud(req: Request):
    return JSONResponse({"ok": True, "mcp": bool(MCP_TOKEN), "telegram": bool(TG_TOKEN and TG_CHAT)})


@_privado
async def app_index(req: Request):
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@_privado
async def api_cursos(req: Request):
    return JSONResponse({"arbol": store.arbol_con_resumen(), "racha": store.racha()})


@_privado
async def api_estado(req: Request):
    cid = req.query_params.get("curso", "")
    if not store.curso_existe(cid):
        return JSONResponse({"curso": None, "datos": None, "hojas": [], "pantalla": store.pantalla()})
    return JSONResponse({"curso": cid, "datos": store.leer_datos(cid), "hojas": store.listar_hojas(cid),
                         "pantalla": store.pantalla(), "tarjetas": store.stats_tarjetas(cid),
                         "lecciones": store.listar_lecciones(cid), "tiempo_hoy": _minutos_hoy()})


def _minutos_hoy():
    hoy = store.hoy_local()
    return round(sum(store.minutos_por_dia(hoy, hoy).get(hoy.isoformat(), {}).values()))


@_privado
async def api_panel(req: Request):
    p = store.panel(int(req.path_params["pid"]))
    if not p:
        return JSONResponse({"error": "No existe ese panel."}, status_code=404)
    return JSONResponse(p, headers={"Cache-Control": "private, max-age=3600"})  # un panel no cambia


@_privado
async def api_cola(req: Request):
    cid = req.query_params.get("curso", "todos")
    return JSONResponse({"cola": store.cola(cid)})


@_privado
async def api_repasar(req: Request):
    body = await req.json()
    try:
        return JSONResponse(store.repasar(int(req.path_params["tid"]), int(body.get("rating", 0))))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@_privado
async def api_tarjetas(req: Request):
    return JSONResponse({"tarjetas": store.listar_tarjetas(req.query_params.get("curso", ""))})


@_privado
async def api_lecciones(req: Request):
    cid = req.query_params.get("curso", "")
    return JSONResponse({"lecciones": store.listar_lecciones(cid)})


@_privado
async def api_leccion(req: Request):
    lec = store.leer_leccion(req.path_params["curso"], req.path_params["mision"])
    if not lec:
        return JSONResponse({"error": "No existe esa lección."}, status_code=404)
    return JSONResponse(lec)


@_privado
async def api_completar(req: Request):
    body = await req.json()
    try:
        return JSONResponse(store.completar_leccion(req.path_params["curso"], req.path_params["mision"], body.get("predicciones")))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@_privado
async def api_mejoras(req: Request):
    if req.method == "POST":
        body = await req.json()
        try:
            return JSONResponse(store.registrar_mejora(body.get("descripcion"), "leo", body.get("curso") or None))
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"mejoras": store.listar_mejoras()})


@_privado
async def api_mejora(req: Request):
    body = await req.json()
    try:
        store.actualizar_mejora(int(req.path_params["mid"]), body.get("estado"), body.get("nota"))
        return JSONResponse({"ok": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


def _err(fn):
    async def wrap(req: Request):
        try:
            return await fn(req)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    return wrap


@_privado
@_err
async def api_tiempo(req: Request):
    """GET: ratos y minutos por día entre desde y hasta (fechas locales). POST: agrega un rato a mano."""
    if req.method == "POST":
        b = await req.json()
        return JSONResponse(store.registrar_tiempo(b.get("curso") or None, b.get("tipo", "otro"), b.get("inicio"), b.get("fin"),
                                                   b.get("minutos"), b.get("mision"), b.get("nota"), "manual"))
    q = req.query_params
    return JSONResponse({"ratos": store.listar_tiempo(q.get("desde"), q.get("hasta")),
                         "dias": store.minutos_por_dia(q.get("desde"), q.get("hasta")),
                         "habil": store.tiempo_habil()})


@_privado
@_err
async def api_tiempo_uno(req: Request):
    tid = int(req.path_params["tid"])
    if req.method == "DELETE":
        store.borrar_tiempo(tid)
        return JSONResponse({"ok": True})
    b = await req.json()
    return JSONResponse(store.editar_tiempo(tid, b.get("curso"), b.get("mision"), b.get("tipo"), b.get("inicio"),
                                            b.get("fin"), b.get("minutos"), b.get("nota")))


@_privado
@_err
async def api_tiempo_ping(req: Request):
    b = await req.json()
    return JSONResponse(store.ping_tiempo(b.get("tipo"), b.get("curso") or None, b.get("mision")))


@_privado
@_err
async def api_tiempo_habil(req: Request):
    if req.method == "POST":
        b = await req.json()
        return JSONResponse(store.guardar_tiempo_habil(b.get("semana"), b.get("excepciones")))
    return JSONResponse(store.tiempo_habil())


@_privado
async def api_prediccion(req: Request):
    return JSONResponse(tiempo.prediccion())


@_privado
async def api_plan_png(req: Request):
    from . import imagen as img
    png = await asyncio.to_thread(img.plan_de_hoy_png, req.query_params.get("curso") or None)
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


@_privado
async def imagen(req: Request):
    p = store.ruta_imagen(req.path_params["curso"], req.path_params["archivo"])
    if not p:
        return Response("No existe esa imagen.", status_code=404)
    return FileResponse(p, media_type=store.MIME[p.suffix[1:]],
                        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})


@_privado
async def hoja(req: Request):
    html = store.leer_hoja(req.path_params["curso"], req.path_params["archivo"])
    if html is None:
        return Response("No existe esa hoja.", status_code=404)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


# ======================================================================== MCP (para Claude Code)
mcp = FastMCP(
    "mi-tutor",
    instructions=("Mi Tutor: la app de estudio de Leo. Usa estas herramientas siguiendo la skill 'tutor' del repo "
                  "AI Engineer Courses: leer el curso, sus mejoras abiertas y la lección de la misión al empezar; enseñar "
                  "desde la lección (explicar primero, practicar después); mostrar cosas en vivo; y al cerrar guardar datos, "
                  "hoja y tarjetas y registrar las mejoras que notaste. Registra el tiempo de cada misión: iniciar_sesion al empezar "
                  "y terminar_sesion al cerrar (vista Tiempo). Las lecciones se escriben con la skill 'ingestar'."),
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def ver_arbol() -> dict:
    """Árbol de estudios (áreas › series › cursos) con el resumen de cada curso (misiones hechas, siguiente misión, tarjetas
    y score por módulo), el score de cada rama y la racha de días seguidos estudiando."""
    return {"arbol": store.arbol_con_resumen(), "racha": store.racha()}


@mcp.tool()
def guardar_arbol(arbol: list) -> str:
    """Reemplaza el árbol de estudios completo. Lee primero con ver_arbol y manda el árbol entero modificado.
    Nodo rama: {"id", "nombre", "hijos": [...]}. Nodo curso: {"id", "nombre", "curso": true, "estado": "actual|en pausa|terminado",
    "nota"?, "carpeta_local"? (ruta en la PC de Leo con el material)}. Solo un curso debe tener estado "actual"."""
    store.guardar_arbol(arbol)
    return "Árbol guardado."


@mcp.tool()
def leer_curso(curso: str) -> dict:
    """Todo lo de un curso: su plan (Markdown), sus datos (misiones, banco, hojas, exámenes, proyecto, hilos),
    las hojas guardadas y las estadísticas de tarjetas. Léelo siempre al empezar una sesión."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    return {"plan": store.leer_plan(curso), "datos": store.leer_datos(curso), "hojas": store.listar_hojas(curso),
            "tarjetas": store.stats_tarjetas(curso)}


@mcp.tool()
def guardar_datos(curso: str, datos: dict) -> str:
    """Reemplaza los datos del curso (el JSON completo que devolvió leer_curso, ya modificado): misiones, siguiente,
    sesiones, hojas {archivo: {estado, falladas, total}}, banco, examenes, modulos, proyecto, hilos.
    Cada misión puede traer links: [{"tipo": "video"|"lectura"|"lab"|"quiz", "titulo", "url" (https), "min"?}]: el
    material oficial (p. ej. LangChain Academy). La app los muestra como botones en Hoy, en el camino y en la lección."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    store.guardar_datos(curso, datos)
    return "Datos guardados."


@mcp.tool()
def guardar_plan(curso: str, plan: str) -> str:
    """Reemplaza el plan del curso (Markdown): meta, material, actividades, hojas y examen, entorno y mapa de misiones."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    store.guardar_plan(curso, plan)
    return "Plan guardado."


@mcp.tool()
def guardar_hoja(curso: str, archivo: str, html: str) -> str:
    """Guarda una hoja imprimible (HTML completo, con la estructura de la plantilla de la skill). archivo: '01-mision.html'.
    Registra también la hoja en datos.hojas con guardar_datos."""
    store.guardar_hoja(curso, archivo, html)
    return f"Hoja guardada. Leo la ve en la app → Hojas."


@mcp.tool()
def leer_hoja(curso: str, archivo: str) -> str:
    """Devuelve el HTML de una hoja guardada (para usarla de plantilla o revisar sus respuestas)."""
    h = store.leer_hoja(curso, archivo)
    if h is None:
        raise ValueError("No existe esa hoja.")
    return h


@mcp.tool()
def mostrar(curso: str, titulo: str, tipo: str, contenido: str = "", notas: str | None = None,
            resaltar: list[int] | None = None, respuesta: str | None = None, datos: dict | None = None,
            mision: str | None = None) -> str:
    """Muestra algo en la Pantalla en vivo de Leo (lo ve en ~2 s). La pantalla es SOLO para ver: Leo contesta en el chat.
    Manda UN panel y espera a que Leo responda antes del siguiente (si mandas dos seguidos, solo ve el último).
    mision: el id de la misión que están trabajando (p. ej. "1.B"). El panel queda guardado en esa lección y Leo lo
      vuelve a ver en el modo "Por lección". Sin mision (una duda suelta), el panel va al modo "Libre".
    tipo:
      'mermaid'   diagrama; marca el nodo clave con 'class X clave'. Opcional datos={"detalles": {"X": "qué hace X"}}:
                  Leo toca un nodo y ve su explicación al lado.
      'codigo'    código COMPLETO (nunca recortado); resaltar=[n° de línea].
      'markdown'  explicación, tabla o ejemplo.
      'predice'   pregunta; 'respuesta' queda oculta hasta que Leo da clic. Leo contesta en el chat ANTES de revelarla.
      'recorrido' un grafo paso a paso: contenido = diagrama mermaid (flowchart);
                  datos={"pasos": [{"nodo": "A", "estado": {...}, "nota": "qué pasa aquí"}, ...]}. Leo avanza con ← →;
                  se ilumina el nodo activo y se ve el state en ese momento. Ideal para seguir un invoke o un loop.
      'estado'    cómo cambia el state con un update: datos={"antes": {...}, "update": {...}, "despues": {...}};
                  se resaltan las keys que cambiaron. Ideal para reducers.
      'comparar'  dos versiones de código lado a lado: datos={"izquierda": {"titulo", "codigo"}, "derecha": {...}};
                  se resaltan las líneas distintas. Ideal para "antes / después" o "con y sin reducer".
      'html'      solo si nada de lo anterior sirve.
    notas: 2–5 líneas que dicen qué mirar; van al lado del contenido (ponlas siempre)."""
    store.mostrar(curso, titulo, tipo, contenido, notas, resaltar, respuesta, datos, mision)
    donde = f"la lección {mision}" if mision else "Libre"
    return f"En pantalla ({donde}). Espera a que Leo conteste antes de mandar el siguiente panel."


@mcp.tool()
def clasificar_panel(curso: str, ids: list[int], mision: str | None = None) -> dict:
    """Mueve paneles ya mostrados a la lección de una misión (o a Libre si mision es null). Sirve para ordenar paneles
    que quedaron en Libre o en la lección equivocada. Los ids salen de ver_pantalla."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    return store.clasificar_paneles(curso, ids, mision)


@mcp.tool()
def ver_pantalla(curso: str, mision: str | None = None) -> dict:
    """Lo que ya se le mostró a Leo en la pantalla en vivo: título, tipo y fecha de cada panel. Con mision, solo los de
    esa lección; con mision="libre", los que no son de ninguna lección; sin mision, todos los del curso.
    Úsalo para retomar una lección sin repetir lo que ya vio."""
    items = [p for p in store.pantalla(curso) if p.get("curso") == curso]
    if mision == "libre":
        items = [p for p in items if not p.get("mision")]
    elif mision:
        items = [p for p in items if p.get("mision") == str(mision)]
    return {"paneles": items}


@mcp.tool()
def crear_tarjetas(curso: str, tarjetas: list[dict]) -> dict:
    """Crea tarjetas de repaso espaciado (FSRS). Cada una: {"frente", "reverso", "modulo"?, "mision"?}.
    Reglas: una idea por tarjeta; el frente pregunta algo que hay que ENTENDER (por qué, qué pasa si, cuándo usar),
    no solo definiciones; el reverso es corto (1–3 líneas) y dice el porqué. Las repetidas (mismo frente) se ignoran."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    return store.crear_tarjetas(curso, tarjetas)


@mcp.tool()
def ver_tarjetas(curso: str) -> dict:
    """Lista las tarjetas del curso con su estabilidad (días), cuántas veces se fallaron y si están suspendidas,
    más las estadísticas (para hoy, dominio por módulo). Úsalo para elegir preguntas de calentamiento entre las más falladas."""
    return {"stats": store.stats_tarjetas(curso), "tarjetas": store.listar_tarjetas(curso)}


@mcp.tool()
def editar_tarjeta(id: int, frente: str | None = None, reverso: str | None = None, suspendida: bool | None = None) -> str:
    """Corrige el texto de una tarjeta o la suspende (deja de aparecer en el repaso)."""
    store.editar_tarjeta(id, frente, reverso, suspendida)
    return "Tarjeta actualizada."


@mcp.tool()
def guardar_leccion(curso: str, mision_id: str, titulo: str, pasos: list[dict], fuentes: list[str] | None = None,
                    tarjetas: list[dict] | None = None) -> dict:
    """Guarda (o reemplaza) la lección de una misión. Leo la ve en la app → Lecciones, paso a paso.
    Si Leo ya la completó, su avance se conserva.
    pasos: lista en orden; cada paso es UN concepto: {"tipo", "titulo"?, "contenido", "notas"?, "resaltar"?, "respuesta"?}.
      tipo 'markdown' (explicación), 'codigo' (código COMPLETO, nunca recortado; resaltar=[líneas clave]),
      'mermaid' (diagrama; 'class nodo clave'), 'predice' (pregunta; 'respuesta' obligatoria, Leo debe contestar antes de avanzar;
      debe poder contestarse con lo que está en pantalla: si es una variación, el código completo va en 'contenido' en un
      bloque ```python; si es sobre un ejemplo ya mostrado, "ref": número del paso de código),
      'imagen' ({"url": la de subir_imagen, "alt", "notas"?}).
      notas: 2–5 líneas de qué mirar, van al lado del código o diagrama.
    Orden obligatorio: explicación con un ejemplo resuelto y su código completo PRIMERO; después los pasos predice
    (Kirschner, Sweller y Clark 2006). Nada decorativo.
    fuentes: de dónde sale (p. ej. 'module-1/router.ipynb'). tarjetas: 4–8 sugeridas {"frente", "reverso"}; entran al
    mazo FSRS cuando Leo completa la lección."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    r = store.guardar_leccion(curso, mision_id, titulo, pasos, fuentes, tarjetas)
    return {**r, "mensaje": "Lección guardada. Leo la ve en la app → Lecciones."}


@mcp.tool()
def leer_leccion(curso: str, mision_id: str) -> dict:
    """La lección de una misión: pasos, fuentes, tarjetas sugeridas, si Leo ya la completó y sus predicciones
    (lo que escribió en cada paso 'predice' y si dijo que acertó). Léela antes de enseñar esa misión."""
    lec = store.leer_leccion(curso, mision_id)
    if not lec:
        raise ValueError(f"La misión '{mision_id}' de '{curso}' todavía no tiene lección (usa la skill ingestar).")
    return lec


@mcp.tool()
def listar_lecciones(curso: str) -> dict:
    """Lecciones guardadas del curso (sin los pasos): misión, título, número de pasos, si Leo ya la leyó (completada)
    y si el tutor la verificó (verificada / verificacion)."""
    return {"lecciones": store.listar_lecciones(curso)}


@mcp.tool()
def verificar_leccion(curso: str, mision_id: str, resultado: str, nota: str = "") -> dict:
    """Solo el tutor marca si Leo SABE una lección; leerla en la app no basta. Úsalo al cerrar la sesión de esa misión.
    resultado: 'dominada' si Leo contestó bien SIN ayuda (al menos 2 de 3 preguntas de práctica: predecir, diseñar,
    revisar o romper) o 'repasar' si necesitó pistas o falló lo central. nota: 1–2 líneas con el porqué (qué acertó o
    qué falló). En la app la lección pasa de 'leída' a 'verificada' (verde) o 'repasar' (ámbar), y el score solo
    cuenta las verificadas."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    return store.verificar_leccion(curso, mision_id, resultado, nota)


@mcp.tool()
def subir_imagen(curso: str, nombre: str, base64_data: str) -> dict:
    """Sube una imagen (PNG, JPG, GIF o WEBP; máx. ~1.5 MB) para usarla en un paso 'imagen' de una lección.
    base64_data: el archivo en base64 (sin el prefijo 'data:'). Devuelve la URL privada (/imagenes/<curso>/<archivo>).
    Mismo nombre = reemplaza. Para archivos locales es más barato correr tools/subir_imagen.py del repo learn."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    try:
        data = base64.b64decode(base64_data.split(",", 1)[-1], validate=True)
    except Exception:
        raise ValueError("base64_data no es base64 válido.")
    return store.guardar_imagen(curso, nombre, data)


@mcp.tool()
def registrar_mejora(descripcion: str, reporta: str = "tutor", curso: str | None = None) -> dict:
    """Registra un error o una propuesta de mejora del tutor o de la app (vista Mejoras).
    reporta: 'tutor' (lo notaste tú) o 'leo' (lo dijo Leo). Una mejora por llamada, concreta y accionable.
    Si ya existe una abierta con el mismo texto, no se duplica."""
    return store.registrar_mejora(descripcion, reporta, curso)


@mcp.tool()
def ver_mejoras(estado: str | None = "abiertas", curso: str | None = None) -> dict:
    """Lista las mejoras. estado: 'abiertas' (nuevas y aceptadas, por defecto), 'nueva', 'aceptada', 'hecha', 'descartada'
    o null para todas. Revísalas al empezar cada sesión y aplica las aceptadas."""
    return {"mejoras": store.listar_mejoras(estado, curso)}


@mcp.tool()
def actualizar_mejora(id: int, estado: str | None = None, nota: str | None = None) -> str:
    """Cambia el estado de una mejora (nueva / aceptada / hecha / descartada) o le agrega una nota."""
    store.actualizar_mejora(id, estado, nota)
    return "Mejora actualizada."


@mcp.tool()
def iniciar_sesion(curso: str, mision: str | None = None, tipo: str = "tutor", nota: str | None = None) -> dict:
    """Marca el INICIO de un rato de estudio (vista Tiempo). Llámalo al empezar cada misión con Leo, antes del
    calentamiento: iniciar_sesion(curso, mision="2.C"). Devuelve el 'id' que necesitas para terminar_sesion.
    tipo: 'tutor' (misión con el tutor, por defecto), 'leccion', 'tarjetas', 'hoja' u 'otro'.
    Si ya hay uno abierto igual (mismo curso, misión y tipo), devuelve ese en vez de duplicarlo.
    Las lecciones y tarjetas de la app se registran solas; no las abras tú."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    return store.iniciar_tiempo(curso, mision, tipo, nota, "tutor")


@mcp.tool()
def terminar_sesion(id: int, nota: str | None = None, fin: str | None = None) -> dict:
    """Marca el FIN de un rato que abriste con iniciar_sesion (al cerrar la misión, después de guardar datos y tarjetas).
    fin: opcional, 'YYYY-MM-DD HH:MM' en hora local de Leo (por defecto, ahora). Si Leo se fue a mitad de la sesión y
    volvió mucho después, pon el fin real o divide en dos con registrar_sesion. Un rato abierto más de 4 h queda
    'sin cerrar' y no cuenta hasta corregirlo."""
    return store.terminar_tiempo(id, nota, fin)


@mcp.tool()
def registrar_sesion(curso: str, tipo: str, inicio: str, fin: str | None = None, minutos: float | None = None,
                     mision: str | None = None, nota: str | None = None) -> dict:
    """Registra un rato de estudio ya pasado, con inicio y fin o con inicio y minutos. Úsalo para lo que no se mide solo:
    la hoja en papel ("me tomó 20 min"), una sesión que se te olvidó abrir o algo que Leo estudió fuera de la app.
    inicio/fin: 'YYYY-MM-DD HH:MM' en hora local de Leo (America/Mexico_City) o ISO 8601 con zona.
    tipo: 'tutor', 'leccion', 'tarjetas', 'hoja' u 'otro'. mision: el id de la misión, si aplica."""
    if not store.curso_existe(curso):
        raise ValueError(f"No hay un curso '{curso}' en el árbol.")
    return store.registrar_tiempo(curso, tipo, inicio, fin, minutos, mision, nota, "tutor")


@mcp.tool()
def editar_sesion(id: int, curso: str | None = None, mision: str | None = None, tipo: str | None = None,
                  inicio: str | None = None, fin: str | None = None, minutos: float | None = None,
                  nota: str | None = None, borrar: bool = False) -> dict:
    """Corrige o borra un rato de estudio (los ids salen de ver_tiempo). Solo cambia los campos que pases.
    minutos: recalcula el fin desde el inicio. borrar=true lo elimina."""
    if borrar:
        store.borrar_tiempo(id)
        return {"borrado": id}
    return store.editar_tiempo(id, curso, mision, tipo, inicio, fin, minutos, nota)


@mcp.tool()
def ver_tiempo(curso: str | None = None, desde: str | None = None, hasta: str | None = None) -> dict:
    """Cuánto estudió Leo y cuándo termina. desde/hasta: 'YYYY-MM-DD' (por defecto, los últimos 30 días).
    Devuelve: los ratos (con id, tipo, misión, minutos y estado abierta/cerrada/sin_cerrar), minutos por tipo y por
    curso, esta semana contra su tiempo hábil, el tiempo hábil configurado y la predicción de fin por curso y total
    (ritmo real con rango del 80 % y la fecha según su tiempo hábil). Úsalo al empezar para ver si quedó algo
    'sin cerrar' y al cerrar para decirle a Leo cuánto le tomó la misión."""
    r = tiempo.resumen_tiempo(desde, hasta, curso)
    p = tiempo.prediccion()
    if curso:
        p["cursos"] = [c for c in p["cursos"] if c["id"] == curso]
    return {**r, "habil": store.tiempo_habil(), "prediccion": p}


@mcp.tool()
def guardar_tiempo_habil(semana: dict | None = None, excepciones: list[dict] | None = None) -> dict:
    """Define el tiempo hábil de estudio de Leo (normalmente lo edita él en la app → Tiempo).
    semana: {"0": [["19:00", "21:00"]], ..., "6": []} con 0 = lunes; varias franjas por día.
    excepciones: lista COMPLETA [{"fecha": "YYYY-MM-DD", "minutos": 0 (libre) o los minutos de ese día, "nota"?}]."""
    return store.guardar_tiempo_habil(semana, excepciones)


@mcp.tool()
def dar_link(vista: str = "hoy") -> str:
    """Link de acceso a la app (válido 36 h) para dárselo a Leo. vista: hoy, lecciones, tarjetas, pantalla, hojas, repaso,
    proyecto, mejoras, estudios (grafo de cursos con su progreso y el detalle por módulo), tiempo."""
    if vista == "progreso":  # la vista Progreso se juntó con Mis estudios
        vista = "estudios"
    return link_de_acceso(vista)


@mcp.tool()
async def avisar_por_telegram(texto: str) -> str:
    """Manda un mensaje a Leo por Telegram (p. ej. el resumen al cerrar la sesión). Texto plano, corto."""
    if not (TG_TOKEN and TG_CHAT):
        return "El bot de Telegram no está configurado."
    await tg_send(TG_CHAT, texto, html=False)
    return "Enviado."


def _mcp_auth(app):
    async def wrapped(scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if not MCP_TOKEN or not hmac.compare_digest(auth, f"Bearer {MCP_TOKEN}"):
                await JSONResponse({"error": "no autorizado"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)
    return wrapped


# ======================================================================== Telegram
def _tg_call(method, data):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/{method}",
                                 data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read())


async def tg_send(chat, text, html=True):
    data = {"chat_id": chat, "text": text, "disable_web_page_preview": True}
    if html:
        data["parse_mode"] = "HTML"
    try:
        await asyncio.to_thread(_tg_call, "sendMessage", data)
    except Exception as e:
        print("telegram sendMessage:", e)


def _tg_foto(chat, png, caption):
    """sendPhoto con multipart/form-data (Telegram no acepta SVG: la imagen va en PNG)."""
    limite = "----mitutor" + os.urandom(8).hex()
    partes = []
    for k, v in (("chat_id", str(chat)), ("caption", caption[:1024]), ("parse_mode", "HTML")):
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="photo"; filename="plan-de-hoy.png"\r\n'
                  f"Content-Type: image/png\r\n\r\n".encode() + png + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", data=b"".join(partes),
                                 headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read())


async def tg_plan(chat, saludo=True):
    """El plan de hoy como imagen (plan, racha, tiempo y predicción) con el resumen de texto como pie. Si la imagen
    falla por algo, manda solo el texto."""
    texto, total = resumen_del_dia(saludo)
    try:
        from . import imagen as img
        png = await asyncio.to_thread(img.plan_de_hoy_png)
        await asyncio.to_thread(_tg_foto, chat, png, texto)
    except Exception as e:
        print("telegram sendPhoto:", e)
        await tg_send(chat, texto)
    return total


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def resumen_del_dia(saludo=True):
    lineas, total = [], 0
    actual = None
    for ruta, n in store.iter_cursos():
        s = store.stats_tarjetas(n["id"])
        if s["para_hoy"]:
            lineas.append(f"• {_esc(n['nombre'])}: <b>{s['para_hoy']}</b> tarjetas")
            total += s["para_hoy"]
        if n.get("estado") == "actual":
            actual = n
    partes = ["Buenos días, Leo." if saludo else "Leo:"]
    partes.append(f"Hoy tienes <b>{total}</b> tarjetas para repasar (~{max(1, round(total * 0.4))} min):" if total
                  else "Hoy no tienes tarjetas pendientes.")
    partes += lineas
    if actual:
        d = store.leer_datos(actual["id"]) or {}
        pend = [a for a, m in (d.get("hojas") or {}).items() if m.get("estado") != "hecha"]
        if pend:
            partes.append(f"Hoja pendiente: {_esc(pend[-1])}")
        sig = next((m for m in d.get("misiones", []) if m.get("id") == d.get("siguiente")), None)
        if sig:
            partes.append(f"Siguiente misión de {_esc(actual['nombre'])}: {_esc(sig['id'])} · {_esc(sig['titulo'])}")
    vista = "tarjetas" if total else "hoy"
    partes.append(f'\n<a href="{link_de_acceso(vista)}">Abrir Mi Tutor</a>')
    return "\n".join(partes), total


async def telegram_loop():
    offset = store.kv_get("tg_offset", 0)
    while True:
        try:
            res = await asyncio.to_thread(_tg_call, "getUpdates", {"offset": offset, "timeout": 50, "allowed_updates": ["message"]})
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                store.kv_set("tg_offset", offset)
                msg = u.get("message") or {}
                chat = str((msg.get("chat") or {}).get("id", ""))
                text = (msg.get("text") or "").strip().split("@")[0]
                if not chat:
                    continue
                if not TG_CHAT:
                    await tg_send(chat, f"Hola. Tu chat id es <code>{chat}</code>.\nPonlo en EasyPanel como TELEGRAM_CHAT_ID y vuelve a implementar.")
                    continue
                if chat != TG_CHAT:
                    continue  # lista blanca: solo Leo
                if text in ("/start", "/hoy"):
                    await tg_plan(chat, saludo=False)
                elif text == "/tarjetas":
                    await tg_send(chat, f'<a href="{link_de_acceso("tarjetas")}">Repasar tarjetas</a>')
                elif text == "/link":
                    await tg_send(chat, f'<a href="{link_de_acceso("hoy")}">Abrir Mi Tutor</a> (válido 36 h)')
                elif text == "/tiempo":
                    await tg_send(chat, f'<a href="{link_de_acceso("tiempo")}">Tu calendario y la predicción</a>')
                else:
                    await tg_send(chat, "Comandos: /hoy (plan de hoy con tu gráfica), /tarjetas (repasar), /tiempo (calendario), /link (abrir la app).")
        except Exception as e:
            print("telegram getUpdates:", e)
            await asyncio.sleep(10)


def _ya_paso(hhmm):
    h, m = map(int, hhmm.split(":"))
    ahora = datetime.now(store.TZ)
    return (ahora.hour, ahora.minute) >= (h, m)


async def avisos_loop():
    while True:
        try:
            hoy = store.hoy_local().isoformat()
            if _ya_paso(AVISO_HORA) and store.kv_get("aviso_manana") != hoy:
                store.kv_set("aviso_manana", hoy)
                await tg_plan(TG_CHAT)
            if _ya_paso(RECORDATORIO_HORA) and store.kv_get("aviso_tarde") != hoy:
                store.kv_set("aviso_tarde", hoy)
                texto, total = resumen_del_dia(saludo=False)
                if total and store.repasos_hoy_total() == 0:
                    await tg_send(TG_CHAT, "Todavía no repasas hoy. Son unos minutos y es lo que más fija lo aprendido.\n" + texto)
        except Exception as e:
            print("avisos:", e)
        await asyncio.sleep(60)


# ======================================================================== app
@contextlib.asynccontextmanager
async def lifespan(app):
    tareas = []
    if TG_TOKEN:
        tareas.append(asyncio.create_task(telegram_loop()))
        if TG_CHAT:
            # No mandar el aviso de hoy al arrancar si ya pasó la hora: solo desde el siguiente.
            hoy = store.hoy_local().isoformat()
            if _ya_paso(AVISO_HORA) and store.kv_get("aviso_manana") is None:
                store.kv_set("aviso_manana", hoy)
            tareas.append(asyncio.create_task(avisos_loop()))
    async with mcp.session_manager.run():
        yield
    for t in tareas:
        t.cancel()


mcp_app = mcp.streamable_http_app()

routes = [
    Route("/", raiz),
    Route("/salud", salud),
    Route("/entrar", entrar),
    Route("/login", login, methods=["GET", "POST"]),
    Route("/salir", salir),
    Route("/app/", app_index),
    Route("/app", raiz),
    Route("/api/cursos", api_cursos),
    Route("/api/estado", api_estado),
    Route("/api/cola", api_cola),
    Route("/api/tarjetas", api_tarjetas),
    Route("/api/tarjetas/{tid:int}/repaso", api_repasar, methods=["POST"]),
    Route("/api/pantalla/{pid:int}", api_panel),
    Route("/api/lecciones", api_lecciones),
    Route("/api/lecciones/{curso}/{mision}", api_leccion),
    Route("/api/lecciones/{curso}/{mision}/completar", api_completar, methods=["POST"]),
    Route("/api/mejoras", api_mejoras, methods=["GET", "POST"]),
    Route("/api/mejoras/{mid:int}", api_mejora, methods=["POST"]),
    Route("/api/tiempo", api_tiempo, methods=["GET", "POST"]),
    Route("/api/tiempo/ping", api_tiempo_ping, methods=["POST"]),
    Route("/api/tiempo/habil", api_tiempo_habil, methods=["GET", "POST"]),
    Route("/api/tiempo/prediccion", api_prediccion),
    Route("/api/tiempo/plan.png", api_plan_png),
    Route("/api/tiempo/{tid:int}", api_tiempo_uno, methods=["POST", "DELETE"]),
    Route("/imagenes/{curso}/{archivo}", imagen),
    Route("/hojas/{curso}/{archivo}", hoja),
    Mount("/static", StaticFiles(directory=STATIC)),
    Mount("/", app=mcp_app),
]

app = _mcp_auth(Starlette(routes=routes, lifespan=lifespan))


def run():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "3000")), proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    run()
