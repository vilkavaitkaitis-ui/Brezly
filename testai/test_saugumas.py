"""1.5.1 saugumas: vietinio serverio „užkarda“ ir atnaujinimų apsauga.
Svetima svetainė (kitas Origin, kitas Host, be sesijos rakto, GET) nieko negali padaryti; Brėžly puslapis veikia."""
import http.client
import json
import os
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
import brezly as B          # noqa: E402
import serveris as P        # noqa: E402


class Uzkarda(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), B.BrezlyTvarkykle)
        cls.srv.daemon_threads = True
        cls.p = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def u(self, metodas, kelias, kunas=None, antrastes=None):
        c = http.client.HTTPConnection("127.0.0.1", self.p, timeout=10)
        a = {"Content-Type": "application/json", **(antrastes or {})}
        c.request(metodas, kelias, body=kunas, headers=a)
        r = c.getresponse()
        d = r.read()
        c.close()
        return r.status, dict(r.getheaders()), d

    def post(self, kelias, duom=None, **ant):
        return self.u("POST", kelias, json.dumps(duom or {}), ant)

    def test_brezly_puslapis_ir_raktas_veikia(self):
        st, h, html = self.u("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(b'<meta name="brezly-raktas" content="' + P.RAKTAS.encode() + b'">', html)
        self.assertEqual(h["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"])
        self.assertEqual(h["Cross-Origin-Resource-Policy"], "same-origin")
        st, _, d = self.post("/api/info", **{"X-Brezly-Raktas": P.RAKTAS, "Origin": f"http://127.0.0.1:{self.p}"})
        self.assertEqual(st, 200)
        self.assertTrue(json.loads(d)["ok"])

    def test_be_rakto_ar_netinkamas(self):
        for ant in ({}, {"X-Brezly-Raktas": "neteisingas"}, {"X-Brezly-Raktas": ""}):
            st, _, d = self.post("/api/progresas", {"S": {"xp": 0}}, **ant)
            self.assertEqual(st, 403, ant)
            self.assertFalse(json.loads(d)["ok"])

    def test_svetima_svetaine(self):
        for o in ("https://blogas.example", "null", f"http://127.0.0.1:{self.p + 1}"):
            st, _, _ = self.post("/api/progresas", {"S": {"xp": 0}}, **{"X-Brezly-Raktas": P.RAKTAS, "Origin": o})
            self.assertEqual(st, 403, o)

    def test_dns_rebinding(self):
        for h in ("blogas.example:%d" % self.p, "blogas.example", f"127.0.0.1:{self.p + 1}"):
            self.assertEqual(self.u("GET", "/", antrastes={"Host": h})[0], 403, h)
            self.assertEqual(self.u("GET", "/praktika/U1_Tarpine.svg", antrastes={"Host": h})[0], 403, h)
            self.assertEqual(self.post("/api/info", **{"Host": h, "X-Brezly-Raktas": P.RAKTAS})[0], 403, h)
        self.assertEqual(self.u("GET", "/", antrastes={"Host": f"localhost:{self.p}"})[0], 200)

    def test_api_tik_post(self):
        for k in ("/api/info", "/api/progresas", "/api/atnaujinti", "/api/perkrauti"):
            self.assertEqual(self.u("GET", k)[0], 405, k)

    def test_raktas_adrese_sendbeacon(self):
        st, _, d = self.u("POST", "/api/ping?r=" + P.RAKTAS, "{}", {"Content-Type": "text/plain;charset=UTF-8"})
        self.assertEqual(st, 200)

    def test_per_didele_uzklausa(self):
        c = http.client.HTTPConnection("127.0.0.1", self.p, timeout=10)
        c.putrequest("POST", "/api/ping")
        c.putheader("X-Brezly-Raktas", P.RAKTAS)
        c.putheader("Content-Length", str(P.MAKS_UZKLAUSA + 1))
        c.endheaders()
        self.assertEqual(c.getresponse().status, 413)
        c.close()

    def test_atmetimai_skaiciuojami(self):
        pries = P.ATMESTA["kiek"]
        self.post("/api/ping")
        self.assertEqual(P.ATMESTA["kiek"], pries + 1)
        self.assertIn("rakto", P.ATMESTA["paskutine"])

    def test_raktas_kas_kart_naujas_ir_ilgas(self):
        self.assertGreaterEqual(len(P.RAKTAS), 40)


class Atnaujinimai(unittest.TestCase):
    def setUp(self):
        self.senas = B.ATNAUJINIMU_URL
        B.ATNAUJINIMU_URL = "https://github.com/vilkavaitkaitis-ui/Brezly/releases/latest/download/atnaujinimai.json"

    def tearDown(self):
        B.ATNAUJINIMU_URL = self.senas

    def test_leidziama_tik_is_savo_releases(self):
        self.assertEqual(B._leistina_pradzia(), "https://github.com/vilkavaitkaitis-ui/Brezly/releases/download/")
        for url in ("https://blogas.example/Brezly_Setup.exe", "http://github.com/vilkavaitkaitis-ui/Brezly/releases/download/v1/x.exe",
                    "https://github.com/kitas/Brezly/releases/download/v1/x.exe", None):
            with self.assertRaises(ValueError, msg=url):
                B._atsisiusti(url, os.devnull, "a" * 64)

    def test_be_kontrolines_sumos_nediegiama(self):
        for h in ("", None, "123", "z" * 64):
            with self.assertRaises(ValueError, msg=h):
                B._atsisiusti("https://github.com/vilkavaitkaitis-ui/Brezly/releases/download/v1.5/Brezly_Setup.exe", os.devnull, h)


if __name__ == "__main__":
    unittest.main()
