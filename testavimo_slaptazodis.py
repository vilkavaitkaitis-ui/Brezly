"""Nustato (pakeičia) Brėžly testavimo įrankių slaptažodį.

Paleisk: SLAPTAZODIS.bat (arba python testavimo_slaptazodis.py)
Slaptažodis nesaugomas - testavimas.json faile lieka tik jo „maiša“ (PBKDF2), iš kurios atkurti neįmanoma.
Ištrynus testavimas.json, testavimo įrankiai programoje visai dingsta (naudotojų versijai).
"""
import getpass
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("BREZLY_BE_LANGO", "1")
import brezly  # noqa: E402

if __name__ == "__main__":
    print("Brėžly testavimo įrankių slaptažodis\n")
    s1 = getpass.getpass("Naujas slaptažodis (bent 8 simboliai, nesimato rašant): ")
    if len(s1) < 8:
        sys.exit("Per trumpas - bent 8 simboliai.")
    if getpass.getpass("Pakartok: ") != s1:
        sys.exit("Nesutampa - bandyk dar kartą.")
    brezly.nustatyti_slaptazodi(s1)
    print("\nOK. Slaptažodis pakeistas (testavimas.json).")
