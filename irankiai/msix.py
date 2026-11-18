"""
Brėžly MSIX paketas Microsoft Store'ui (ir bandymui be Store).

  python irankiai/msix.py                     -> isvestis/Brezly_Store.msix (iš dist/Brezly, reikia Windows SDK makeappx)
  python irankiai/msix.py --tik-aplankas      -> tik dist/msix/ (manifestas + ikonos + programa), be pakavimo

Tapatybė (Partner Center -> Produkto tapatybė / Product identity) - per aplinkos kintamuosius:
  MSIX_TAPATYBE        Package/Identity/Name, pvz. 12345Vardas.Brezly
  MSIX_LEIDEJAS        Package/Identity/Publisher, pvz. CN=ABCD1234-...
  MSIX_LEIDEJO_VARDAS  Package/Properties/PublisherDisplayName
Jei nenustatyta - bandomoji tapatybė (tinka įdiegti su bandomuoju sertifikatu, bet ne Store'ui).

Versija: VERSIJA (kaip GitHub surinkime), Store'ui - keturios dalys, paskutinė 0 (1.0.1 -> 1.0.1.0).
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(SAKNIS, "dist", "Brezly")
ISVESTIS = os.path.join(SAKNIS, "isvestis")
APLANKAS = os.path.join(SAKNIS, "dist", "msix")      # pakuojamas turinys (ne isvestis - ten tik galutiniai failai)

BANDOMOJI = {"tapatybe": "Brezly.Bandomasis", "leidejas": "CN=Brezly Bandomasis", "vardas": "Brėžly (bandomasis)"}

APRASAS = ("AutoCAD mokymosi programa inžinerijos studentams: braižai AutoCAD'e pats, "
           "o Brėžly veda žingsnis po žingsnio ir patikrina brėžinį. Nemokama.")

# (failas, plotis, aukštis) - Store reikalaujami dydžiai
IKONOS = [("StoreLogo.png", 50, 50), ("Square44x44Logo.png", 44, 44), ("Square150x150Logo.png", 150, 150),
          ("Wide310x150Logo.png", 310, 150), ("Square44x44Logo.targetsize-48_altform-unplated.png", 48, 48),
          ("Square44x44Logo.targetsize-256_altform-unplated.png", 256, 256)]


def tapatybe():
    t = {"tapatybe": os.environ.get("MSIX_TAPATYBE", "").strip() or BANDOMOJI["tapatybe"],
         "leidejas": os.environ.get("MSIX_LEIDEJAS", "").strip() or BANDOMOJI["leidejas"],
         "vardas": os.environ.get("MSIX_LEIDEJO_VARDAS", "").strip() or BANDOMOJI["vardas"]}
    if not re.fullmatch(r"[A-Za-z0-9.\-]{3,50}", t["tapatybe"]):
        raise SystemExit(f"MSIX_TAPATYBE netinka: {t['tapatybe']!r} (3-50 raidžių, skaičių, taškų, brūkšnelių)")
    if not t["leidejas"].startswith("CN="):
        raise SystemExit(f"MSIX_LEIDEJAS turi prasidėti CN= (dabar: {t['leidejas']!r})")
    return t


def versija4(v=None):
    """1.0.1 -> 1.0.1.0. Bandomajam surinkimui (0.0.0-bandymas) - naujausia iš naujienos.json."""
    v = (v if v is not None else os.environ.get("VERSIJA", "")).strip().lstrip("vV")
    if not re.fullmatch(r"\d+(\.\d+){0,2}", v):
        with open(os.path.join(SAKNIS, "naujienos.json"), encoding="utf-8") as f:
            v = json.load(f)["versijos"][0]["versija"]
    dalys = (v.split(".") + ["0", "0", "0"])[:3]
    if int(dalys[0]) == 0 and int(dalys[1]) == 0 and int(dalys[2]) == 0:
        dalys[2] = "1"                                       # Store nepriima 0.0.0.0
    return ".".join(str(int(d)) for d in dalys) + ".0"       # Store: paskutinė dalis visada 0


def manifestas(t, versija):
    kab = {'"': "&quot;"}
    vardas, leidejas, pav, apr = (escape(t["tapatybe"], kab), escape(t["leidejas"], kab),
                                  escape(t["vardas"]), escape(APRASAS, kab))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:uap3="http://schemas.microsoft.com/appx/manifest/uap/windows10/3"
  xmlns:desktop="http://schemas.microsoft.com/appx/manifest/desktop/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap uap3 desktop rescap">
  <Identity Name="{vardas}" Publisher="{leidejas}"
            Version="{versija}" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>Brėžly</DisplayName>
    <PublisherDisplayName>{pav}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <Description>{apr}</Description>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="lt-LT" />
    <Resource Language="en-US" />
  </Resources>
  <Applications>
    <Application Id="Brezly" Executable="Brezly.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="Brėžly" Description="{apr}"
        BackgroundColor="transparent"
        Square150x150Logo="Assets\\Square150x150Logo.png" Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" ShortName="Brėžly" />
      </uap:VisualElements>
      <Extensions>
        <uap3:Extension Category="windows.appExecutionAlias" Executable="Brezly.exe"
                        EntryPoint="Windows.FullTrustApplication">
          <uap3:AppExecutionAlias>
            <desktop:ExecutionAlias Alias="brezly.exe" />
          </uap3:AppExecutionAlias>
        </uap3:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""


def ikonos(kur):
    from PIL import Image
    os.makedirs(kur, exist_ok=True)
    with Image.open(os.path.join(SAKNIS, "brezly.ico")) as ico:
        ico.size = max(ico.info.get("sizes") or [ico.size])          # didžiausia ikona faile
        saltinis = ico.convert("RGBA")
    for vardas, w, h in IKONOS:
        kv = min(w, h) if w == h else int(h * 0.8)                   # plačiai plytelei - ikona per vidurį
        pav = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        mazas = saltinis.resize((kv, kv), Image.LANCZOS)
        pav.alpha_composite(mazas, ((w - kv) // 2, (h - kv) // 2))
        pav.save(os.path.join(kur, vardas))


def paruosti_aplanka():
    if not os.path.isfile(os.path.join(DIST, "Brezly.exe")):
        raise SystemExit("Nėra dist/Brezly/Brezly.exe - pirma: python irankiai/surinkti.py exe")
    if os.path.isdir(APLANKAS):
        shutil.rmtree(APLANKAS)
    shutil.copytree(DIST, APLANKAS, ignore=shutil.ignore_patterns("klaida.txt", "patikra.txt", "testavimas.json",
                                                                  "api_raktas.txt", "funkcijos.json"))
    for slaptas in ("testavimas.json", "api_raktas.txt"):
        assert not os.path.exists(os.path.join(APLANKAS, slaptas)), slaptas
    ikonos(os.path.join(APLANKAS, "Assets"))
    t, v = tapatybe(), versija4()
    with open(os.path.join(APLANKAS, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifestas(t, v))
    print(f"MSIX aplankas: {APLANKAS}\n  tapatybė: {t['tapatybe']}  leidėjas: {t['leidejas']}  versija: {v}"
          + ("  (BANDOMOJI - Store'ui nustatyk MSIX_TAPATYBE/MSIX_LEIDEJAS)" if t["tapatybe"] == BANDOMOJI["tapatybe"] else ""))
    return t, v


def makeappx():
    if os.environ.get("MAKEAPPX"):
        return os.environ["MAKEAPPX"]
    kandidatai = sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\10\bin\10.*\x64\makeappx.exe"))
    if not kandidatai:
        raise SystemExit("Nerastas makeappx.exe (Windows SDK). Nurodyk MAKEAPPX=kelias")
    return kandidatai[-1]


def main(argv):
    paruosti_aplanka()
    if "--tik-aplankas" in argv:
        return
    isvestis = os.path.join(ISVESTIS, "Brezly_Store.msix")
    r = subprocess.run([makeappx(), "pack", "/d", APLANKAS, "/p", isvestis, "/o"])
    if r.returncode:
        raise SystemExit(f"makeappx klaida ({r.returncode})")
    print(f"Sukurta: {isvestis}")


if __name__ == "__main__":
    main(sys.argv[1:])
