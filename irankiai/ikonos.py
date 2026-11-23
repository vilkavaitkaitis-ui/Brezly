"""Brėžly ikonos (1.3 Bauhaus): juodas kvadratas, raudonas apskritimas, geltonas kvadratas, mėlynas trikampis.
Sukuria brezly.ico (programa, diegimo programa, MSIX) ir app/icon-192.png, app/icon-512.png (programėlė).
Paleisti: python irankiai/ikonos.py"""
import os
from PIL import Image, ImageDraw

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JUODA, RAUDONA, GELTONA, MELYNA = (17, 17, 17, 255), (226, 54, 43, 255), (255, 196, 0, 255), (31, 79, 209, 255)


def zenklas(dydis, fonas=True):
    k = 4                                   # piešiam 4x didesnį ir sumažinam - lygūs kraštai
    d = dydis * k
    im = Image.new("RGBA", (d, d), JUODA if fonas else (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    p = d * 0.16                            # paraštė
    m = (d - 2 * p) / 30                    # ženklo vienetas (SVG viewBox 30)
    x = lambda v: p + v * m
    dr.ellipse([x(2), x(2), x(20), x(20)], fill=RAUDONA)
    dr.rectangle([x(14), x(14), x(28), x(28)], fill=GELTONA)
    dr.polygon([(x(2), x(28)), (x(14), x(28)), (x(2), x(16))], fill=MELYNA)
    return im.resize((dydis, dydis), Image.LANCZOS)


def main():
    zenklas(256).save(os.path.join(SAKNIS, "brezly.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    for n in (192, 512):
        zenklas(n).save(os.path.join(SAKNIS, "app", f"icon-{n}.png"))
    print("Ikonos: brezly.ico, app/icon-192.png, app/icon-512.png")


if __name__ == "__main__":
    main()
