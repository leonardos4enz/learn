# Plan: 01 Introduction to LangChain

Id del curso: `langchain` (`/tutor langchain`). Es el primer curso de la ruta LCAE y cubre la base del dominio
**Build** (25 % del examen): `create_agent`, tools, memoria, MCP, contexto, multiagente y middleware.

## Meta y punto de partida

Construir agentes con LangChain v1: `create_agent` (un loop ReAct sobre LangGraph), sus tools, su memoria de corto
plazo (checkpointer + `thread_id`), el contexto en runtime, MCP, multiagente y el middleware para producción (resumir,
HITL, modelos/prompts/tools dinámicos). Solo se necesita Python básico.

## Material

- Cada misión trae en `links` sus videos y lecturas de LangChain Academy (botones en la app).
- Repo oficial: `langchain-ai/lca-lc-foundations` (MIT). Notebooks en `notebooks/module-X/`; los proyectos (Personal
  Chef, Wedding Planner, Email Assistant) traen además su `.py` y `langgraph.json` para `langgraph dev`.
- Lecciones de la app: explicación con el código del notebook (completo) y después predicciones.

## Modo por defecto: rápido

1. **Explicación:** el video oficial (botones de la misión) o la lección de la app.
2. **~15 min con el tutor:** 1–2 preguntas de días anteriores, 2–3 predicciones o preguntas estilo examen (escenario +
   4 opciones) sobre variaciones, dudas y 4–6 tarjetas. Hoja impresa opcional.
3. Verifica la misión (`dominada` / `repasar`).

## Actividades

Predecir, revisar y romper sobre código corto. Como el examen es de opción múltiple, usa preguntas estilo examen con
el porqué de las opciones incorrectas. Relaciona con lo que viene: los checkpointers y el middleware reaparecen en
Deep Agents; LangGraph explica por dentro el loop que `create_agent` arma.

## Entorno y reglas propias

- Carpeta del curso (`carpeta_local`): el repo clonado. Se instala con `uv sync` (o `uv venv` + `uv pip install -r
  requirements.txt`); notebooks con el kernel del `.venv`. El `.env` sale de `example.env`.
- Keys: `OPENAI_API_KEY` (modelo por defecto), `TAVILY_API_KEY` (búsqueda web), `LANGSMITH_API_KEY` (opcional, trazas).
  Nunca leas `.env` ni pidas keys en el chat.
- Los proyectos se corren con `langgraph dev` desde su carpeta (`notebooks/module-1` y `module-3`).

## Mapa de misiones

| # | Misión | Concepto clave | Malentendido típico |
|---|---|---|---|
| 0.A | Bienvenida y setup | `uv`, `.env`, kernel del notebook | Correr el notebook con otro Python y culpar al código |
| 1.A | Modelos y prompting | `init_chat_model`, mensajes, system prompt | Creer que el modelo "recuerda" entre llamadas |
| 1.B | Tools y búsqueda web | `@tool`, docstring = descripción, el loop tool_call → ToolMessage | Creer que el modelo ejecuta la tool |
| 1.C | Memoria de corto plazo | checkpointer + `thread_id` | Creer que la memoria está en el modelo |
| 1.D | Mensajes multimodales | content blocks (imagen, audio) | Creer que todo modelo acepta cualquier tipo |
| 1.E | Proyecto Personal Chef | juntar tools + memoria + `langgraph dev` | — |
| 2.A | MCP | tools de un servidor externo (`langchain-mcp-adapters`) | Confundir el servidor MCP con una tool |
| 2.B | Runtime context y state | `context_schema` (fijo por run) vs state (cambia) | Guardar en el state lo que es contexto |
| 2.C | Sistemas multiagente | un agente como tool de otro | Creer que el subagente ve todo el historial |
| 2.D | Proyecto Wedding Planner | coordinador + especialistas | — |
| 3.A | Middleware | ganchos `before_*`/`after_*` (agregan nodos al grafo) y `wrap_*` (envuelven la llamada) | Creer que todo middleware es un nodo más, o que ninguno toca el grafo |
| 3.B | Conversaciones largas | resumir/recortar mensajes | Confundir borrar del state con no mandárselo al modelo |
| 3.C | Human in the loop | interrupción, aprobar/editar/rechazar | Creer que pausar funciona sin checkpointer |
| 3.D | Agentes dinámicos | modelo, prompt y tools que cambian por request | Creer que se fijan al crear el agente |
| 3.E | Proyecto Email Assistant | middleware + HITL en un agente real | — |
| 3.F | Agent Chat UI y cierre | una UI para un agente desplegado | — |
