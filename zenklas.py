"""
Paleidimo užsklanda: originalus talismanas - robotas braižytojas su žaibais ir skriestuvu,
po jo užrašas "Brėžly" ir versija. Bet kuris klavišas - praleisti.
"""

import os
import sys
import time

# ANSI spalvos (Windows 10+ konsolėje įsijungia per os.system(""))
R = "\033[0m"
GELTONA = "\033[93m"
ZYDRA = "\033[96m"
MELYNA = "\033[94m"
ZALIA = "\033[92m"
PILKA = "\033[90m"
BALTA = "\033[97m"
RAUDONA = "\033[91m"

ROBOTAS = [
    (GELTONA, r"          \   |   /"),
    (GELTONA, r"        --    *    --"),
    (GELTONA, r"          /   |   \ "),
    (ZYDRA,   r"              |"),
    (ZYDRA,   r"      .-------+-------."),
    (ZYDRA,   r"      |   _       _   |"),
    (ZYDRA,   r"      |  {A}     {A}  |"),
    (ZYDRA,   r"      |       ^       |"),
    (ZYDRA,   r"      |   \_______/   |"),
    (ZYDRA,   r"      '---.-------.---'"),
    (ZYDRA,   r"          |       |"),
    (MELYNA,  r"     .----'-------'----.          o"),
    (MELYNA,  r"     |  []         []  |---------/ \ "),
    (MELYNA,  r"     |       ==        |        /   \ "),
    (MELYNA,  r"     '-----------------'       /     \ "),
    (PILKA,   r"  ========================================"),
]
# akys: atmerktos / užmerktos (mirktelėjimas)
AKYS_ATMERKTOS = "(o)"
AKYS_UZMERKTOS = "(-)"

UZRASAS = [
    r" ____             .     \/    _         ",
    r"| __ )   _ __    ___   ____  | |  _   _ ",
    r"|  _ \  | '__|  / _ \ |_  /  | | | | | |",
    r"| |_) | | |    |  __/  / /   | | | |_| |",
    r"|____/  |_|     \___| /___|  |_|  \__, |",
    r"                                  |___/ ",
]


def _paspausta():
    """Ar paspaustas klavišas (tik Windows). Klavišą nuskaito, kad nepatektų į meniu."""
    try:
        import msvcrt
        if msvcrt.kbhit():
            msvcrt.getwch()
            return True
    except Exception:
        pass
    return False


def _laukti(sek):
    pabaiga = time.time() + sek
    while time.time() < pabaiga:
        if _paspausta():
            return True
        time.sleep(0.02)
    return False


def _valyti():
    os.system("cls" if os.name == "nt" else "clear")


def _robotas(akys, zaibas_sviecia=True):
    eilutes = []
    for i, (spalva, tekstas) in enumerate(ROBOTAS):
        tekstas = tekstas.replace("{A}", akys)
        if i < 3:
            spalva = GELTONA if zaibas_sviecia else PILKA
        eilutes.append(f"{spalva}{tekstas}{R}")
    return eilutes


def rodyti(versija="1.4"):
    if os.environ.get("BREZLY_BE_UZSKLANDOS"):
        return
    if os.name == "nt":
        os.system("")                     # įjungia ANSI spalvas Windows konsolėje
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _valyti()
    print()
    # 1. Robotas atsiranda eilutė po eilutės
    for eil in _robotas(AKYS_ATMERKTOS):
        print(eil)
        if _laukti(0.05):
            _valyti()
            return
    # 2. Žaibas sublyksi ir robotas mirkteli
    for zaibas, akys in ((False, AKYS_ATMERKTOS), (True, AKYS_UZMERKTOS), (False, AKYS_ATMERKTOS),
                         (True, AKYS_ATMERKTOS)):
        if _laukti(0.18):
            _valyti()
            return
        sys.stdout.write(f"\033[{len(ROBOTAS)}A")          # grįžti į roboto viršų
        for eil in _robotas(akys, zaibas):
            sys.stdout.write("\r" + eil + "\n")
        sys.stdout.flush()
    # 3. Užrašas
    print()
    for eil in UZRASAS:
        print(f"{ZALIA}{eil}{R}")
        if _laukti(0.06):
            _valyti()
            return
    print(f"\n{BALTA}{' ' * 22}v{versija}{R}   {PILKA}Brėžly Pilotas · braižo AutoCAD'e už tave{R}")
    print(f"\n{PILKA}{' ' * 14}(bet kuris klavišas - tęsti){R}")
    _laukti(2.5)
    _valyti()


if __name__ == "__main__":
    rodyti()
