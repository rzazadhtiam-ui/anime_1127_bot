import os
import ast
import uuid
import shutil
import subprocess
import tempfile
from flask import Flask, request, jsonify, render_template_string

# =======================
# CONFIG
# =======================
PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.abspath("user_apps")
os.makedirs(BASE_DIR, exist_ok=True)

# =======================
# FLASK
# =======================
app = Flask(__name__)

# =======================
# HTML
# =======================
HTML = """
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<title>Python Runner</title>
<style>
body{background:#0b0b0b;color:#fff;font-family:tahoma}
textarea{width:100%;height:260px;background:#000;color:#00ff9c;padding:15px}
button{padding:10px 25px;margin:10px;font-size:16px}
pre{background:#000;border:1px solid #333;padding:15px;min-height:150px}
.status{margin-top:10px;font-weight:bold}
</style>
</head>
<body>

<h2>🚀 اجرای کد پایتون</h2>

<textarea id="code" placeholder="مثال: print('سلام')"></textarea><br>

<button onclick="run()">اجرا</button>

<div class="status" id="status">وضعیت: -</div>

<pre id="out">---</pre>

<script>
function run(){
  document.getElementById("status").textContent = "وضعیت: ⏳ در حال اجرا...";
  fetch("/run", {
    method:"POST",
    body:document.getElementById("code").value
  })
  .then(r=>r.json())
  .then(d=>{
    document.getElementById("status").textContent = "وضعیت: " + d.status;
    document.getElementById("out").textContent = d.output || "---";
  });
}
</script>

</body>
</html>
"""

# =======================
# AST SECURITY
# =======================
FORBIDDEN_CALLS = {
    "eval", "exec", "__import__", "open"
}

FORBIDDEN_ATTRS = {
    ("os", "system"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("shutil", "rmtree"),
}

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.safe = True

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.safe = False

        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                pair = (node.func.value.id, node.func.attr)
                if pair in FORBIDDEN_ATTRS:
                    self.safe = False

        self.generic_visit(node)

def is_code_safe(code: str) -> bool:
    try:
        tree = ast.parse(code)
        v = SecurityVisitor()
        v.visit(tree)
        return v.safe
    except:
        return False

# =======================
# EXECUTION ENGINE
# =======================
def run_python(code: str):
    workdir = tempfile.mkdtemp()
    main_file = os.path.join(workdir, "main.py")

    with open(main_file, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        result = subprocess.run(
            ["python3", "-u", main_file],
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout + result.stderr

        if result.returncode != 0:
            status = "❌ خطا در اجرا"
        else:
            status = "✅ اجرا شد"

    except subprocess.TimeoutExpired:
        output = ""
        status = "⏱ زمان اجرا بیش از حد مجاز"

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return status, output.strip()

# =======================
# ROUTES
# =======================
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/run", methods=["POST"])
def run():
    code = request.data.decode("utf-8")

    if not is_code_safe(code):
        return jsonify({
            "status": "🚫 کد غیرمجاز",
            "output": "استفاده از دستور یا رفتار خطرناک مجاز نیست"
        })

    status, output = run_python(code)

    return jsonify({
        "status": status,
        "output": output or "بدون خروجی"
    })

# =======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
