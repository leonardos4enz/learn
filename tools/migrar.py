"""Sube a Mi Tutor (por el MCP) el árbol, los cursos, las hojas y las tarjetas iniciales que vivían en archivos locales.

Uso:
  python tools/migrar.py <url-base> <ruta-del-repo-AI-Engineer-Courses>
El token del MCP se lee de la variable de entorno MI_TUTOR_TOKEN (nunca se imprime).
Es idempotente: volver a correrlo reemplaza árbol, datos, plan y hojas; las tarjetas repetidas se ignoran.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

TARJETAS_M1 = [
    {"modulo": "1", "mision": "1.1", "frente": "¿Cuáles son las tres piezas con las que se define un grafo en LangGraph y qué hace cada una?",
     "reverso": "**State** (la memoria compartida), **nodes** (funciones que reciben el state y devuelven un update) y **edges** (qué node sigue, fijo o condicional)."},
    {"modulo": "1", "mision": "1.1", "frente": "El state tiene `foo = 1` y no hay reducer. Un node devuelve `{\"foo\": 2}`. ¿Cuánto vale `foo` y por qué?",
     "reverso": "`2`. Sin reducer, el update **sobrescribe** la key. El node no modifica el state: devuelve un update que LangGraph aplica."},
    {"modulo": "1", "mision": "1.2", "frente": "¿Por qué la key `messages` se declara con `add_messages` y no como lista normal?",
     "reverso": "Para que los mensajes **se acumulen** en vez de sobrescribirse. Además, si llega un mensaje con un id que ya existe, lo **reemplaza**."},
    {"modulo": "1", "mision": "1.2", "frente": "Con `add_messages`, ya hay `[Human(id=1), AI(id=2, \"qué tal\")]` y un node devuelve `AI(id=2, \"buenas\")`. ¿Cómo queda la lista?",
     "reverso": "`[Human(id=1), AI(id=2, \"buenas\")]`: siguen siendo dos mensajes, porque el id 2 ya existía y se **reemplaza**."},
    {"modulo": "1", "mision": "1.3", "frente": "En el agente ReAct, ¿qué revisa `tools_condition` para elegir entre `tools` y `END`?",
     "reverso": "Si el último mensaje (un AIMessage) trae **`tool_calls`**. El edge no ejecuta el tool: solo lee el mensaje y elige la ruta."},
    {"modulo": "1", "mision": "1.3", "frente": "¿Qué edge convierte un grafo con LLM y tools en un *loop* ReAct?",
     "reverso": "El edge **tools → assistant**: después de correr el tool, el resultado vuelve al LLM para que decida otra vez."},
    {"modulo": "1", "mision": "1.1", "frente": "En un conditional edge, ¿con qué state se toma la decisión: el de antes o el de después del node anterior?",
     "reverso": "Con el state **después** de aplicar el update del node anterior."},
    {"modulo": "1", "mision": "1.4", "frente": "¿Qué es un Agent Server (LangGraph Platform) y qué te da que no tienes con `graph.invoke` en un notebook?",
     "reverso": "Un servidor que sirve tus grafos por **API**: threads y estado persistente, runs (también en segundo plano), streaming y Studio. Leo lo tiene en su VPS."},
]


def convertir(nodos, repo):
    out = []
    for n in nodos:
        m = {k: v for k, v in n.items() if k not in ("carpeta", "hijos")}
        if "carpeta" in n:
            m["curso"] = True
            m["carpeta_local"] = str((repo / n["carpeta"]).parent).replace("\\", "/")
        if "hijos" in n:
            m["hijos"] = convertir(n["hijos"], repo)
        out.append(m)
    return out


async def main(url, repo):
    token = os.environ["MI_TUTOR_TOKEN"]
    reg = json.loads((repo / "tutor" / "cursos.json").read_text(encoding="utf-8"))
    async with streamablehttp_client(url.rstrip("/") + "/mcp", headers={"Authorization": f"Bearer {token}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()

            async def call(tool, **args):
                res = await s.call_tool(tool, args)
                txt = " ".join(getattr(c, "text", "") for c in res.content)
                if res.isError:
                    raise SystemExit(f"{tool}: {txt}")
                return txt

            print(await call("guardar_arbol", arbol=convertir(reg["arbol"], repo)))

            def cursos(ns):
                for n in ns:
                    if "carpeta" in n:
                        yield n
                    yield from cursos(n.get("hijos", []))

            for c in cursos(reg["arbol"]):
                carpeta = repo / c["carpeta"]
                if (carpeta / "datos.json").exists():
                    datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8"))
                    print(c["id"], await call("guardar_datos", curso=c["id"], datos=datos))
                if (carpeta / "plan.md").exists():
                    print(c["id"], await call("guardar_plan", curso=c["id"], plan=(carpeta / "plan.md").read_text(encoding="utf-8")))
                for h in sorted((carpeta / "hojas").glob("*.html")) if (carpeta / "hojas").exists() else []:
                    print(c["id"], h.name, await call("guardar_hoja", curso=c["id"], archivo=h.name, html=h.read_text(encoding="utf-8")))
            print("tarjetas M1:", await call("crear_tarjetas", curso="langgraph", tarjetas=TARJETAS_M1))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], Path(sys.argv[2])))
