from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>HF AI Tester</title>

<style>
body {
    margin:0;
    font-family:Arial;
    background:#0b0f19;
    color:white;
}

.top {
    padding:10px;
    display:flex;
    gap:10px;
    border-bottom:1px solid #333;
}

input {
    padding:10px;
    flex:1;
    background:#111827;
    border:none;
    color:white;
}

button {
    padding:10px;
    background:#2563eb;
    border:none;
    color:white;
    cursor:pointer;
}

.container {
    display:flex;
    height:calc(100vh - 60px);
}

.left {
    width:45%;
    overflow-y:auto;
    border-right:1px solid #333;
}

.right {
    width:55%;
    padding:10px;
    overflow-y:auto;
}

.model {
    padding:10px;
    margin:8px;
    background:#111827;
    border-radius:8px;
}

small {
    color:#9ca3af;
}
</style>
</head>

<body>

<div class="top">
    <input id="token" placeholder="Enter HF Token">
    <button onclick="loadModels()">Load Models</button>
</div>

<div class="container">

    <div class="left" id="list"></div>

    <div class="right">
        <h3>Result</h3>
        <pre id="out">Ready...</pre>
    </div>

</div>

<script>

async function loadModels(){

    let res = await fetch("/models");
    let data = await res.json();

    let box = document.getElementById("list");
    box.innerHTML = "";

    data.forEach(m => {

        let div = document.createElement("div");
        div.className = "model";

        div.innerHTML = `
            <b>${m.id}</b><br>
            <small>${m.type}</small><br><br>

            <button onclick="testModel('${m.id}','${m.type}')">
                Test
            </button>
        `;

        box.appendChild(div);
    });
}

async function testModel(id,type){

    let token = document.getElementById("token").value;

    document.getElementById("out").innerText = "Testing...";

    let res = await fetch("/test",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            model:id,
            type:type,
            token:token
        })
    });

    let data = await res.json();

    document.getElementById("out").innerText =
        JSON.stringify(data,null,2);
}

</script>

</body>
</html>
"""

from huggingface_hub import HfApi
api = HfApi()

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/models")
def models():
    try:
        data = api.list_models(limit=30)

        out = []

        for m in data:

            task = getattr(m, "pipeline_tag", None)

            if task is None:
                task = "unknown"

            if isinstance(task, str):

                if "text" in task or "generation" in task:
                    t = "text"
                elif "image" in task:
                    t = "image"
                elif "video" in task:
                    t = "video"
                elif "audio" in task:
                    t = "audio"
                else:
                    t = "unknown"
            else:
                t = "unknown"

            out.append({
                "id": m.modelId,
                "type": t
            })

        return jsonify(out)

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/test", methods=["POST"])
def test():

    data = request.json

    model = data["model"]
    model_type = data["type"]
    token = data["token"]

    url = f"https://api-inference.huggingface.co/models/{model}"

    headers = {"Authorization": f"Bearer {token}"}

    try:

        if model_type == "image":

            payload = {"inputs":"a futuristic robot"}

            r = requests.post(url, headers=headers, json=payload, timeout=60)

            if r.headers.get("content-type","").startswith("image"):
                return {"status":"ok","type":"image","note":"binary image returned"}

        else:

            payload = {"inputs":"Hello AI test"}

            r = requests.post(url, headers=headers, json=payload, timeout=30)

        return {
            "model": model,
            "type": model_type,
            "status": r.status_code,
            "response": r.text[:2000]
        }

    except Exception as e:

        return {
            "error": str(e)
        }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
