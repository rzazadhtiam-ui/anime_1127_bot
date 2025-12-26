from flask import Flask, request, render_template_string
import subprocess
import tempfile
import os
import shutil
import datetime

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Python Runner 🚀</title>
<style>
body {
    margin: 0;
    font-family: Tahoma, sans-serif;
    background: #0b0b0b;
    color: #fff;
}
.container {
    max-width: 950px;
    margin: auto;
    padding: 40px 25px;
}
h1 {
    text-align: center;
    color: #ff9800;
    font-size: 2.5em;
    margin-bottom: 25px;
}
textarea {
    width: 100%;
    height: 280px;
    background: #000;
    color: #00ff9c;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 15px;
    font-family: monospace;
    font-size: 15px;
    resize: vertical;
}
button {
    margin-top: 20px;
    padding: 14px 32px;
    border: none;
    border-radius: 12px;
    background: #ff9800;
    font-size: 17px;
    cursor: pointer;
    transition: 0.3s;
}
button:hover {
    background: #e68a00;
}
pre {
    background: #000;
    border: 1px solid #222;
    border-radius: 12px;
    padding: 18px;
    min-height: 180px;
    max-height: 400px;
    overflow: auto;
    font-family: monospace;
    font-size: 14px;
}
.footer {
    text-align: center;
    opacity: 0.5;
    margin-top: 35px;
    font-size: 0.9em;
}
.status {
    margin-top: 15px;
    padding: 12px;
    border-radius: 10px;
    background: #111;
    border: 1px solid #333;
    font-family: monospace;
    color: #00ff9c;
    min-height: 30px;
}
</style>
</head>
<body>
<div class="container">
<h1>🚀 اجرای آنلاین پایتون</h1>

<textarea id="code" placeholder="کد پایتونتو اینجا بنویس..."></textarea>
<br>
<button onclick="runCode()">اجرا</button>

<div class="status" id="status">وضعیت: آماده</div>

<h3>📤 خروجی</h3>
<pre id="output">---</pre>

<div class="footer">
Keep Alive Enabled | © 2025
</div>
</div>

<script>
function runCode(){
    const code = document.getElementById("code").value;
    const output = document.getElementById("output");
    const status = document.getElementById("status");

    if(code.trim()===""){
        output.textContent = "کدی وارد نشده";
        status.textContent = "وضعیت: خطا";
        return;
    }

    output.textContent = "در حال اجرا...";
    status.textContent = "وضعیت: اجرای کد";

    fetch("/run",{method:"POST", body:code})
    .then(r=>r.text())
    .then(t=>{
        output.textContent = t || "بدون خروجی";
        status.textContent = "وضعیت: اجرا کامل شد";
    })
    .catch(e=>{
        output.textContent = "❌ خطا در اتصال";
        status.textContent = "وضعیت: خطا";
    });
}

// 🔁 هر 45 ثانیه سایت خودشو بیدار می‌کنه
setInterval(()=>{fetch("/ping");},45000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/run", methods=["POST"])
def run_code():
    code = request.data.decode()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = tempfile.mkdtemp(prefix=f"pyrun_{timestamp}_")
    main_file = os.path.join(temp_dir, "main.py")

    try:
        # ذخیره کد در فایل اصلی
        with open(main_file, "w", encoding="utf-8") as f:
            f.write(code)

        # اجرای کد با محدودیت زمان 60 ثانیه
        result = subprocess.run(
            ["python3", main_file],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=600
        )

        # ترکیب خروجی و خطاها
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\nERROR:\n" + result.stderr

        return output.strip()

    except subprocess.TimeoutExpired:
        return "❌ اجرای کد طولانی شد و متوقف شد (Timeout 60s)"
    except Exception as e:
        return f"❌ خطا: {str(e)}"
    finally:
        # پاکسازی دایرکتوری موقت
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
