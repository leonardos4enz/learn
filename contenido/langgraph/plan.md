# Plan: 02 Introduction to LangGraph

Id del curso: `langgraph` (se invoca con `/tutor langgraph`). Carpeta del curso: el repo
`langchain-academy/` del curso (el trabajo con el tutor va en su subcarpeta `tutor/`).

> **Servidor para practicar:** para el SDK y el Módulo 6 usa `langgraph dev` en local
> (`http://127.0.0.1:2024`). Si el estudiante tiene su propio Agent Server desplegado, puede usar su URL;
> si una lección muestra una URL o una salida de un server desplegado, trátala como ejemplo.

## Meta y punto de partida

Entender LangGraph a fondo (state, reducers, memoria, humano en el loop, paralelismo, memoria de
largo plazo y deploy) como parte de una ruta para ser AI Engineer. Al empezar, pregúntale al estudiante
qué notebooks ya hizo por su cuenta para no repetir lo que domina.

## Material

- Notebooks del curso en `langchain-academy/module-X/*.ipynb`. Son **material de referencia para
  ti**: los lees para preparar la sesión; el estudiante no tiene que recorrerlos ni ver los videos.
- Para dudas de API, usa el MCP de docs de LangChain si está disponible. No inventes firmas de
  funciones: si no estás seguro, corre el código y mira.

## Actividades del núcleo: entender sin escribir código desde cero

El estudiante **no escribe código a mano** (la tendencia es que la IA lo escriba). Lo respetamos
con cuidado: si la IA hace *todo*, no se aprende (Bastani 2025). Así que tú escribes el código y
**el estudiante pone el pensamiento**. Cada misión usa al menos tres actividades:

1. **Predice.** Antes de correr el código, el estudiante dice qué va a pasar: qué imprime, cómo queda el
   state, qué nodo se ejecuta, si truena y por qué. Después lo corres y comparan. Lo valioso son
   los errores de predicción. Usa el tipo `predice` de la pantalla en vivo.
2. **Diseña.** El estudiante especifica en palabras el state, los nodes, los edges y los reducers. Tú
   implementas **exactamente lo que dijo**, aunque esté mal, y él ve la consecuencia. No corrijas
   su diseño antes de correrlo.
3. **Revisa.** Le das código tuyo, a veces con un bug plantado (avísale que *puede* haber uno, sin
   decir si lo hay). El estudiante lo encuentra y explica por qué falla.
4. **Rompe.** El estudiante propone un cambio ("¿y si quito el reducer?"), predice la consecuencia y lo
   corres.
5. **Toque mínimo.** Si el concepto lo pide, el estudiante cambia **una línea** clave. Nunca más, salvo que
   él quiera.

Prefiere grafos **sin LLM** (nodos de Python puro): son gratis, instantáneos y deterministas. Usa
el LLM solo cuando el concepto lo necesite.

## Hojas y examen

- **De memoria:** preguntas de entender ("¿qué pasa si dos nodes devuelven la misma key sin
  reducer?"), no de sintaxis ("¿cómo se importa StateGraph?").
- **Predice:** un snippet corto sin LLM, con 2–3 preguntas sobre su salida. Verifica las
  respuestas corriendo el código en el `.venv` antes de guardar la hoja.
- **Dibuja:** el grafo o el flujo del state.
- **Examen de módulo:** 4 de predecir, 3 de diseñar ("¿cómo armarías un grafo que…?") y 2–3 de
  detectar un bug.

## Proyecto del estudiante

En la primera sesión (si `proyecto` es `null`), ayúdale a elegir un agente que **le importe**.
Ofrece 3 ideas concretas y deja que proponga la suya: un asistente de estudio que le pregunta
sobre sus cursos, un bot para algo de su trabajo o negocio, o un investigador que le arma
resúmenes.

- Vive en `tutor/proyecto/` como scripts `.py`, para correrlos con
  `uv run python tutor/proyecto/<archivo>.py` desde `langchain-academy/`.
- Cada módulo le agrega una feature (ver el mapa de abajo). Regístralas en `proyecto.features`.
- En el Módulo 6 se le habla por el SDK con `langgraph dev`; desplegarlo es opcional.

## Hilo: nanograph (abrir el capó)

Un mini-LangGraph en Python puro, en `tutor/nanograph/`, que crece por etapas (el hilo
`nanograph` en `datos.json`). **Tú lo escribes**, pero antes de cada etapa el estudiante **diseña** la
decisión clave ("¿cómo guardarías el state entre pasos?"). Después predice qué hará con un grafo
de prueba. Al final, compáralo con LangGraph real: "esto que hicimos en 15 líneas es lo que hace
`add_messages` o el checkpointer". Estilo Karpathy (micrograd, nanoGPT).

## Entorno y reglas propias

- Corre todo **desde `langchain-academy/`** con `uv run python ...`: usa su `.venv` con Python
  3.12. Si el estudiante lo corre con el botón ▶️ de VS Code, usará el Python del sistema y la carpeta
  equivocada, y fallará; explícale la causa.
- Los notebooks no leen `.env`. En los scripts que usan LLM, carga las keys con
  `load_dotenv("module-1/studio/.env")` dentro del script.
- Modelo por defecto: `ChatOpenAI`, como el curso.
- Relaciona cada concepto con lo ya visto: `create_agent` del curso 01 y, más adelante, Deep
  Agents (curso 03).

## Mapa de misiones

Cada misión toma su material de uno o más notebooks (léelos antes de la sesión). La columna
"Malentendido típico" es lo que hay que hacer salir a la luz con una predicción: si el estudiante lo
predice bien, avanza rápido; si no, ahí está la sesión.

Las rutas son relativas a `langchain-academy/`.

### Módulo 1: Fundamentos

| # | Misión | Notebook | Concepto clave | Malentendido típico |
|---|---|---|---|---|
| 1.1 | El grafo más simple | `module-1/simple-graph.ipynb` | state, nodes, edges, conditional edge | — |
| 1.2 | Chain: mensajes, tools y reducers | `module-1/chain.ipynb` | mensajes, `bind_tools`, `add_messages` | — |
| 1.3 | Agente ReAct | `module-1/agent.ipynb` | loop `assistant` ⇄ `tools` con `tools_condition` | — |
| 1.4 | Deployment: el Agent Server | `module-1/deployment.ipynb` | Agent Server, `langgraph.json`, Studio y SDK | Creer que Studio es el servidor; es un cliente más de su API. |
| 1.A | El grafo que decide | `module-1/router.ipynb` | conditional edges, `tools_condition`, el LLM elige ruta | Creer que el edge "llama" al tool; en realidad el LLM devuelve un `tool_call` y el edge solo lee el último mensaje para decidir. |
| 1.B | El grafo que recuerda | `module-1/agent-memory.ipynb` | `MemorySaver`, `thread_id`, `config` | Creer que la memoria está "en el modelo" o en el grafo. Está en el checkpointer, por thread: otro `thread_id` = conversación nueva. |

- **nanograph etapa 1** (después de 1.A): `StateGraph` con `add_node`, `add_edge`,
  `add_conditional_edges` e `invoke`, en unas 40 líneas. Antes, el estudiante diseña: "¿cómo sabe el motor
  qué nodo sigue?".
- **Proyecto:** elegir el agente y hacer su versión 0: un ReAct con 1–2 tools y memoria por thread.

### Módulo 2: State y memoria

| # | Misión | Notebook | Concepto clave | Malentendido típico |
|---|---|---|---|---|
| 2.A | La forma del state | `module-2/state-schema.ipynb` | TypedDict, dataclass y Pydantic; solo Pydantic valida en runtime | Creer que TypedDict valida tipos (no lo hace: pasa un `str` sin error). |
| 2.B | Quién gana cuando dos escriben | `module-2/state-reducers.ipynb` | Sobrescritura por defecto, `InvalidUpdateError` en ramas paralelas, `Annotated[list, add]`, reducers propios, `add_messages` (añade, reemplaza por id, `RemoveMessage`) | Creer que el node "modifica" el state; en realidad devuelve un *update* y el reducer decide cómo se combina. |
| 2.C | State privado y entrada/salida | `module-2/multiple-schemas.ipynb` | Private state entre nodes, `input`/`output` schema | Creer que todo lo que un node devuelve llega al usuario. |
| 2.D | Que el historial no explote | `module-2/trim-filter-messages.ipynb` | Filtrar con `RemoveMessage` vs. pasarle al LLM solo una parte vs. `trim_messages` por tokens | Confundir "borrar del state" con "no mandárselo al LLM" (son dos cosas distintas). |
| 2.E | Resumir la conversación | `module-2/chatbot-summarization.ipynb` | Node de resumen + borrar mensajes viejos + checkpointer | Creer que el resumen reemplaza la memoria; convive con los últimos mensajes. |
| 2.F | Memoria que sobrevive reinicios | `module-2/chatbot-external-memory.ipynb` | `SqliteSaver` vs. `MemorySaver` | Creer que `MemorySaver` persiste al reiniciar el proceso (no: vive en RAM). |

- **Predicción estrella (2.B):** el grafo `node_1 → (node_2, node_3)` donde ambos devuelven `foo`
  sin reducer. ¿Qué pasa? (`InvalidUpdateError`). Luego con `add`: ¿en qué orden quedan?
- **nanograph etapa 2:** reducers por key leyendo `Annotated`. Antes, el estudiante diseña: "¿dónde y cuándo
  se combinan los updates?".
- **Proyecto:** resumen automático cuando el historial pasa de N mensajes y persistencia en SQLite.
- **Relación con lo ya visto:** `add_messages` es lo que `create_agent` (curso 01) usaba por dentro.

### Módulo 3: Humano en el loop

| # | Misión | Notebook | Concepto clave | Malentendido típico |
|---|---|---|---|---|
| 3.A | Ver mientras corre | `module-3/streaming-interruption.ipynb` | `stream_mode` `updates` vs `values`, streaming de tokens | Creer que `updates` y `values` dan lo mismo. |
| 3.B | Pausa para aprobar | `module-3/breakpoints.ipynb` | `interrupt_before`, reanudar con `None` | Creer que la pausa necesita algo especial; solo funciona porque hay checkpointer. |
| 3.C | Editar el state en pausa | `module-3/edit-state-human-feedback.ipynb` | `update_state`, node de feedback humano | Creer que `update_state` sobrescribe; pasa por el reducer igual que un node. |
| 3.D | Pausa decidida por el grafo | `module-3/dynamic-breakpoints.ipynb` | Interrumpir desde dentro de un node según una condición | (Ojo: el curso usa `NodeInterrupt`; en versiones nuevas se usa `interrupt()`. Verifícalo en el `.venv` antes de enseñarlo.) |
| 3.E | Viajar en el tiempo | `module-3/time-travel.ipynb` | `get_state_history`, replay, fork desde un checkpoint | Creer que el replay lo vuelve a correr todo, o que no corre nada: reutiliza lo guardado **hasta** el checkpoint y vuelve a ejecutar (LLM incluido) lo que va **después**. |

- **nanograph etapa 3:** checkpointer (lista de snapshots por thread) e `interrupt_before`. Antes,
  el estudiante diseña: "¿qué hay que guardar para poder continuar después?".
- **Proyecto:** pedir aprobación antes de cualquier tool "peligroso" y permitir editar.

### Módulo 4: Paralelismo y composición

| # | Misión | Notebook | Concepto clave | Malentendido típico |
|---|---|---|---|---|
| 4.A | Varias ramas a la vez | `module-4/parallelization.ipynb` | Fan-out/fan-in, supersteps, orden de updates | Creer que una rama espera a la otra a mitad de camino; todo el superstep termina junto. |
| 4.B | Grafos dentro de grafos | `module-4/sub-graph.ipynb` | Subgraphs y keys compartidas | Creer que el subgraph ve todo el state del padre. |
| 4.C | Map-reduce dinámico | `module-4/map-reduce.ipynb` | `Send` para N ramas que no se conocen de antemano | Creer que el número de ramas se fija al compilar. |
| 4.D | Juntarlo todo | `module-4/research-assistant.ipynb` | Proyecto integrador del curso | El estudiante lo **revisa y explica** en vez de construirlo: que dibuje el grafo y prediga el flujo. |

- **nanograph etapa 4:** supersteps paralelos y `Send`. Antes, el estudiante diseña: "¿cuándo puede correr
  un node?".
- **Proyecto:** un "modo investigación" que lance varias búsquedas en paralelo y las junte.

### Módulo 5: Memoria de largo plazo

| # | Misión | Notebook | Concepto clave | Malentendido típico |
|---|---|---|---|---|
| 5.A | Memoria entre threads | `module-5/memory_store.ipynb` | `Store`, namespaces, `put`/`get`/`search` | Confundir el store (entre threads) con el checkpointer (dentro de un thread). |
| 5.B | Perfil del usuario | `module-5/memoryschema_profile.ipynb` | Schema de perfil y Trustcall | Creer que el LLM siempre actualiza bien un JSON grande. |
| 5.C | Colección de recuerdos | `module-5/memoryschema_collection.ipynb` | Colección vs. perfil | ¿Cuándo conviene uno y cuándo el otro? |
| 5.D | Agente que decide qué recordar | `module-5/memory_agent.ipynb` | Agente que actualiza memorias como tool | — |

- **Relación con lo ya visto:** es la memoria de largo plazo de Deep Agents (M3.3), si el estudiante
  lo toma después.
- **Proyecto:** que su agente recuerde preferencias entre conversaciones.

### Módulo 6: Deploy

Este módulo se practica con `langgraph dev` en local (si el estudiante ya desplegó un Agent Server, relaciónalo:
es la misma API). Es corto:

| # | Misión | Notebook | Concepto clave |
|---|---|---|---|
| 6.A | Hablarle al server | `module-6/connecting.ipynb` | SDK, `RemoteGraph`, runs, threads y background runs |
| 6.B | Un grafo, varias personalidades | `module-6/assistant.ipynb` | Assistants y configuración |
| 6.C | Cuando el usuario escribe dos veces | `module-6/double-texting.ipynb` | reject / enqueue / interrupt / rollback |

- **Proyecto final:** hablarle a su agente por el SDK con `langgraph dev`; desplegarlo solo si el estudiante quiere.
