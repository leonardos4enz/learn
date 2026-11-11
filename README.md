# Mi Tutor (learn)

App de estudio con Claude como tutor: **lecciones** paso a paso (una por misión), misiones por sesión, hojas para imprimir,
**tarjetas de repaso espaciado (FSRS)**, pantalla en vivo, progreso por curso y una lista de **mejoras**, organizado en ramas
(área › serie › curso › módulo › misión).

- **Lecciones:** camino por módulos; cada lección va explicación con ejemplo resuelto → pasos *predice* (hay que contestar
  para avanzar). Al terminarla, sus tarjetas entran al mazo. Se escriben con la skill `ingestar` (`.claude/skills/ingestar`).
  Las imágenes viven en `DATA_DIR/imagenes/<curso>/` y se sirven en `/imagenes/...` solo con sesión.
- **Mejoras:** errores y propuestas del estudiante o del tutor (nueva / aceptada / hecha / descartada).
- **Tiempo:** calendario por mes y semana (tabla `tiempo`), tiempo hábil (semana tipo + excepciones) y predicción de fin
  por curso y total (`app/tiempo.py`: ritmo real con rango del 80 % contra el tiempo hábil). Las lecciones y tarjetas
  se registran solas con un ping cada 30 s mientras el estudiante está activo; las misiones, el tutor por MCP (`iniciar_sesion`,
  `terminar_sesion`, `registrar_sesion`, `editar_sesion`, `ver_tiempo`, `guardar_tiempo_habil`).
- **Imagen del plan de hoy** (`app/imagen.py`, Pillow + Nunito OFL en `app/static/fuentes/`): el bot la manda en el aviso
  de la mañana y con `/hoy`; se ve en `/api/tiempo/plan.png`.
- **Exportar a PDF:** en *Mis estudios* (grafo), cada rama o curso tiene un botón **PDF**: abre un documento con todas
  sus lecciones (respuestas de los *predice* al final de cada una, y sus tarjetas) para guardarlo como PDF o leerlo en
  el celular (`/app/exportar?nodo=<id>`).
- `tools/tutor_mcp.py`: extrae imágenes de notebooks, las sube, llama herramientas del MCP desde archivos JSON y
  **exporta / importa** el contenido (ver abajo).

- **Web:** `/app/` (login con link mágico de Telegram o `ADMIN_PASSWORD`).
- **MCP para Claude Code:** `/mcp` (Streamable HTTP, `Authorization: Bearer $MCP_TOKEN`). Claude es el tutor: lee el curso,
  muestra cosas en vivo, enseña desde las lecciones y guarda datos, hojas, tarjetas, lecciones y mejoras. La app no lleva
  ningún modelo.
- **Bot de Telegram:** aviso diario (`AVISO_HORA`, 08:00) con las tarjetas del día y un link directo; segundo aviso
  (`RECORDATORIO_HORA`, 19:00) si no has repasado. Comandos: `/hoy` (plan de hoy como imagen), `/tarjetas`, `/tiempo`, `/link`. Solo responde a `TELEGRAM_CHAT_ID`.

## Empieza aquí: tu propia copia para estudiar

Cada persona tiene **su propia app** (su progreso y sus tarjetas son suyos). Para estudiar con el contenido de este repo:

1. **Despliega la app** (Docker, por ejemplo en EasyPanel) desde este repo, con un volumen en `/data` y las
   variables `MCP_TOKEN` (una cadena larga y secreta que tú inventas), `ADMIN_PASSWORD` y `PUBLIC_URL`. Telegram es
   opcional. También corre en tu PC (ver "Correr en local").
2. **Clona el repo** y crea `.venv` (ver "Correr en local"). Copia `.mcp.example.json` a `.mcp.json` y pon la URL de
   tu app. Define la variable de entorno `MI_TUTOR_TOKEN` con el mismo valor que tu `MCP_TOKEN`.
3. **Carga el contenido** en tu app:
   `MI_TUTOR_TOKEN=... .venv/Scripts/python tools/tutor_mcp.py importar contenido`
   (árbol de cursos, Ruta LCAE, planes, misiones con links a LangChain Academy y 76 lecciones).
4. **Inscríbete gratis** en los cursos de [LangChain Academy](https://academy.langchain.com) y clona sus repos
   (cada plan y la lección 0.A de cada curso dicen cuál). Para cada curso, pon su carpeta en `carpeta_local` del árbol
   (pídeselo al tutor).
5. Abre **Claude Code en esta carpeta** y escribe `/tutor deepagents` (o el curso que quieras). Si quieres, crea un
   `CLAUDE.local.md` con tu nombre, tu meta y tus carpetas: el tutor lo lee y no se sube a GitHub.

Si no puedes usar la app (por ejemplo, solo tienes el celular), entra a *Mis estudios* y usa el botón **PDF** de
cualquier rama o curso.

### Contenido (`contenido/`)

Copia curada y sin datos personales de los cursos de la ruta hacia la certificación **LangChain Certified Agent
Engineer** (Deep Agents, Building Reliable Agents, Monitoring Production Agents, LangSmith Deployment y el examen) y de
Introduction to LangGraph. Las lecciones son explicaciones propias en español, con código verificado, basadas en los
cursos gratuitos de LangChain Academy (código de ejemplo con licencia MIT); cada una enlaza su material oficial.

- `tools/tutor_mcp.py exportar contenido [--cursos a,b] [--pisar]`: regenera la copia desde tu app (no pisa lo curado).
- `tools/tutor_mcp.py importar contenido [--forzar]`: la carga en tu app (no toca cursos que ya tengan progreso).

## Por qué está hecha así

**Lee [FILOSOFIA.md](FILOSOFIA.md)**: es la esencia de la app. Todo lo que hace tiene su porqué en estudios reales.

Cada decisión tiene evidencia detrás (los botones «?» de la app lo explican): práctica de recuerdo y repaso espaciado
(Dunlosky et al. 2013; Cepeda et al. 2006), IA con guardrails (Bastani et al. 2025), principios de Mayer para la pantalla
(contigüidad, coherencia, señalización, segmentación), texto oscuro sobre claro (Piepenbrock 2013).

## Correr en local

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt
DEV_NOAUTH=1 MCP_TOKEN=prueba PORT=3010 .venv/Scripts/python -m app.main
```

## Producción (EasyPanel)

Proyecto `learn`, servicio App desde GitHub `leonardos4enz/learn` (rama `main`, Dockerfile). Volumen en `/data`
(base SQLite `tutor.db`). Puerto 3000. Variables: ver el encabezado de `app/main.py`.

## Créditos

El grokpet usa el motor de animación de [bloub](https://github.com/jeremy-prt/bloub) (MIT © 2026 Jérémy Perret),
ver `app/static/BLOUB-LICENSE.txt`.
