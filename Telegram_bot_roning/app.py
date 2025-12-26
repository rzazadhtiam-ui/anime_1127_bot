from flask import Flask, request, render_template_string, jsonify
import ast
import threading
import queue
import time
import math
import random
import datetime
import uuid

# =========================
# APP INIT
# =========================
app = Flask(__name__)

# =========================
# SIMPLE STORAGE (DEMO)
# بعداً می‌تونی ببری روی DB
# =========================
USER_CODES = {}  # code_id -> {code, status, created_at}

# =========================
# AUTO IMPORT MODULES
# =========================
AUTO_MODULES = {
    "math": math,
    "random": random,
    "time": time,
    "datetime": datetime,
}

# =========================
# BLOCKED NAMES (SECURITY)
# =========================
BLOCKED_NAMES = {
    "os", "sys", "subprocess", "socket", "shutil",
    "eval", "exec", "compile", "open",
    "__import__", "globals", "locals",
    "getattr", "setattr", "delattr",
    "input"
}

# =========================
# AST ANALYZER
# =========================
class CodeInspector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def visit_Name(self, node):
        self.names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            self.names.add(node.value.id)
        self.generic_visit(node)


def analyze_code(code: str):
    tree = ast.parse(code)
    inspector = CodeInspector()
    inspector.visit(tree)
    return inspector.names

# =========================
# SANDBOX EXECUTION
# =========================
def sandbox_exec(code: str, result_queue: queue.Queue):
    try:
        used_names = analyze_code(code)

        # Security check
        for name in used_names:
            if name in BLOCKED_NAMES:
                result_queue.put({
                    "status": "error",
                    "output": f"❌ استفاده از «{name}» مجاز نیست"
                })
                return

        # Restricted environment
        safe_builtins = {
            "print": print,
            "int": int,
            "str": str,
            "float": float,
            "bool": bool,
            "len": len,
            "range": range,
            "enumerate": enumerate,
        }

        env = {
            "__builtins__": safe_builtins
        }

        # Auto inject modules
        for name in used_names:
            if name in AUTO_MODULES:
                env[name] = AUTO_MODULES[name]

        exec(code, env, env)

        result_queue.put({
            "status": "ok",
            "output": "✅ اجرا با موفقیت انجام شد"
        })

    except Exception as e:
        result_queue.put({
            "status": "error",
            "output": f"❌ خطا:\n{e}"
        })

# =========================
# TEST RUN ENDPOINT
# =========================
@app.route("/test", methods=["POST"])
def test_code():
    code = request.data.decode("utf-8")
    q = queue.Queue()

    t = threading.Thread(target=sandbox_exec, args=(code, q))
    t.start()
    t.join(timeout=5)

    if t.is_alive():
        return "❌ اجرای کد بیش از حد طول کشید (Timeout)"

    result = q.get()
    return result["output"]

# =========================
# ACTIVATE CODE (PERMANENT)
# =========================
@app.route("/activate", methods=["POST"])
def activate_code():
    code = request.data.decode("utf-8")
    q = queue.Queue()

    sandbox_exec(code, q)
    result = q.get()

    if result["status"] != "ok":
        return "❌ کد شما ناامن است و فعال نشد"

    code_id = str(uuid.uuid4())
    USER_CODES[code_id] = {
        "code": code,
        "status": "active",
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    return f"✅ کد شما با موفقیت فعال شد 😁\nCode ID:\n{code_id}"

# =========================
# SHARED WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json or {}

    # اینجا بعداً می‌تونی routing واقعی بزنی
    # فعلاً فقط همه کدهای فعال اجرا می‌شن (دمو)
    for item in USER_CODES.values():
        if item["status"] == "active":
            q = queue.Queue()
            sandbox_exec(item["code"], q)

    return "ok"

# =========================
# BASIC UI
# =========================
HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Python Bot Platform</title>
<style>
body{background:#0b0b0b;color:#fff;font-family:tahoma}
textarea{width:100%;height:260px;background:#000;color:#00ff9c}
button{padding:12px 24px;margin-top:10px}
pre{background:#000;padding:15px}
</style>
</head>
<body>
<h2>🚀 پلتفرم اجرای کد پایتون</h2>

<textarea id="code" placeholder="کد پایتون خود را وارد کنید..."></textarea><br>

<button onclick="send('/test')">اجرای تستی</button>
<button onclick="send('/activate')">فعال‌سازی دائمی</button>

<pre id="out">---</pre>

<script>
function send(url){
  fetch(url,{method:"POST",body:document.getElementById("code").value})
  .then(r=>r.text()).then(t=>{
    document.getElementById("out").textContent=t;
  })
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
