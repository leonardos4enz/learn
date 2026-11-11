# Plan: 05 Monitoring Production Agents

Id del curso: `monitoring` (`/tutor monitoring`). Cubre el dominio **Monitor (25 %) del LCAE**.

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

- Repo oficial del curso: carpeta `lca-production-monitoring/python` (~95 MB: trazas JSON).
  `uv sync`, Python **==3.12.0** exacto; si no hay `.venv`, pide permiso antes de instalar.
- Keys: `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`.
- Comandos rotos del material: el lab del módulo 2 necesita `--input module2_traces.json`; el capstone usa
  `upload_csa_traces.py --input ... --project ...` (no `upload_traces.py`). No hay `requirements.txt` (es `uv sync`).
- Insights y online evals piden plan Plus/keys del proveedor: se enseñan conceptualmente. `client.generate_insights` de la
  página falla en langsmith 0.14 (falta `chat_histories`).
- Labs y quizzes los hace el estudiante solo: las lecciones usan datos inventados para no dar respuestas. No le des las
  oficiales.
- Lecciones: 9.

## Mapa de misiones

Las misiones y sus links están en los datos del curso. Concepto clave y malentendido que una predicción debe sacar
a la luz (complétalos al ingestar o al dar cada misión):

| # | Misión | Concepto clave | Malentendido típico |
|---|---|---|---|
| 1.A–1.B | Costo | tokens de entrada/salida por run | Creer que el costo solo depende de la respuesta |
| 2.A | Product analytics | Insights: patrones de uso | — |
| 3.A–3.B | Calidad | latencia, errores, sentimiento, A/B | — |
| 4.A–4.B | Seguridad | alertas, riesgos en producción | — |
| 5.A | Capstone | — | — |
