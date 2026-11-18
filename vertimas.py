"""
Brėžly kalba: lietuvių (numatytoji) arba anglų.

Pranešimai kode rašomi abiem kalbomis vienoje vietoje:  tr("Neradau apskritimo.", "No circle found.")
Kalbą nustato sąsaja (/api/info?kalba=en) - viena programa, vienas naudotojas, todėl užtenka globalios reikšmės.
"""

KALBOS = ("lt", "en")
_DABAR = {"kalba": "lt"}


def nustatyti(kalba):
    _DABAR["kalba"] = kalba if kalba in KALBOS else "lt"
    return _DABAR["kalba"]


def kalba():
    return _DABAR["kalba"]


def tr(lt, en):
    """Tekstas dabartine kalba."""
    return en if _DABAR["kalba"] == "en" else lt
