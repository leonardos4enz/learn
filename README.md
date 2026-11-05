# Mi Tutor (learn)

La app de estudio de Leo: misiones por sesión, hojas para imprimir, **tarjetas de repaso espaciado (FSRS)**, pantalla en vivo
y progreso por curso, organizado en ramas (área › serie › curso › módulo › misión).

- **Web:** `/app/` (login con link mágico de Telegram o `ADMIN_PASSWORD`).
- **MCP para Claude Code:** `/mcp` (Streamable HTTP, `Authorization: Bearer $MCP_TOKEN`). Claude es el tutor: lee el curso,
  muestra cosas en vivo y guarda datos, hojas y tarjetas. La app no lleva ningún modelo.
- **Bot de Telegram:** aviso diario (`AVISO_HORA`, 08:00) con las tarjetas del día y un link directo; segundo aviso
  (`RECORDATORIO_HORA`, 19:00) si no has repasado. Comandos: `/hoy`, `/tarjetas`, `/link`. Solo responde a `TELEGRAM_CHAT_ID`.

## Por qué está hecha así

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
