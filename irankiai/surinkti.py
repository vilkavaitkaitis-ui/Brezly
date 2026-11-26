"""
Brėžly surinkimas - vienas failų sąrašas ir GitHub Actions, ir SUKURTI_DIEGIMA.bat.

  python irankiai/surinkti.py exe    - PyInstaller: dist/Brezly/Brezly.exe (reikia Windows, pyinstaller, pywin32)
  python irankiai/surinkti.py zip    - isvestis/Brezly_programa.zip (atnaujinimas be .exe) ir Brezly.lsp/.txt

Naujas failas, kurio reikia programai veikti, įrašomas tik čia (DUOMENYS arba MODULIAI).
"""

import os
import shutil
import subprocess
import sys
import zipfile

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISVESTIS = os.path.join(SAKNIS, "isvestis")

# Failai šalia programos (sąsaja, turinys). Aplankas praktika/ - visas.
DUOMENYS = ["brezly.html", "brezly.css", "brezly.js", "brezly.ico", "pamokos.json", "pamokos_en.json", "sasaja_en.json", "naujienos.json", "mokymas.js", "zinynas.json", "issukiai.json"]
APLANKAI = ["praktika", "sriftai", "paveiksleliai"]
# Įrašomi tik GitHub surinkime (versija ir atnaujinimų adresas)
NEBUTINI = ["versija.txt", "atnaujinimai_url.txt"]
# Python moduliai (.exe juos randa pats; ZIP atnaujinimui reikia išvardyti)
MODULIAI = ["brezly.py", "serveris.py", "branduolys.py", "pamokos.py", "praktika.py", "kalba.py", "vertimas.py", "issukiai.py"]


def _kelias(v):
    return os.path.join(SAKNIS, v)


def exe():
    duomenys = DUOMENYS + APLANKAI + [v for v in NEBUTINI if os.path.exists(_kelias(v))]
    sep = ";" if os.name == "nt" else ":"
    kom = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "Brezly",
           "--icon", "brezly.ico", "--contents-directory", ".", "--hidden-import", "win32timezone"]
    for v in duomenys:
        kom += ["--add-data", f"{v}{sep}{v if os.path.isdir(_kelias(v)) else '.'}"]
    kom.append("brezly.py")
    print(" ".join(kom), flush=True)
    subprocess.run(kom, cwd=SAKNIS, check=True)


def zip_():
    os.makedirs(ISVESTIS, exist_ok=True)
    kelias = os.path.join(ISVESTIS, "Brezly_programa.zip")
    # Senesnės versijos išskleidžia tik failus šaknyje ir praktika/<failas> (nuo 1.0.2 - ir sriftai/<failas>,
    # nuo 1.1 - paveiksleliai/[en/]<failas>); kitų katalogų nedėti. Be šriftų sąsaja veikia su Segoe UI,
    # be paveikslėlių - žingsnis rodomas be jų.
    with zipfile.ZipFile(kelias, "w", zipfile.ZIP_DEFLATED) as z:
        for v in MODULIAI + DUOMENYS + [v for v in NEBUTINI if os.path.exists(_kelias(v))]:
            z.write(_kelias(v), v)
        for ap in APLANKAI:
            for sakn, _, vardai in sorted(os.walk(_kelias(ap))):
                for v in sorted(vardai):
                    rel = os.path.relpath(os.path.join(sakn, v), SAKNIS).replace(os.sep, "/")
                    z.write(os.path.join(sakn, v), rel)
    print("Sukurta:", os.path.relpath(kelias, SAKNIS))
    lsp = _kelias(os.path.join("lisp", "Brezly.lsp"))
    if os.path.exists(lsp):
        shutil.copyfile(lsp, os.path.join(ISVESTIS, "Brezly.lsp"))
        shutil.copyfile(lsp, os.path.join(ISVESTIS, "Brezly.txt"))


def patikrinti():
    """Ar visi išvardyti failai yra (paleidžiama testuose)."""
    truksta = [v for v in MODULIAI + DUOMENYS + APLANKAI if not os.path.exists(_kelias(v))]
    if truksta:
        raise FileNotFoundError("Trūksta: " + ", ".join(truksta))


if __name__ == "__main__":
    veiksmas = sys.argv[1] if len(sys.argv) > 1 else ""
    {"exe": exe, "zip": zip_, "patikrinti": patikrinti}.get(veiksmas, lambda: sys.exit(__doc__))()
