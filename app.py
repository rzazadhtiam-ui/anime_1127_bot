from flask import Flask, request, render_template_string
import subprocess
import tempfile
import os
import time

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Python Runner</title>
<style>
body{
    margin:0;
    font-family:tahoma;
    background:#0b0b0b;
    color:#fff;
}
.container{
    max-width:900px;
    margin:auto;
    padding:40px 20px;
}
h1{
    text-align:center;
    color:#ff9800;
}
textarea{
    width:100%;
    height:260px;
    background:#000;
    color:#00ff9c;
    border:1px solid #333;
    border-radius:10px;
    padding:15px;
    font-family:monospace;
}
button{
    margin-top:15px;
    padding:12px 30px;
    border:none;
    border-radius:10px;
    background:#ff9800;
    font-size:16px;
    cursor:pointer;
}
pre{
    background:#000;
    border:1px solid #222;
    border-radius:10px;
    padding:15px;
    min-height:150px;
    max-height:350px;
    overflow:auto;
}
.footer{
    text-align:center;
    opacity:0.4;
    margin-top:40px;
}
</style>
</head>
<body>

<div class="container">
<h1>🚀 اجرای آنلاین پایتون</h1>

<textarea id="code" placeholder="کد پایتونتو اینجا بنویس..."></textarea>
<br>
<button onclick="runCode()">اجرا</button>

<h3>📤 خروجی</h3>
<pre id="output">---</pre>

<div class="footer">
Keep Alive Enabled
</div>
</div>

<script>
function runCode(){
    const code = document.getElementById("code").value;
    const output = document.getElementById("output");

    if(code.trim()===""){
        output.textContent = "کدی وارد نشده";
        return;
    }

    output.textContent = "در حال اجرا...";

    fetch("/run",{method:"POST", body:code})
    .then(r=>r.text())
    .then(t=>output.textContent=t || "بدون خروجی");
}

// 🔁 هر 45 ثانیه سایت خودشو بیدار می‌کنه
setInterval(()=>{
    fetch("/ping");
},45000);
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

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
            f.write(code.encode())
            path = f.name

        result = subprocess.run(
            ["python3", path],
            capture_output=True,
            text=True,
            timeout=10
        )

        os.remove(path)

        out = ""
        if result.stdout:
            out += result.stdout
        if result.stderr:
            out += "\\nERROR:\\n" + result.stderr

        return out.strip()

    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
