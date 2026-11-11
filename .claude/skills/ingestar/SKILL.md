---
name: ingestar
description: "Convierte el material de un curso (carpeta con notebooks, .md y código, PDFs, links, imágenes o la skill oficial lca-deepagents) en lecciones de la app Mi Tutor, una por misión, en español, con el código verificado, imágenes y 4–8 tarjetas de entender por lección. Primero propone el temario y espera a que el estudiante lo apruebe. Se invoca con /ingestar <id-del-curso> <fuente>."
---

# Ingestar un curso en Mi Tutor

Conviertes material de estudio en **lecciones** de la app Mi Tutor (vista Lecciones). Hablas en
español; los términos técnicos se quedan en inglés cuando es lo natural. Todo se guarda por el MCP
**`mi-tutor`**; no dejes lecciones solo en archivos locales.

Antes de escribir, lee `FILOSOFIA.md` (raíz del repo learn): cada decisión de la lección sale
de ahí. Lo esencial está abajo.

## Entrada

`/ingestar <curso> <fuente>`. Si falta algo, pregúntalo con `AskUserQuestion`.

- **curso:** el `id` del árbol (`ver_arbol`). Si el curso no existe, créalo como dice la skill
  `tutor` ("Crear o arrancar un curso").
- **fuente**, cualquiera de estas (pueden ser varias):
  - una carpeta con notebooks (`.ipynb`), `.md`, código o PDFs;
  - links (léelos con la herramienta web; no descargues archivos sin permiso del estudiante);
  - imágenes sueltas;
  - para el curso 03 (Deep Agents): las lecciones de la skill oficial en
    `~/.claude/skills/lca-deepagents/references/` (`m1.1-overview.md`, …). Úsalas como guion y
    verifica el código en la carpeta del curso (`carpeta_local` en el árbol), track `python` o `typescript`.

## Paso 1. Proponer el temario y esperar

1. Lee `leer_curso(<curso>)` y `listar_lecciones(<curso>)`. Si el curso ya tiene misiones,
   **respétalas**: una lección por misión, con el mismo `id`.
2. Recorre la fuente (índice, títulos, celdas Markdown) y arma el temario: **unidades (módulos) y
   lecciones (misiones)**, cada una con su fuente, el concepto clave y el malentendido típico que
   un paso `predice` debe sacar a la luz.
3. Muéstraselo al estudiante como tabla y **espera su aprobación** (`AskUserQuestion`: Aprobar /
   Cambiar algo). No escribas lecciones antes de eso.
4. Si el temario agrega misiones nuevas, guárdalas en los datos del curso (`leer_curso` →
   `guardar_datos` con el JSON completo) y en el mapa del plan (`guardar_plan`).

## Paso 2. Escribir cada lección

Una lección = una misión = 8–16 pasos. **Orden fijo:**

1. **El problema** (1 paso `markdown`): qué no se puede hacer todavía y por qué importa. Corto.
2. **Explicación con un ejemplo resuelto** (varios pasos): un concepto por paso.
   - El **código va completo**, nunca recortado ni con `...`: el que el estudiante podría copiar y correr.
     Si es largo, pártelo en pasos que cada uno sea un archivo o bloque completo con sentido.
   - En cada `codigo` y `mermaid`, `notas` de 2–5 líneas que dicen qué mirar, y `resaltar` solo
     las 1–3 líneas clave.
   - Pon la **salida real** que obtuviste al correrlo (en un `markdown` o en las notas).
   - Un diagrama `mermaid` del grafo cuando ayude (marca el nodo clave con `class X clave`).
3. **Predice** (2–4 pasos `predice`) al final: preguntas sobre el ejemplo ya explicado o una
   variación pequeña ("¿y si quito el reducer?"). La `respuesta` dice el resultado **y el porqué**,
   en 2–5 líneas. Apunta al malentendido típico.
   **Cada pregunta se tiene que poder contestar con lo que está en pantalla.** el estudiante no tiene el código a la mano:
   - Si pregunta por una **variación** (otro state, una línea cambiada, otro input), pon el **código completo de la
     variación** dentro del `contenido` en un bloque ```python``` y córrelo para la respuesta.
   - Si pregunta por un ejemplo ya mostrado, pon `"ref": <número del paso de código>`: la app muestra un botón
     "Ver el código del paso N". Sin `ref`, la app ofrece el último paso de código anterior.
   - Nombra siempre qué ejemplo es ("el contador del paso 3"), nunca "el grafo de antes".

4. **Resumen** (1 paso `markdown`): 3–5 viñetas con lo que debe quedar, y cómo se relaciona con lo
   ya visto (p. ej. `create_agent` del curso 01, checkpointers de Deep Agents).

Por qué este orden: en temas nuevos, la instrucción con poca guía rinde menos que un ejemplo
resuelto bien explicado (Kirschner, Sweller y Clark 2006); predecir después obliga a recordar
(práctica de recuerdo, Dunlosky 2013). Un concepto por paso es segmentación (Mayer). **Nada
decorativo**: sin emojis, chistes, datos curiosos ni frases de relleno (coherencia, Mayer;
*seductive details*, Sundararajan y Adesope 2020).

Estilo: frases cortas, en segunda persona ("tú"), sin "¡Genial!". Explica el *por qué*, no solo
el *qué*. Máximo ~120 palabras por paso `markdown`.

### Verificar el código (obligatorio)

- Corre **cada bloque** de código de la lección en el entorno del curso y copia la salida real.
  El entorno está en el plan del curso, en `carpeta_local` del árbol y en `CLAUDE.local.md` (si existe). Ejemplo:
  `cd "<carpeta del curso>" && .venv/Scripts/python archivo.py`.
- Escribe los scripts de prueba en tu scratchpad, no en el repo.
- Si el notebook usa una API vieja (p. ej. `NodeInterrupt`), comprueba qué hace la versión
  instalada y enseña la que funciona; menciónalo en una nota.
- Si el código llama a un LLM y necesita keys: carga el `.env` desde el script
  (`load_dotenv("module-1/studio/.env")`) **sin leer ni imprimir el archivo**. Si no hay key o
  falla, usa la salida guardada en el notebook y dilo en la nota ("salida del notebook original").
- Prefiere ejemplos **sin LLM** (nodes de Python puro): deterministas y gratis.

### Imágenes

- Saca las imágenes incrustadas del material con el ayudante del repo `learn`:
  `.venv/Scripts/python tools/tutor_mcp.py imagenes <notebook.ipynb> <carpeta-scratchpad>`
- Súbelas con `... tutor_mcp.py subir <curso> <archivo> <nombre>` (devuelve la URL
  `/imagenes/<curso>/<archivo>`). Así el base64 no pasa por el chat. La herramienta MCP
  `subir_imagen` existe para imágenes pequeñas que ya tengas en base64. Máx. ~1.5 MB; PNG, JPG,
  GIF o WEBP.
- Usa una imagen solo si **enseña** algo (un diagrama de arquitectura, una captura de Studio). Un
  grafo que puedes dibujar en `mermaid` va mejor en `mermaid` (se adapta al modo oscuro).
- No descargues imágenes de internet sin permiso del estudiante.
- Paso imagen: `{"tipo": "imagen", "titulo", "url", "alt", "notas"}`.

### Tarjetas sugeridas (4–8 por lección)

- Una idea por tarjeta; el frente pide **entender** ("¿qué pasa si…?", "¿por qué…?", "¿cuándo
  usarías…?"), no definiciones. Reverso de 1–3 líneas con el porqué.
- Entran al mazo FSRS cuando el estudiante termina la lección en la app (no las crees tú con
  `crear_tarjetas`). Revisa `ver_tarjetas` para no repetir las que ya existen.

### Guardar

`guardar_leccion(curso, mision_id, titulo, pasos, fuentes, tarjetas)`.
- `fuentes`: los archivos de origen relativos a la carpeta del curso (p. ej.
  `module-1/router.ipynb`) o el link. Siempre al menos uno.
- Para lecciones grandes puedes escribir los argumentos en un JSON en tu scratchpad y correr
  `tutor_mcp.py llamar guardar_leccion <archivo.json>`.
- Volver a guardar una lección la reemplaza, pero conserva si el estudiante ya la completó.

## Paso 3. Revisar y cerrar

1. `listar_lecciones(<curso>)`: que estén todas las del temario, con su número de pasos.
2. Lee una lección al azar con `leer_leccion` y revisa el orden (explicación → predice), que el
   código esté completo y que no haya relleno.
3. Dile al estudiante cuántas lecciones quedaron y dale un link a la vista con `dar_link("lecciones")`.
4. Si notaste algo que mejorar del método o de la app, regístralo con `registrar_mejora`.

## Repartir el trabajo

Para un curso grande, reparte por módulo en subagentes (uno por módulo) después de que el estudiante apruebe
el temario. Cada subagente recibe: el curso, las misiones de su módulo con su fuente, este archivo
como instrucciones y la ruta del entorno. Al final revisa tú el resultado (Paso 3).

## Secretos

Nunca leas ni imprimas un `.env`, ni pidas keys en el chat. El token del MCP lo lee
`tutor_mcp.py` de la variable `MI_TUTOR_TOKEN` sin mostrarlo.
