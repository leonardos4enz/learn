"""Ayudante de la skill `ingestar`: habla con el MCP de Mi Tutor sin pasar archivos grandes por el chat.

Uso (desde cualquier carpeta, con el Python del .venv de learn):
  python tools/tutor_mcp.py imagenes <notebook.ipynb> <carpeta-salida>
      Extrae las imágenes que el notebook trae incrustadas (salidas PNG/JPEG y adjuntos de celdas Markdown).
  python tools/tutor_mcp.py subir <curso> <archivo-imagen> [nombre]
      Sube una imagen local y muestra su URL (/imagenes/<curso>/<archivo>).
  python tools/tutor_mcp.py llamar <herramienta> <args.json>
      Llama a cualquier herramienta del MCP con los argumentos de un archivo JSON (p. ej. guardar_leccion).
  python tools/tutor_mcp.py exportar <carpeta> [--cursos id1,id2] [--pisar]
      Exporta el CONTENIDO (árbol, rutas, planes, misiones con links, lecciones e imágenes) sin nada personal:
      ni progreso, ni tarjetas repasadas, ni sesiones, hojas, banco o tiempo. Las rutas de la PC se vuelven genéricas.
      Los plan.md y lecciones que ya existan en la carpeta no se pisan (están curados a mano) salvo con --pisar.
  python tools/tutor_mcp.py importar <carpeta> [--forzar]
      Carga ese contenido en una app Mi Tutor (la de MI_TUTOR_URL). No toca cursos que ya tengan datos (tu progreso),
      salvo con --forzar. Las lecciones se guardan siempre (guardarlas de nuevo conserva si ya las completaste).

URL: variable MI_TUTOR_URL; si no está, la de "mi-tutor" en el .mcp.json de la raíz del repo.
Token: variable MI_TUTOR_TOKEN (en Windows se lee también de las variables de usuario). Nunca se imprime.
"""
import asyncio
import base64
import json
import os
import re
import sys
from pathlib import Path


def _token():
    t = os.environ.get("MI_TUTOR_TOKEN")
    if not t and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                t = winreg.QueryValueEx(k, "MI_TUTOR_TOKEN")[0]
        except OSError:
            t = None
    if not t:
        raise SystemExit("Falta la variable MI_TUTOR_TOKEN.")
    return t


def _url():
    u = os.environ.get("MI_TUTOR_URL")
    if not u:
        cfg = Path(__file__).resolve().parent.parent / ".mcp.json"
        try:
            u = json.loads(cfg.read_text(encoding="utf-8"))["mcpServers"]["mi-tutor"]["url"]
        except (OSError, KeyError, ValueError):
            raise SystemExit("Falta la URL de tu app: define MI_TUTOR_URL o crea .mcp.json (ver .mcp.example.json).")
    u = u.rstrip("/")
    return u if u.endswith("/mcp") else u + "/mcp"


async def _llamar(tool, args):
    return (await _llamar_varios([(tool, args)]))[0]


async def _llamar_varios(llamadas):
    """Varias llamadas en una sola conexión. Devuelve el texto de cada una; si una falla, se detiene con su error."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    out, error = [], None
    async with streamablehttp_client(_url(), headers={"Authorization": f"Bearer {_token()}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for tool, args in llamadas:
                res = await s.call_tool(tool, args)
                txt = " ".join(getattr(c, "text", "") for c in res.content)
                if res.isError:
                    error = f"{tool}: {txt}"
                    break
                out.append(txt)
    if error:  # fuera del task group, para que el error salga limpio
        raise SystemExit(error)
    return out


def _json(txt):
    d = json.loads(txt)
    return d["result"] if isinstance(d, dict) and set(d) == {"result"} else d


def imagenes(nb, salida):
    nb, salida = Path(nb), Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    data = json.loads(nb.read_text(encoding="utf-8"))
    n = 0
    for i, cell in enumerate(data.get("cells", [])):
        blobs = []
        for out in cell.get("outputs", []) or []:
            for mime, ext in (("image/png", "png"), ("image/jpeg", "jpg")):
                if mime in out.get("data", {}):
                    blobs.append((ext, out["data"][mime]))
        for nombre, att in (cell.get("attachments") or {}).items():
            for mime, b in att.items():
                if mime.startswith("image/") and mime != "image/svg+xml":
                    blobs.append((mime.split("/")[1].replace("jpeg", "jpg"), b))
        for j, (ext, b) in enumerate(blobs):
            b = "".join(b) if isinstance(b, list) else b
            p = salida / f"{nb.stem}-celda{i:02d}-{j}.{ext}"
            p.write_bytes(base64.b64decode(b))
            n += 1
            print(f"{p}  ({p.stat().st_size // 1024} KB)")
    print(f"{n} imágenes extraídas.")


# ---------- exportar / importar contenido ----------
def _cursos_de(nodos):
    for n in nodos:
        if n.get("curso"):
            yield n
        yield from _cursos_de(n.get("hijos", []))


def _podar(nodos, ids):
    """El árbol solo con los cursos pedidos (y las ramas que los contienen), sin datos de la PC ni del avance."""
    out = []
    for n in nodos:
        if n.get("curso"):
            if n["id"] in ids:
                out.append({"id": n["id"], "nombre": n["nombre"], "curso": True, "estado": "en pausa"})
        else:
            hijos = _podar(n.get("hijos", []), ids)
            if hijos:
                out.append({"id": n["id"], "nombre": n["nombre"], "hijos": hijos})
    return out


def _datos_limpios(d):
    """Misiones (con sus links) y módulos; todo lo demás es de la persona que estudia y se va en blanco."""
    ms = [{k: m.get(k) for k in ("id", "modulo", "titulo", "material", "links") if m.get(k) not in (None, "", [])}
          | {"estado": "pendiente", "fecha": None, "nota": ""} for m in d.get("misiones", [])]
    hilos = [{**h, "etapa": 0} for h in d.get("hilos", [])]
    return {"nombre": d.get("nombre", ""), "siguiente": ms[0]["id"] if ms else None, "modulos": d.get("modulos", []),
            "misiones": ms, "proyecto": None, "hilos": hilos, "sesiones": [], "hojas": {}, "banco": [], "examenes": []}


_RUTA_PC = re.compile(r"""[A-Za-z]:[\\/]+Users[\\/]+[^\\/"']+[\\/]+Desktop[\\/]+AI Engineer Courses""")


def _generico(txt):
    """Quita la ruta de la PC de quien exporta (C:/Users/<nombre>/Desktop/AI Engineer Courses)."""
    return _RUTA_PC.sub("C:/ruta/a/tus/cursos", txt)


def exportar(carpeta, solo=None, pisar=False):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    arbol = _json(asyncio.run(_llamar("ver_arbol", {})))
    ids = [c["id"] for c in _cursos_de(arbol["arbol"]) if not solo or c["id"] in solo]
    (carpeta / "arbol.json").write_text(json.dumps(_podar(arbol["arbol"], set(ids)), ensure_ascii=False, indent=1), encoding="utf-8")
    rutas = [{"id": r["id"], "nombre": r["nombre"], "descripcion": r.get("descripcion", ""),
              "cursos": [c for c in r["cursos"] if c in ids]} for r in arbol.get("rutas", [])]
    (carpeta / "rutas.json").write_text(json.dumps([r for r in rutas if r["cursos"]], ensure_ascii=False, indent=1), encoding="utf-8")
    for cid in ids:
        curso, lista = asyncio.run(_llamar_varios([("leer_curso", {"curso": cid}), ("listar_lecciones", {"curso": cid})]))
        curso, lista = _json(curso), _json(lista)["lecciones"]
        dc = carpeta / cid
        (dc / "lecciones").mkdir(parents=True, exist_ok=True)
        if curso.get("datos"):
            (dc / "datos.json").write_text(json.dumps(_datos_limpios(curso["datos"]), ensure_ascii=False, indent=1), encoding="utf-8")
        if curso.get("plan") and (pisar or not (dc / "plan.md").exists()):
            (dc / "plan.md").write_text(_generico(curso["plan"]), encoding="utf-8")
        lecs = [_json(t) for t in asyncio.run(_llamar_varios(
            [("leer_leccion", {"curso": cid, "mision_id": l["mision_id"]}) for l in lista]))] if lista else []
        imgs = set()
        for l in lecs:
            limpia = {k: l.get(k) for k in ("mision_id", "titulo", "modulo", "pasos", "fuentes", "tarjetas")}
            f = dc / "lecciones" / f"{l['mision_id']}.json"
            if pisar or not f.exists():
                f.write_text(_generico(json.dumps(limpia, ensure_ascii=False, indent=1)), encoding="utf-8")
            imgs |= {p["url"].rsplit("/", 1)[-1] for p in l["pasos"]
                     if p.get("tipo") == "imagen" and p.get("url", "").startswith(f"/imagenes/{cid}/")}
        if imgs:
            (dc / "imagenes").mkdir(exist_ok=True)
            try:
                for t in asyncio.run(_llamar_varios([("leer_imagen", {"curso": cid, "archivo": a}) for a in sorted(imgs)])):
                    im = _json(t)
                    (dc / "imagenes" / im["archivo"]).write_bytes(base64.b64decode(im["base64_data"]))
            except SystemExit as e:  # p. ej. una app vieja sin leer_imagen: el resto del contenido sí se exporta
                print(f"  aviso: no se pudieron bajar las imágenes de {cid} ({e})")
        print(f"{cid}: {len(lecs)} lecciones, {len(imgs)} imágenes, plan {'sí' if curso.get('plan') else 'no'}")


def _fusionar(actual, nuevo):
    """Agrega al árbol actual las ramas y cursos que no tiene; no toca los que ya existen."""
    por_id = {n["id"]: n for n in actual}
    for n in nuevo:
        if n["id"] not in por_id:
            actual.append(n)
        elif not n.get("curso") and not por_id[n["id"]].get("curso"):
            por_id[n["id"]]["hijos"] = _fusionar(por_id[n["id"]].get("hijos", []), n.get("hijos", []))
    return actual


def _sin_resumen(nodos):
    return [{k: v for k, v in n.items() if k not in ("resumen", "score_pct", "n_cursos", "hijos")}
            | ({"hijos": _sin_resumen(n["hijos"])} if "hijos" in n else {}) for n in nodos]


def importar(carpeta, forzar=False):
    carpeta = Path(carpeta)
    actual = _json(asyncio.run(_llamar("ver_arbol", {})))
    nuevo = json.loads((carpeta / "arbol.json").read_text(encoding="utf-8"))
    asyncio.run(_llamar("guardar_arbol", {"arbol": _fusionar(_sin_resumen(actual["arbol"]), nuevo)}))
    for dc in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        cid = dc.name
        curso = _json(asyncio.run(_llamar("leer_curso", {"curso": cid})))
        llamadas = []
        if (dc / "plan.md").exists() and (forzar or not curso.get("plan")):
            llamadas.append(("guardar_plan", {"curso": cid, "plan": (dc / "plan.md").read_text(encoding="utf-8")}))
        if (dc / "datos.json").exists() and (forzar or not curso.get("datos")):
            llamadas.append(("guardar_datos", {"curso": cid, "datos": json.loads((dc / "datos.json").read_text(encoding="utf-8"))}))
        for im in (sorted((dc / "imagenes").glob("*")) if (dc / "imagenes").exists() else []):
            llamadas.append(("subir_imagen", {"curso": cid, "nombre": im.stem,
                                              "base64_data": base64.b64encode(im.read_bytes()).decode()}))
        lecs = sorted((dc / "lecciones").glob("*.json")) if (dc / "lecciones").exists() else []
        for f in lecs:
            l = json.loads(f.read_text(encoding="utf-8"))
            llamadas.append(("guardar_leccion", {"curso": cid, "mision_id": l["mision_id"], "titulo": l["titulo"],
                                                 "pasos": l["pasos"], "fuentes": l.get("fuentes") or [],
                                                 "tarjetas": l.get("tarjetas") or []}))
        if llamadas:
            asyncio.run(_llamar_varios(llamadas))
        print(f"{cid}: {len(lecs)} lecciones importadas")
    if (carpeta / "rutas.json").exists():
        nuevas = json.loads((carpeta / "rutas.json").read_text(encoding="utf-8"))
        tengo = [{k: r[k] for k in ("id", "nombre", "descripcion", "cursos") if k in r} for r in actual.get("rutas", [])]
        ids = {r["id"] for r in tengo}
        asyncio.run(_llamar("guardar_rutas", {"rutas": tengo + [r for r in nuevas if r["id"] not in ids]}))
        print("rutas: " + ", ".join(r["nombre"] for r in nuevas))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "imagenes":
        imagenes(sys.argv[2], sys.argv[3])
    elif cmd == "subir":
        curso, archivo = sys.argv[2], Path(sys.argv[3])
        nombre = sys.argv[4] if len(sys.argv) > 4 else archivo.stem
        b64 = base64.b64encode(archivo.read_bytes()).decode()
        print(asyncio.run(_llamar("subir_imagen", {"curso": curso, "nombre": nombre, "base64_data": b64})))
    elif cmd == "exportar":
        a = sys.argv[2:]
        solo = set(a[a.index("--cursos") + 1].split(",")) if "--cursos" in a else None
        exportar(a[0], solo, "--pisar" in a)
    elif cmd == "importar":
        importar(sys.argv[2], "--forzar" in sys.argv[3:])
    elif cmd == "llamar":
        args = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        print(asyncio.run(_llamar(sys.argv[2], args)))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
