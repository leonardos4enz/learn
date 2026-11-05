"""Mi Tutor: app de estudio de Leo (web + MCP para Claude + bot de Telegram).

Variables de entorno (en EasyPanel → Entorno):
  MCP_TOKEN            token que Claude Code manda como "Authorization: Bearer ..." al MCP (/mcp). Sin él, el MCP está apagado.
  ADMIN_PASSWORD       (opcional) contraseña para entrar a la web sin link de Telegram.
  TELEGRAM_BOT_TOKEN   (opcional) token del bot de BotFather. Sin él, no hay bot.
  TELEGRAM_CHAT_ID     (opcional) tu chat id. Si falta, el bot te lo dice al escribirle /start.
  PUBLIC_URL           URL pública de la app, para los links (p. ej. https://learn-tutor.ppnoc4.easypanel.host).
  AVISO_HORA           hora del aviso diario (por defecto 08:00).   RECORDATORIO_HORA  segundo aviso (por defecto 19:00).
  TZ_NAME              zona horaria (por defecto America/Mexico_City).
  DATA_DIR             carpeta de la base SQLite (en producción, el volumen /data).
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

from . import store

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
    return JSONResponse({"arbol": store.arbol_con_resumen()})


@_privado
async def api_estado(req: Request):
    cid = req.query_params.get("curso", "")
    if not store.curso_existe(cid):
        return JSONResponse({"curso": None, "datos": None, "hojas": [], "pantalla": store.pantalla()})
    return JSONResponse({"curso": cid, "datos": store.leer_datos(cid), "hojas": store.listar_hojas(cid),
                         "pantalla": store.pantalla(), "tarjetas": store.stats_tarjetas(cid)})


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
async def hoja(req: Request):
    html = store.leer_hoja(req.path_params["curso"], req.path_params["archivo"])
    if html is None:
        return Response("No existe esa hoja.", status_code=404)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


# ======================================================================== MCP (para Claude Code)
mcp = FastMCP(
    "mi-tutor",
    instructions=("Mi Tutor: la app de estudio de Leo. Usa estas herramientas siguiendo la skill 'tutor' del repo "
                  "AI Engineer Courses: leer el curso al empezar, mostrar cosas en vivo durante la sesión, y al cerrar "
                  "guardar datos, hoja y tarjetas."),
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def ver_arbol() -> dict:
    """Árbol de estudios (áreas › series › cursos) con el resumen de cada curso: misiones hechas, siguiente misión y tarjetas."""
    return {"arbol": store.arbol_con_resumen()}


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
    sesiones, hojas {archivo: {estado, falladas, total}}, banco, examenes, modulos, proyecto, hilos."""
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
def mostrar(curso: str, titulo: str, tipo: str, contenido: str, notas: str | None = None,
            resaltar: list[int] | None = None, respuesta: str | None = None) -> str:
    """Muestra algo en la Pantalla en vivo de Leo (lo ve en ~2 s).
    tipo: 'mermaid' (diagrama; marca el nodo clave con 'class nodo clave'), 'codigo' (usa resaltar=[n° de línea]),
    'markdown', 'html' o 'predice' (pregunta; 'respuesta' queda oculta hasta que Leo da clic).
    notas: 2–5 líneas que dicen qué mirar; van al lado del contenido (ponlas siempre en diagramas y código)."""
    store.mostrar(curso, titulo, tipo, contenido, notas, resaltar, respuesta)
    return "En pantalla."


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
def dar_link(vista: str = "hoy") -> str:
    """Link de acceso a la app (válido 36 h) para dárselo a Leo. vista: hoy, tarjetas, pantalla, hojas, repaso, progreso, estudios."""
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
                    msg_txt, _ = resumen_del_dia(saludo=False)
                    await tg_send(chat, msg_txt)
                elif text == "/tarjetas":
                    await tg_send(chat, f'<a href="{link_de_acceso("tarjetas")}">Repasar tarjetas</a>')
                elif text == "/link":
                    await tg_send(chat, f'<a href="{link_de_acceso("hoy")}">Abrir Mi Tutor</a> (válido 36 h)')
                else:
                    await tg_send(chat, "Comandos: /hoy (resumen), /tarjetas (repasar), /link (abrir la app).")
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
                texto, _ = resumen_del_dia()
                await tg_send(TG_CHAT, texto)
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
    Route("/hojas/{curso}/{archivo}", hoja),
    Mount("/static", StaticFiles(directory=STATIC)),
    Mount("/", app=mcp_app),
]

app = _mcp_auth(Starlette(routes=routes, lifespan=lifespan))


def run():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "3000")), proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    run()
