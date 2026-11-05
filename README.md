# Mi Tutor (learn)

La app de estudio de Leo: **lecciones** paso a paso (una por misión), misiones por sesión, hojas para imprimir,
**tarjetas de repaso espaciado (FSRS)**, pantalla en vivo, progreso por curso y una lista de **mejoras**, organizado en ramas
(área › serie › curso › módulo › misión).

- **Lecciones:** camino por módulos; cada lección va explicación con ejemplo resuelto → pasos *predice* (hay que contestar
  para avanzar). Al terminarla, sus tarjetas entran al mazo. Se escriben con la skill `ingestar` (repo AI Engineer Courses).
  Las imágenes viven en `DATA_DIR/imagenes/<curso>/` y se sirven en `/imagenes/...` solo con sesión.
- **Mejoras:** errores y propuestas de Leo o del tutor (nueva / aceptada / hecha / descartada).
- **Tiempo:** calendario por mes y semana (tabla `tiempo`), tiempo hábil (semana tipo + excepciones) y predicción de fin
  por curso y total (`app/tiempo.py`: ritmo real con rango del 80 % contra el tiempo hábil). Las lecciones y tarjetas
  se registran solas con un ping cada 30 s mientras Leo está activo; las misiones, el tutor por MCP (`iniciar_sesion`,
  `terminar_sesion`, `registrar_sesion`, `editar_sesion`, `ver_tiempo`, `guardar_tiempo_habil`).
- **Imagen del plan de hoy** (`app/imagen.py`, Pillow + Nunito OFL en `app/static/fuentes/`): el bot la manda en el aviso
  de la mañana y con `/hoy`; se ve en `/api/tiempo/plan.png`.
- `tools/tutor_mcp.py`: extrae imágenes de notebooks, las sube y llama herramientas del MCP desde archivos JSON.

- **Web:** `/app/` (login con link mágico de Telegram o `ADMIN_PASSWORD`).
- **MCP para Claude Code:** `/mcp` (Streamable HTTP, `Authorization: Bearer $MCP_TOKEN`). Claude es el tutor: lee el curso,
  muestra cosas en vivo, enseña desde las lecciones y guarda datos, hojas, tarjetas, lecciones y mejoras. La app no lleva
  ningún modelo.
- **Bot de Telegram:** aviso diario (`AVISO_HORA`, 08:00) con las tarjetas del día y un link directo; segundo aviso
  (`RECORDATORIO_HORA`, 19:00) si no has repasado. Comandos: `/hoy` (plan de hoy como imagen), `/tarjetas`, `/tiempo`, `/link`. Solo responde a `TELEGRAM_CHAT_ID`.

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
