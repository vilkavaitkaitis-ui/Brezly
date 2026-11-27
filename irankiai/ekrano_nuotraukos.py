"""Tikros Brėžly lango ekrano nuotraukos svetainei (svetaine/vaizdai/*.webp).

Paleidžia Brėžly be AutoCAD - programos pačios imitacijos režimu („gerai“) -
ir per Playwright nufotografuoja: pamokos žingsnį po patikrinimo, praktiką ir spintą.
Apatinė būsenos juosta (rodo „Imitacija.dwg“) nukerpama.

  pip install playwright pillow && playwright install chromium
  python irankiai/ekrano_nuotraukos.py
"""
import os
import sys
import threading
import time

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUR = os.path.join(SAKNIS, "svetaine", "vaizdai")
sys.path.insert(0, SAKNIS)
os.chdir(SAKNIS)
os.environ["BREZLY_BE_LANGO"] = "1"


def main():
    import tempfile
    os.environ["HOME"] = os.environ["USERPROFILE"] = tempfile.mkdtemp()     # švarus progresas
    import brezly
    from PIL import Image
    from playwright.sync_api import sync_playwright
    brezly.KUREJAS["imitacija"] = "gerai"
    threading.Thread(target=lambda: brezly.P.main(brezly.BrezlyTvarkykle, 8799), daemon=True).start()
    time.sleep(2)
    url = "http://127.0.0.1:8799/"
    tvarka = "sg('vedlys','1');sg('cadet_turas','1');try{uzdarytiLangeli()}catch(e){};Gidas.slepti();"
    os.makedirs(KUR, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
        pg.goto(url); pg.wait_for_timeout(2500); pg.evaluate(tvarka)

        def foto(vardas):
            pg.wait_for_timeout(400)
            laik = os.path.join(KUR, vardas + ".png")
            pg.screenshot(path=laik, clip={"x": 0, "y": 0, "width": 1280, "height": 756})
            Image.open(laik).convert("RGB").save(os.path.join(KUR, vardas + ".webp"), quality=82, method=6)
            os.remove(laik)

        pg.evaluate("pradeti(0)"); pg.wait_for_timeout(1200); pg.evaluate(tvarka + "document.querySelector('main').scrollTop=0")
        pg.click("#tikrinti", force=True); pg.wait_for_timeout(2400)
        pg.evaluate("Gidas.slepti();document.querySelector('main').scrollTop=0;document.querySelectorAll('.pranesimas,#pranesimas').forEach(e=>e.remove())")
        foto("pamoka")
        pg.evaluate("rodytiPraktika()"); pg.wait_for_timeout(1500); pg.evaluate(tvarka)
        foto("praktika")
        pg.evaluate("rodytiSpinta()"); pg.wait_for_timeout(1500); pg.evaluate(tvarka)
        foto("spinta")
        b.close()
    print("Nuotraukos:", ", ".join(sorted(os.listdir(KUR))))


if __name__ == "__main__":
    main()
