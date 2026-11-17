"""
Brėžly Pilotas - langas. Įrašai, ką nori nubraižyti, žodžiais arba komandomis,
spaudi "Braižyti" (arba Ctrl+Enter) - programa padaro AutoCAD'e.

Paleidimas: du kartus spausk LANGAS.bat (arba: pythonw langas.py)
"""

import os
import sys
import traceback

os.chdir(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)))


def rodyti_klaida(antraste):
    """Kai paleista be konsolės (pythonw) - klaidą parodo lange ir įrašo į klaida.txt."""
    tekstas = traceback.format_exc()
    try:
        with open("klaida.txt", "w", encoding="utf-8") as f:
            f.write(tekstas)
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"{antraste}\n\n{tekstas[-900:]}\n\n(Išsaugota klaida.txt)",
                                         "Brėžly Pilotas - klaida", 0x10)
    except Exception:
        print(tekstas)
    sys.exit(1)


try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext
    import branduolys as A
    import kalba
except Exception:
    rodyti_klaida("Nepavyko paleisti programos. Ar įdiegti Python, pywin32 ir tkinter?")

SPALVOS = {
    "fonas": "#f4f5f7", "kortele": "#ffffff", "tekstas": "#1f2328", "pilka": "#6b7280",
    "melyna": "#2563eb", "melyna_tamsi": "#1d4ed8", "zalia": "#15803d", "raudona": "#b91c1c",
    "geltona": "#a16207", "zurnalas": "#0f172a", "zurnalo_tekstas": "#e2e8f0",
}
SRIFTAS = ("Segoe UI", 10)
MONO = ("Consolas", 10)


class Zurnalas:
    """Nukreipia print() į lango žurnalą."""
    def __init__(self, langas):
        self.langas = langas

    def write(self, tekstas):
        self.langas.rasyti(tekstas)

    def flush(self):
        pass


class Langas:
    def __init__(self, root):
        self.root = root
        self.b = None
        self.kalba = kalba.Kalba(A.KOMANDOS.keys(), virsus=self._virsus,
                                 ribos=lambda: self.b.ribos() if self.b else None)
        root.title(f"Brėžly Pilotas {A.VERSIJA}")
        root.geometry("1050x700")
        root.minsize(800, 550)
        root.configure(bg=SPALVOS["fonas"])
        self._sukurti()
        sys.stdout = Zurnalas(self)
        root.after(200, self.prisijungti)

    # ---------- išdėstymas ----------
    def _mygtukas(self, tevas, tekstas, komanda, pagrindinis=False):
        spalva = SPALVOS["melyna"] if pagrindinis else SPALVOS["kortele"]
        tekst_sp = "white" if pagrindinis else SPALVOS["tekstas"]
        m = tk.Button(tevas, text=tekstas, command=komanda, font=(SRIFTAS[0], 10, "bold" if pagrindinis else "normal"),
                      bg=spalva, fg=tekst_sp, activebackground=SPALVOS["melyna_tamsi"] if pagrindinis else "#e5e7eb",
                      activeforeground=tekst_sp, relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
                      highlightthickness=1, highlightbackground="#d1d5db")
        return m

    def _sukurti(self):
        r = self.root
        # Viršus
        virsus = tk.Frame(r, bg=SPALVOS["fonas"])
        virsus.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(virsus, text="Brėžly Pilotas", font=(SRIFTAS[0], 16, "bold"),
                 bg=SPALVOS["fonas"], fg=SPALVOS["tekstas"]).pack(side="left")
        self.busena = tk.Label(virsus, text="● Jungiamasi prie AutoCAD...", font=SRIFTAS,
                               bg=SPALVOS["fonas"], fg=SPALVOS["geltona"])
        self.busena.pack(side="left", padx=16)
        self._mygtukas(virsus, "Prisijungti iš naujo", self.prisijungti).pack(side="right")

        pagrindas = tk.PanedWindow(r, orient="horizontal", bg=SPALVOS["fonas"], sashwidth=8, bd=0)
        pagrindas.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Kairė: įvedimas
        kaire = tk.Frame(pagrindas, bg=SPALVOS["fonas"])
        tk.Label(kaire, text="Ką nubraižyti? Po vieną veiksmą eilutėje - žodžiais arba komandomis.",
                 font=SRIFTAS, bg=SPALVOS["fonas"], fg=SPALVOS["pilka"], anchor="w").pack(fill="x")
        self.ivestis = scrolledtext.ScrolledText(kaire, font=(MONO[0], 11), wrap="word", undo=True,
                                                 relief="flat", bd=0, padx=10, pady=8,
                                                 highlightthickness=1, highlightbackground="#d1d5db")
        self.ivestis.pack(fill="both", expand=True, pady=(4, 8))
        self.ivestis.insert("1.0", kalba.PAVYZDZIAI)
        self.ivestis.bind("<Control-Return>", lambda e: (self.braizyti(), "break")[1])

        eil1 = tk.Frame(kaire, bg=SPALVOS["fonas"])
        eil1.pack(fill="x")
        self._mygtukas(eil1, "▶  Braižyti  (Ctrl+Enter)", self.braizyti, True).pack(side="left")
        self._mygtukas(eil1, "Tik parodyti komandas", self.perziura).pack(side="left", padx=6)
        self._mygtukas(eil1, "Išvalyti laukelį", lambda: self.ivestis.delete("1.0", "end")).pack(side="left")

        eil2 = tk.Frame(kaire, bg=SPALVOS["fonas"])
        eil2.pack(fill="x", pady=(6, 0))
        self._mygtukas(eil2, "↶ Atšaukti", lambda: self.vykdyti_viena("atsaukti")).pack(side="left")
        self._mygtukas(eil2, "Išvalyti brėžinį", lambda: self.vykdyti_viena("isvalyti")).pack(side="left", padx=6)
        self._mygtukas(eil2, "Atidaryti .txt", self.atidaryti_faila).pack(side="left")
        self._mygtukas(eil2, "Išsaugoti .txt", self.issaugoti_faila).pack(side="left", padx=6)
        self._mygtukas(eil2, "Nuotrauka → AI", self.nuotrauka).pack(side="left")

        self.viskas_ai = tk.BooleanVar(value=False)
        self.ai_zyme = tk.Checkbutton(kaire, text="Siųsti viską AI (reikia API rakto api_raktas.txt)",
                                      variable=self.viskas_ai, font=SRIFTAS, bg=SPALVOS["fonas"],
                                      fg=SPALVOS["tekstas"], activebackground=SPALVOS["fonas"],
                                      selectcolor=SPALVOS["kortele"])
        self.ai_zyme.pack(anchor="w", pady=(6, 0))
        pagrindas.add(kaire, minsize=420, stretch="always")

        # Dešinė: pavyzdžiai + žurnalas
        desine = tk.Frame(pagrindas, bg=SPALVOS["fonas"])
        tk.Label(desine, text="Pavyzdžiai (spausk - įrašys į laukelį)", font=SRIFTAS,
                 bg=SPALVOS["fonas"], fg=SPALVOS["pilka"], anchor="w").pack(fill="x")
        pv = tk.Frame(desine, bg=SPALVOS["fonas"])
        pv.pack(fill="x", pady=(4, 8))
        for pavadinimas, tekstas in [("Detalė iš brėžinio", kalba.PAVYZDZIAI_BREZINYS),
                                     ("Laikiklis su arka", kalba.PAVYZDZIAI_LAIKIKLIS),
                                     ("Stovas su šešiakampiu", kalba.PAVYZDZIAI_STOVAS),
                                     ("3D detalė", kalba.PAVYZDZIAI), ("Elektrinė schema", kalba.PAVYZDZIAI_SCHEMA),
                                     ("2D figūros", kalba.PAVYZDZIAI_2D)]:
            self._mygtukas(pv, pavadinimas, lambda t=tekstas: self._ideti(t)).pack(side="left", padx=(0, 6))
        self._mygtukas(pv, "Visos komandos", lambda: print(A.pagalbos_tekstas())).pack(side="left")

        tk.Label(desine, text="Žurnalas", font=SRIFTAS, bg=SPALVOS["fonas"],
                 fg=SPALVOS["pilka"], anchor="w").pack(fill="x")
        self.zurnalas = scrolledtext.ScrolledText(desine, font=MONO, wrap="word", state="disabled",
                                                  bg=SPALVOS["zurnalas"], fg=SPALVOS["zurnalo_tekstas"],
                                                  relief="flat", bd=0, padx=10, pady=8)
        self.zurnalas.pack(fill="both", expand=True, pady=(4, 0))
        self.zurnalas.tag_configure("ok", foreground="#86efac")
        self.zurnalas.tag_configure("klaida", foreground="#fca5a5")
        self.zurnalas.tag_configure("kom", foreground="#93c5fd")
        self.zurnalas.tag_configure("antr", foreground="#fde68a")
        pagrindas.add(desine, minsize=360, stretch="always")

    # ---------- žurnalas ----------
    def rasyti(self, tekstas, zyme=None):
        if zyme is None:
            if "Praleista" in tekstas or "Klaida" in tekstas or "Nesupratau" in tekstas:
                zyme = "klaida"
            elif "klaidų: 0" in tekstas:
                zyme = "ok"
        self.zurnalas.configure(state="normal")
        self.zurnalas.insert("end", tekstas, zyme)
        self.zurnalas.see("end")
        self.zurnalas.configure(state="disabled")
        self.root.update_idletasks()

    def _ideti(self, tekstas):
        self.ivestis.delete("1.0", "end")
        self.ivestis.insert("1.0", tekstas)

    # ---------- AutoCAD ----------
    def prisijungti(self):
        self.busena.configure(text="● Jungiamasi prie AutoCAD...", fg=SPALVOS["geltona"])
        self.root.update()
        try:
            acad = A.prisijungti()
            self.b = A.Braizytojas(acad)
            self.b.patvirtinti = lambda klausimas: messagebox.askyesno("Patvirtinti", klausimas)
            pavad = A.kartoti(lambda: acad.ActiveDocument.Name)
            self.busena.configure(text=f"● Prisijungta · {pavad}", fg=SPALVOS["zalia"])
        except Exception as e:
            self.b = None
            self.busena.configure(text="● Neprisijungta", fg=SPALVOS["raudona"])
            print(f"Klaida jungiantis: {e}\n")
        rakto = A.gauti_rakta() is not None
        self.ai_zyme.configure(state="normal" if rakto else "disabled")

    def _virsus(self):
        return self.b.virsus() if self.b else None

    def _uzimta(self, taip):
        self.root.configure(cursor="watch" if taip else "")
        self.root.update()

    # ---------- veiksmai ----------
    def _versti(self):
        tekstas = self.ivestis.get("1.0", "end").strip()
        if not tekstas:
            return [], []
        return self.kalba.versti(tekstas)

    def perziura(self):
        komandos, nesuprasta = self._versti()
        self.rasyti("\n=== Programa supras taip ===\n", "antr")
        for k in komandos:
            self.rasyti(f"  {k}\n", "kom")
        for n in nesuprasta:
            self.rasyti(f"  Nesupratau: {n}\n", "klaida")

    def braizyti(self):
        if not self.b:
            messagebox.showwarning("AutoCAD", "Neprisijungta prie AutoCAD. Atsidaryk AutoCAD ir spausk "
                                              "„Prisijungti iš naujo“.")
            return
        tekstas = self.ivestis.get("1.0", "end").strip()
        if not tekstas:
            return
        self._uzimta(True)
        try:
            if self.viskas_ai.get():
                self.rasyti("\n=== Siunčiu AI ===\n", "antr")
                A.kartoti(lambda: self.b.vykdyti("ai " + " ".join(tekstas.split())))
                return
            # Kiekvienas sakinys verčiamas ir vykdomas iš eilės - tada žinomas tikras detalės aukštis
            self.rasyti("\n=== Braižau ===\n", "antr")
            nesuprasta, gerai, klaidos = [], 0, 0
            for sakinys in kalba.skaidyti_sakinius(tekstas):
                try:
                    komandos = self.kalba.sakinys(sakinys)
                except Exception:
                    komandos = None
                if not komandos:
                    nesuprasta.append(sakinys)
                    continue
                for k in komandos:
                    self.rasyti(f"  {k}\n", "kom")
                    try:
                        self.b.vykdyti_saugiai(k, "failas")
                        gerai += 1
                    except Exception as e:
                        klaidos += 1
                        self.rasyti(f"  Praleista '{k}': {e}\n", "klaida")
            self.b.palaukti()
            try:
                A.kartoti(self.b.acad.ZoomExtents)
            except Exception:
                pass
            self.rasyti(f"Įvykdyta: {gerai}, klaidų: {klaidos}\n")
            if nesuprasta:
                if A.gauti_rakta():
                    self.rasyti("Nesuprastus sakinius siunčiu AI:\n", "antr")
                    for n in nesuprasta:
                        self.rasyti(f"  {n}\n", "kom")
                    self.b.vykdyti_saugiai("ai " + ". ".join(nesuprasta))
                else:
                    for n in nesuprasta:
                        self.rasyti(f"Nesupratau: {n}\n", "klaida")
                    self.rasyti("Patarimas: parašyk paprasčiau (žr. pavyzdžius) arba įklijuok API raktą "
                                "į api_raktas.txt - tada ko nesupras, padarys AI.\n")
        except Exception as e:
            self.rasyti(f"Klaida: {e}\n", "klaida")
        finally:
            self._uzimta(False)

    def vykdyti_viena(self, komanda):
        if not self.b:
            return
        self._uzimta(True)
        try:
            self.b.vykdyti_saugiai(komanda)
        except Exception as e:
            self.rasyti(f"Klaida: {e}\n", "klaida")
        finally:
            self._uzimta(False)

    def atidaryti_faila(self):
        kelias = filedialog.askopenfilename(title="Komandų failas", initialdir=os.getcwd(),
                                            filetypes=[("Tekstas", "*.txt"), ("Visi", "*.*")])
        if kelias:
            with open(kelias, encoding="utf-8") as f:
                self._ideti(f.read())
            self.rasyti(f"Įkeltas failas: {os.path.basename(kelias)} - spausk Braižyti.\n")

    def issaugoti_faila(self):
        kelias = filedialog.asksaveasfilename(title="Išsaugoti", initialdir=os.getcwd(),
                                              defaultextension=".txt", filetypes=[("Tekstas", "*.txt")])
        if kelias:
            with open(kelias, "w", encoding="utf-8") as f:
                f.write(self.ivestis.get("1.0", "end"))
            self.rasyti(f"Išsaugota: {kelias}\n", "ok")

    def nuotrauka(self):
        if not self.b:
            return
        if not A.gauti_rakta():
            messagebox.showinfo("AI", "Nuotraukoms reikia API rakto.\n\nĮklijuok jį į failą api_raktas.txt "
                                      "programos aplanke (žr. INSTRUKCIJA.txt).")
            return
        kelias = filedialog.askopenfilename(title="Nuotrauka arba brėžinys",
                                            filetypes=[("Paveikslėliai", "*.png *.jpg *.jpeg *.webp *.gif")])
        if not kelias:
            return
        pastaba = self.ivestis.get("1.0", "end").strip()
        if pastaba == kalba.PAVYZDZIAI.strip():
            pastaba = ""
        self._uzimta(True)
        try:
            self.rasyti(f"\n=== Siunčiu AI: {os.path.basename(kelias)} ===\n", "antr")
            self.b.vykdyti(f'foto "{kelias}" {" ".join(pastaba.split())}')
        except Exception as e:
            self.rasyti(f"Klaida: {e}\n", "klaida")
        finally:
            self._uzimta(False)


def uzsklanda(root):
    """Paleidimo užsklanda lange: talismanas ir pavadinimas ~2 sekundes."""
    try:
        import zenklas
    except Exception:
        return
    root.withdraw()
    u = tk.Toplevel(root)
    u.overrideredirect(True)
    u.configure(bg="#0f172a")
    spalvos = {zenklas.GELTONA: "#facc15", zenklas.ZYDRA: "#22d3ee", zenklas.MELYNA: "#60a5fa",
               zenklas.PILKA: "#64748b"}
    t = tk.Text(u, bg="#0f172a", bd=0, highlightthickness=0, font=("Consolas", 11),
                width=60, height=len(zenklas.ROBOTAS) + len(zenklas.UZRASAS) + 5, padx=24, pady=16)
    t.pack()
    for i, (sp, eil) in enumerate(zenklas.ROBOTAS):
        t.tag_configure(f"r{i}", foreground=spalvos.get(sp, "#e2e8f0"))
        t.insert("end", eil.replace("{A}", zenklas.AKYS_ATMERKTOS) + "\n", f"r{i}")
    t.tag_configure("u", foreground="#4ade80")
    t.insert("end", "\n")
    for eil in zenklas.UZRASAS:
        t.insert("end", eil + "\n", "u")
    t.tag_configure("v", foreground="#f8fafc", font=("Consolas", 12, "bold"))
    t.insert("end", "\n" + " " * 24 + f"v{A.VERSIJA.split()[0]}", "v")
    t.configure(state="disabled")
    u.update_idletasks()
    x = (u.winfo_screenwidth() - u.winfo_reqwidth()) // 2
    y = (u.winfo_screenheight() - u.winfo_reqheight()) // 2
    u.geometry(f"+{x}+{y}")
    u.bind("<Button-1>", lambda e: u.destroy())
    u.after(2200, u.destroy)
    root.wait_window(u)
    root.deiconify()


def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)     # ryškus tekstas Windows'e
    except Exception:
        pass
    root = tk.Tk()
    uzsklanda(root)
    Langas(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        rodyti_klaida("Programa sustojo dėl klaidos.")
