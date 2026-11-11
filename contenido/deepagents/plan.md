# Plan: 03 Introduction to Deep Agents

Id del curso: `deepagents` (`/tutor deepagents`). Cubre el dominio **Build (25 %) del LCAE, y base para Deploy**.

## Ruta LCAE

Este curso es parte de la ruta hacia la **LangChain Certified Agent Engineer** (40 preguntas de opción múltiple,
28 para aprobar, 120 min, 4 dominios de 25 %: Build, Test, Deploy, Monitor). Orden sugerido:
Deep Agents → Building Reliable Agents → Monitoring → LangSmith Deployment → examen. Después de cada curso, el estudiante
hace la sección del examen de práctica que le toca (curso `lcae`). LangGraph no es requisito, pero sus conceptos
(checkpointer, `thread_id`, reducers, `add_messages`, store) reaparecen aquí: si el estudiante ya los vio, relaciónalos.

## Material

Cada misión trae en `links` sus páginas de LangChain Academy (video, lectura, lab o quiz); la app las muestra como
botones en Hoy, en el camino y en la lección. Las "lecturas" son páginas de texto con código; los videos son cortos.
Las páginas de Academy piden cuenta (gratis). Si una misión no tiene lección en la app, enseña desde esas páginas (léelas
con un navegador si tienes uno disponible) o propón `/ingestar`.

## Modo por defecto: rápido

Sentir que se avanza lento desmotiva, así que cada misión es corta:
1. **Explicación:** el estudiante ve el video / lee la página oficial (los botones de la misión) o la lección de la app.
   Es el ejemplo resuelto (Kirschner, Sweller y Clark 2006); no se repite.
2. **15 min con el tutor:** calentamiento de 1–2 preguntas de días anteriores, 2–3 predicciones o "¿qué pasa si…?"
   sobre variaciones del ejemplo, sus dudas, y 4–6 tarjetas. Hoja impresa **opcional**.
3. Verifica la lección/misión igual que siempre (`dominada` / `repasar`).
Si el estudiante pide la misión completa, usa la estructura completa de la skill. Tarjetas: máximo ~10 al día sin culpa.

## Actividades

Predecir, revisar y romper sobre código corto (el estudiante no escribe código desde cero). Como el examen es de opción
múltiple, incluye a menudo preguntas estilo examen: un escenario y 4 opciones, con el porqué de las incorrectas.

## Entorno y secretos

Nunca leas `.env` ni pidas keys en el chat. Para verificar keys, filtra la salida a `configurada` / `<not set>`.

### Propio de este curso

- Fuente para lecciones: la skill `lca-deepagents` (`~/.claude/skills/lca-deepagents/references/mX.Y-*.md`), que
  sigue el mismo temario. Úsala para enseñar o para `/ingestar deepagents`.
- Track **Python**: carpeta `lca-deepagents/python` del repo del curso; `uv run python mX/archivo.py` desde esa
  carpeta (`load_dotenv(override=True)`). Verifica el setup (M0) antes de la primera misión.

- Lecciones (16) escritas con deepagents 0.7 y un modelo falso (`guion.py`, se presenta en 1.A; de 1.B a 1.E se
  importa: si el estudiante corre un ejemplo, que copie `guion.py` junto al script). Usa **Anthropic** (`ANTHROPIC_API_KEY`). En 0.7 no
  existen `pinned_skills`, `include_tools` ni el modo `fork` aunque las páginas los muestren. Nunca uses `LocalShellBackend` con
  un LLM real (puede leer `.env`).

## Mapa de misiones

Las misiones y sus links están en los datos del curso. Concepto clave y malentendido que una predicción debe sacar
a la luz (complétalos al ingestar o al dar cada misión):

| # | Misión | Concepto clave | Malentendido típico |
|---|---|---|---|
| 1.A | Qué es un Deep Agent | harness = loop de agente + piezas incluidas (filesystem, subagents); el planning con `write_todos` es opcional en la 0.7 | Creer que es otro framework aparte; corre sobre LangGraph |
| 1.B | Modelos y system prompt | tu `system_prompt` va primero; el perfil del modelo agrega BASE/SUFFIX (en la 0.7 ya no hay un prompt base grande) | Creer que sin `system_prompt` el agente igual recibe instrucciones detalladas |
| 1.C | Tools y MCP | tools propias + de servidores MCP | Confundir el servidor MCP con un tool |
| 1.D | Mensajes, threads, checkpointers, HITL | lo mismo que LangGraph 1.B y M3 | Creer que la memoria vive en el modelo |
| 1.E | Practica M1 | — | — |
| 2.A–2.B | Entorno, backends, sandboxes, intérprete | dónde viven los archivos del agente | Creer que el filesystem del agente es tu disco |
| 3.A–3.C | Contexto: resumir, offload, skills, memoria | cuidar la ventana de contexto | Confundir memoria de largo plazo con el checkpointer |
| 4.A–4.B | Subagents | delegar con contexto aislado | Creer que el subagent ve todo el historial del padre |
| 5.A–5.C | Proyecto integrador | juntarlo todo, async subagents | — |
| 6.A | Managed Deep Agents | — | — |
