from flask import Flask, jsonify, request, render_template_string
from huggingface_hub import HfApi
import requests

app = Flask(__name__)

HF_TOKEN = "YOUR_HF_TOKEN"

api = HfApi()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>HF Model Scanner</title>

<style>
body{
    margin:0;
    background:#0f1117;
    color:white;
    font-family:Arial;
}

.top{
    padding:15px;
    border-bottom:1px solid #333;
}

input{
    width:100%;
    padding:10px;
    background:#1a1d26;
    color:white;
    border:none;
}

.main{
    display:flex;
    height:calc(100vh - 70px);
}

.left{
    width:50%;
    overflow-y:auto;
    border-right:1px solid #333;
}

.right{
    width:50%;
    overflow-y:auto;
    padding:15px;
}

.model{
    margin:10px;
    padding:10px;
    background:#1a1d26;
    border-radius:8px;
}

button{
    padding:6px 12px;
    cursor:pointer;
}

pre{
    white-space:pre-wrap;
    word-break:break-word;
}
</style>
</head>

<body>

<div class="top">
<input id="search" placeholder="Search model..." onkeyup="loadModels()">
</div>

<div class="main">

<div class="left" id="models"></div>

<div class="right">
<h3>Test Result</h3>
<pre id="result">Ready...</pre>
</div>

</div>

<script>

async function loadModels(){

    let q = document.getElementById("search").value;

    let res = await fetch("/models?q=" + encodeURIComponent(q));

    let data = await res.json();

    let box = document.getElementById("models");

    box.innerHTML = "";

    data.forEach(m=>{

        let div = document.createElement("div");

        div.className = "model";

        div.innerHTML = `
            <b>${m.id}</b><br><br>
            Type: ${m.type}<br><br>
            <button onclick="testModel('${m.id}','${m.type}')">
                Test
            </button>
        `;

        box.appendChild(div);
    });
}

async function testModel(model,type){

    document.getElementById("result").innerText =
        "Testing " + model + "...";

    let res = await fetch("/test",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            model:model,
            type:type
        })
    });

    let data = await res.json();

    document.getElementById("result").innerText =
        JSON.stringify(data,null,2);
}

loadModels();

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/models")
def models():

    q = request.args.get("q","").lower()

    result = []

    try:
        models = api.list_models(limit=200)

        for m in models:

            model_id = m.modelId

            if q and q not in model_id.lower():
                continue

            model_type = getattr(m,"pipeline_tag",None)

            if not model_type:
                model_type = "unknown"

            result.append({
                "id": model_id,
                "type": model_type
            })

    except Exception as e:
        return jsonify([{
            "id":"ERROR",
            "type":str(e)
        }])

    return jsonify(result)

@app.route("/test", methods=["POST"])
def test():

    data = request.json

    model = data["model"]
    model_type = data["type"]

    url = f"https://api-inference.huggingface.co/models/{model}"

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    try:

        if "text" in model_type or "generation" in model_type:

            payload = {
                "inputs":"Hello AI"
            }

            r = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

        elif "image" in model_type:

            payload = {
                "inputs":"robot in cyber city"
            }

            r = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

        else:

            payload = {
                "inputs":"test"
            }

            r = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

        return jsonify({
            "model": model,
            "type": model_type,
            "status": r.status_code,
            "response": r.text[:3000]
        })

    except Exception as e:

        return jsonify({
            "model": model,
            "type": model_type,
            "error": str(e)
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
