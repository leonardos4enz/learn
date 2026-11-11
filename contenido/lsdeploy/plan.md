# Plan: 06 Introduction to LangSmith Deployment

Id del curso: `lsdeploy` (`/tutor lsdeploy`). Cubre el dominio **Deploy (25 %) del LCAE**.

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

- Repo oficial del curso: carpeta `lca-deployment` (el Markdown completo con código está en `thinkific/src/`). Crea el
  `.venv` de `python/` si no existe (con permiso); los labs de m5 traen su propio `pyproject.toml`. El curso fija deepagents 0.5.9.
- Usa **Anthropic** (`ANTHROPIC_API_KEY`) y `LANGSMITH_API_KEY`. El deploy en la nube necesita el **plan Plus** (de pago);
  `langgraph dev` local es gratis. Supabase (5.C) es opcional y necesita cuenta.
- Las misiones 4.B y 5.C no son del temario oficial: se agregaron aparte. El docstring de `checkpointer.py` dice "read-only", pero `update_state` sí escribe
  (crea un checkpoint): enseña eso. Las páginas de m6 usan `open` (macOS); en Windows es `start`.
- Hallazgo: en `api/store.py` el filtro de authorization solo aplica a `search`; `put`/`get`/`delete` lo ignoran.
- Lecciones: 13.

## Mapa de misiones

Las misiones y sus links están en los datos del curso. Concepto clave y malentendido que una predicción debe sacar
a la luz (complétalos al ingestar o al dar cada misión):

| # | Misión | Concepto clave | Malentendido típico |
|---|---|---|---|
| 1.A–1.B | Desplegar | Agent Server, `langgraph.json` | — |
| 2.A–2.B | Conectarte | SDK, threads, runs, assistants, custom routes | Creer que un assistant es otro grafo |
| 3.A | UI de Deployment | — | — |
| 4.A | Memoria | checkpointer (thread) vs store (entre threads) | Confundir uno con otro |
| 4.B | Backends de Deep Agents | dónde viven los archivos de un Deep Agent desplegado | Creer que el filesystem local sobrevive al deploy |
| 5.A–5.C | Auth multi-tenant | authentication (quién eres) vs authorization (qué puedes ver) | Confundirlas |
| 6.A–6.B | Deploy de un Deep Agent | CLI de deepagents, UI propia | — |
