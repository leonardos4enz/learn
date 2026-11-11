# Plan: 04 Building Reliable Agents with LangSmith

Id del curso: `reliable` (`/tutor reliable`). Cubre el dominio **Test (25 %) del LCAE**.

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

- Repo oficial del curso: carpeta `lca-reliable-agents/python`. Se instala con `uv sync` (Python 3.12–3.13); si todavía
  **no tiene `.venv`**, pide permiso al estudiante antes de instalar.
- Keys en `.env` (el estudiante las pone; tú nunca las ves): `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`.
- Trampas del material: el README dice `example.env` pero el archivo es `.env.example`, y `env_utils.py` busca `example.env`
  (sin ese archivo no revisa las keys). La página de 1.B muestra en v2 un bloque que `agent_v2.py` no tiene: manda el repo.
- El agente no usa LangChain: SDK de OpenAI a mano. Experiments, el juez en la UI, Insights y online evals necesitan cuenta de LangSmith.
- Lecciones (8) verificadas con modelos/clientes falsos.

## Mapa de misiones

Las misiones y sus links están en los datos del curso. Concepto clave y malentendido que una predicción debe sacar
a la luz (complétalos al ingestar o al dar cada misión):

| # | Misión | Concepto clave | Malentendido típico |
|---|---|---|---|
| 0.A | Ciclo de vida y setup | build → test → deploy → monitor | — |
| 1.A–1.B | Observability y tracing | trace, run, spans | Creer que el tracing cambia lo que hace el agente |
| 2.A | Evaluar y datasets | dataset = ejemplos con referencia | Creer que se evalúa "a ojo" con un par de pruebas |
| 2.B | Experimentos y evals de código | evaluator determinista | Usar LLM-as-judge para algo que un `==` resuelve |
| 2.C | LLM-as-judge y pairwise | juez con rúbrica; comparar dos versiones | Creer que el juez no se equivoca |
| 3.A–3.B | Producción, Insights, online evals, automations | evaluar tráfico real | Confundir offline (dataset) con online (producción) |
