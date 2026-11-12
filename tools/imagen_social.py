"""Genera docs/img/social.png (1280×640): la imagen que GitHub muestra al compartir el link del repo.

Uso: .venv/Scripts/python tools/imagen_social.py   (después súbela en GitHub → Settings → Social preview)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "app" / "static" / "fuentes" / "Nunito.ttf"
W, H = 1280, 640
FONDO, TINTA, SUAVE, ACENTO, RUTA = "#F5F6F7", "#16191D", "#59636E", "#0B7D67", "#6A4BE0"


def fuente(px, peso=800):
    f = ImageFont.truetype(str(FUENTE), px)
    try:  # Nunito es variable: elige el peso
        f.set_variation_by_axes([peso])
    except Exception:
        pass
    return f


def esquinas(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, *im.size), r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


lienzo = Image.new("RGB", (W, H), FONDO)
d = ImageDraw.Draw(lienzo)

# Captura del grafo, a la derecha, con sombra y esquinas redondeadas
cap = Image.open(RAIZ / "docs" / "img" / "mis-estudios.png").convert("RGB")
cap = cap.crop((250, 130, 1400, 1050))                      # solo el contenido, sin el menú
cap.thumbnail((700, 560))
cap = esquinas(cap, 18)
x, y = W - cap.width - 40, (H - cap.height) // 2
sombra = Image.new("RGBA", (cap.width + 60, cap.height + 60), (0, 0, 0, 0))
ImageDraw.Draw(sombra).rounded_rectangle((30, 34, cap.width + 30, cap.height + 34), 18, fill=(0, 0, 0, 60))
lienzo.paste(sombra.filter(ImageFilter.GaussianBlur(14)), (x - 30, y - 30), sombra.filter(ImageFilter.GaussianBlur(14)))
lienzo.paste(cap, (x, y), cap)

# Texto a la izquierda
icono = Image.open(RAIZ / "app" / "static" / "icono.png").convert("RGBA").resize((96, 96), Image.LANCZOS)
lienzo.paste(icono, (64, 92), icono)
d.text((64, 210), "Mi Tutor", font=fuente(84), fill=TINTA)
lineas = ["Claude como tutor: lecciones", "paso a paso, repaso espaciado", "y un plan de qué toca hoy."]
for i, t in enumerate(lineas):
    d.text((66, 318 + i * 40), t, font=fuente(30, 600), fill=SUAVE)
pildora, fp = "92 lecciones en español", fuente(26, 800)
ancho = d.textlength(pildora, font=fp)
d.rounded_rectangle((64, 470, 64 + ancho + 48, 470 + 52), 26, fill=ACENTO)
d.text((88, 480), pildora, font=fp, fill="#FFFFFF")
d.text((66, 548), "LangChain · LangGraph · Deep Agents · Ruta LCAE", font=fuente(21, 700), fill=RUTA)

salida = RAIZ / "docs" / "img" / "social.png"
lienzo.save(salida, optimize=True)
print(salida, f"{salida.stat().st_size // 1024} KB")
