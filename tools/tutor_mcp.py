"""Ayudante de la skill `ingestar`: habla con el MCP de Mi Tutor sin pasar archivos grandes por el chat.

Uso (desde cualquier carpeta, con el Python del .venv de learn):
  python tools/tutor_mcp.py imagenes <notebook.ipynb> <carpeta-salida>
      Extrae las imágenes que el notebook trae incrustadas (salidas PNG/JPEG y adjuntos de celdas Markdown).
  python tools/tutor_mcp.py subir <curso> <archivo-imagen> [nombre]
      Sube una imagen local y muestra su URL (/imagenes/<curso>/<archivo>).
  python tools/tutor_mcp.py llamar <herramienta> <args.json>
      Llama a cualquier herramienta del MCP con los argumentos de un archivo JSON (p. ej. guardar_leccion).

URL: variable MI_TUTOR_URL (por defecto https://learn-tutor.ppnoc4.easypanel.host).
Token: variable MI_TUTOR_TOKEN (en Windows se lee también de las variables de usuario). Nunca se imprime.
"""
import asyncio
import base64
import json
import os
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


async def _llamar(tool, args):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    url = os.environ.get("MI_TUTOR_URL", "https://learn-tutor.ppnoc4.easypanel.host").rstrip("/") + "/mcp"
    async with streamablehttp_client(url, headers={"Authorization": f"Bearer {_token()}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            txt = " ".join(getattr(c, "text", "") for c in res.content)
    if res.isError:  # fuera del task group, para que el error salga limpio
        raise SystemExit(f"{tool}: {txt}")
    return txt


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
    elif cmd == "llamar":
        args = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        print(asyncio.run(_llamar(sys.argv[2], args)))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
