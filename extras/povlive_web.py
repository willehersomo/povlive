#!/usr/bin/env python3
"""Editor de POV-Ray com preview ao vivo.

Uso:  python3 povlive.py arquivo.pov [--porta 8765] [--largura 640 --altura 480]

Abre no navegador: código à esquerda, imagem à direita.
A cada alteração (no navegador ou salvando no VS Code) a cena é renderizada de novo.
"""
import argparse, base64, json, os, subprocess, sys, tempfile, threading, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ap = argparse.ArgumentParser()
ap.add_argument("arquivo")
ap.add_argument("--porta", type=int, default=8765)
ap.add_argument("--largura", type=int, default=640)
ap.add_argument("--altura", type=int, default=480)
args = ap.parse_args()

POV = os.path.abspath(args.arquivo)
PASTA = os.path.dirname(POV)
if not os.path.exists(POV):
    open(POV, "w").close()

lock = threading.Lock()
proc_atual = None  # render em andamento (é cancelado se chegar um novo)


def renderizar(codigo, w, h, qualidade):
    """Renderiza o código num arquivo temporário e devolve (png_base64, log)."""
    global proc_atual
    with tempfile.TemporaryDirectory() as tmp:
        # o .pov temporário fica na mesma pasta para os #include relativos funcionarem
        fd, fonte = tempfile.mkstemp(prefix=".povlive_", suffix=".pov", dir=PASTA)
        saida = os.path.join(tmp, "out.png")
        with os.fdopen(fd, "w") as f:
            f.write(codigo)
        cmd = ["povray", f"+I{fonte}", f"+O{saida}", f"+W{w}", f"+H{h}",
               "-D", "-V", "+FN", f"+Q{qualidade}"]
        if qualidade >= 9:
            cmd.append("+A0.3")
        with lock:
            if proc_atual and proc_atual.poll() is None:
                proc_atual.kill()
            p = subprocess.Popen(cmd, cwd=PASTA, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True)
            proc_atual = p
        log, _ = p.communicate()
        try:
            os.remove(fonte)
        except OSError:
            pass
        png = None
        if p.returncode == 0 and os.path.exists(saida):
            with open(saida, "rb") as f:
                png = base64.b64encode(f.read()).decode()
        return png, log.strip(), p.returncode


PAGINA = r"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>POV-Ray ao vivo</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/monokai.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/clike/clike.min.js"></script>
<style>
 html,body{margin:0;height:100%;background:#1e1e1e;color:#ddd;font-family:system-ui,sans-serif}
 #topo{height:38px;display:flex;align-items:center;gap:12px;padding:0 12px;background:#2a2a2a;font-size:14px}
 #topo b{color:#fff} #status{margin-left:auto}
 #main{display:flex;height:calc(100% - 38px)}
 #esq{flex:1;min-width:0;display:flex;flex-direction:column}
 .CodeMirror{flex:1;height:auto;font-size:14px}
 #log{max-height:30%;overflow:auto;margin:0;padding:8px;background:#300;color:#f99;font-size:12px;white-space:pre-wrap;display:none}
 #dir{flex:1;display:flex;align-items:center;justify-content:center;background:#111}
 #dir img{max-width:100%;max-height:100%;image-rendering:auto}
 .ok{color:#7d7} .erro{color:#f77} .rodando{color:#fd5}
 button,select{background:#444;color:#ddd;border:1px solid #555;border-radius:4px;padding:3px 8px}
</style></head><body>
<div id="topo"><b>__NOME__</b>
 <label>Qualidade <select id="q"><option value="5">rápida</option><option value="9" selected>normal</option><option value="11">final + AA</option></select></label>
 <button id="hd">Render grande (1280×960)</button>
 <span id="status"></span></div>
<div id="main"><div id="esq"><textarea id="cod"></textarea><pre id="log"></pre></div>
<div id="dir"><img id="img"></div></div>
<script>
const st=document.getElementById('status'), log=document.getElementById('log'), img=document.getElementById('img');
const ed=CodeMirror.fromTextArea(document.getElementById('cod'),{mode:'text/x-csrc',theme:'monokai',lineNumbers:true,indentUnit:4});
let timer=null, seq=0, mtime=0, digitando=false;
function status(t,c){st.textContent=t;st.className=c}
async function render(w,h){
  const meu=++seq; status('renderizando…','rodando');
  const r=await fetch('/render',{method:'POST',body:JSON.stringify({codigo:ed.getValue(),w:w||__W__,h:h||__H__,q:+document.getElementById('q').value})});
  const d=await r.json(); if(meu!==seq) return;
  mtime=d.mtime;
  if(d.png){img.src='data:image/png;base64,'+d.png; status('ok ('+d.ms+' ms)','ok'); log.style.display='none'}
  else{status('erro','erro')}
  if(d.rc!==0){log.textContent=d.log; log.style.display='block'}
}
ed.on('change',(_,ch)=>{ if(ch.origin==='setValue') return; digitando=true; clearTimeout(timer); timer=setTimeout(()=>{digitando=false;render()},500)});
document.getElementById('q').onchange=()=>render();
document.getElementById('hd').onclick=()=>render(1280,960);
ed.setOption('extraKeys',{'Ctrl-S':()=>render(),'Ctrl-Enter':()=>render()});
// se o arquivo for alterado fora (ex.: VS Code), recarrega
setInterval(async()=>{ if(digitando) return;
  const d=await (await fetch('/arquivo')).json();
  if(d.mtime>mtime+0.001 && d.codigo!==ed.getValue()){ const c=ed.getCursor(); ed.setValue(d.codigo); ed.setCursor(c); mtime=d.mtime; render() }
},1000);
fetch('/arquivo').then(r=>r.json()).then(d=>{ed.setValue(d.codigo); mtime=d.mtime; render()});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, corpo, tipo="application/json"):
        b = corpo.encode() if isinstance(corpo, str) else corpo
        self.send_response(200)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/":
            html = (PAGINA.replace("__NOME__", os.path.basename(POV))
                    .replace("__W__", str(args.largura)).replace("__H__", str(args.altura)))
            self.responder(html, "text/html")
        elif self.path == "/arquivo":
            with open(POV) as f:
                self.responder(json.dumps({"codigo": f.read(), "mtime": os.path.getmtime(POV)}))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/render":
            return self.send_error(404)
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        codigo = d["codigo"]
        # salva no arquivo original (só se mudou)
        with open(POV) as f:
            atual = f.read()
        if atual != codigo:
            with open(POV, "w") as f:
                f.write(codigo)
        import time
        t = time.time()
        png, log, rc = renderizar(codigo, int(d["w"]), int(d["h"]), int(d["q"]))
        self.responder(json.dumps({"png": png, "log": log, "rc": rc,
                                   "ms": int((time.time() - t) * 1000),
                                   "mtime": os.path.getmtime(POV)}))


url = f"http://localhost:{args.porta}"
print(f"Editando {POV}\nAbra {url}  (Ctrl+C para sair)")
srv = ThreadingHTTPServer(("127.0.0.1", args.porta), H)
threading.Timer(0.5, lambda: webbrowser.open(url)).start()
try:
    srv.serve_forever()
except KeyboardInterrupt:
    print("\ntchau")
