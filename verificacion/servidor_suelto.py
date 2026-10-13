#!/usr/bin/env python3
"""Imita el lanzador del módulo suelto (rutas /api/ en la raíz) para probar la página ORIGINAL.
Uso: servidor_suelto.py <pagina.html> <app_id> <puerto> <carpeta_datos> <carpeta_web>"""
import sys, json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
page, app_id, port, data, web = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
os.makedirs(data, exist_ok=True)
DF = os.path.join(data, "datos.json")
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _send(self, code, body=b"", ct="application/json"):
        self.send_response(code); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/": return self._send(200, open(page,"rb").read(), "text/html; charset=utf-8")
        if p == "/api/info": return self._send(200, json.dumps({"app": app_id, "version": "0.1", "carpeta": data, "archivo": DF}).encode())
        if p == "/api/referencia":
            return self._send(200, json.dumps({t: (json.load(open(f)) if os.path.exists(f) else None) for t, f in ((t, os.path.join(data, "ref-" + t + ".json")) for t in ("dic", "ibd"))}).encode())
        if p == "/api/ping": return self._send(200, b'{"ok":true}')
        if p == "/api/datos":
            return self._send(200, open(DF,"rb").read()) if os.path.exists(DF) else self._send(404)
        f = os.path.join(web, p.lstrip("/"))
        if os.path.isfile(f): return self._send(200, open(f,"rb").read(), "application/octet-stream")
        self._send(404)
    def do_PUT(self):
        n = int(self.headers.get("Content-Length",0)); b = self.rfile.read(n)
        if self.path.split("?")[0] == "/api/datos": open(DF,"wb").write(b); return self._send(200, b'{"ok":true}')
        if self.path.split("?")[0] == "/api/referencia":
            t = self.path.split("tipo=")[1]; f = os.path.join(data, "ref-" + t + ".json")
            if b.strip() == b"null":
                if os.path.exists(f): os.remove(f)
            else: open(f, "wb").write(b)
            return self._send(200, b'{"ok":true}')
        self._send(404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length",0)); b = self.rfile.read(n)
        p = self.path.split("?")[0]
        if p == "/api/exportar":
            open(os.path.join(data,"export.xlsx"),"wb").write(b)
            return self._send(200, json.dumps({"ok":True,"nombre":"export.xlsx","carpeta":data}).encode())
        self._send(200, b'{"ok":true}')
HTTPServer(("127.0.0.1", port), H).serve_forever()
