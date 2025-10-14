# =======================================
# Dynamic HTTP Methods + URL Interpreter
# =======================================

from flask import Flask, jsonify, request
from datetime import datetime
from URI_Parser import URIParser
from functools import wraps

app = Flask(__name__)


# ============================
# Singleton In-Memory Store
# ============================

class Store:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._next_id = 1
        return cls._instance

    def all(self):
        return list(self._data.values())

    def get(self, key):
        return self._data.get(key)

    def create(self, name):
        item = {
            "id": self._next_id,
            "name": name,
            "created": datetime.utcnow().isoformat() + "Z"
        }
        self._data[self._next_id] = item
        self._next_id += 1
        return item

    def update(self, key, name):
        if key not in self._data:
            return None
        self._data[key]["name"] = name
        self._data[key]["updated"] = datetime.utcnow().isoformat() + "Z"
        return self._data[key]

    def delete(self, key):
        return self._data.pop(key, None)


store = Store()


# ============================
# URL Parsing Middleware
# (Interpreter Pattern)
# ============================

@app.before_request
def interpret_url():
    try:
        parsed = URIParser().parse(request.url)
        request.parsed_uri = {
            "scheme": parsed.scheme,
            "username": parsed.username,
            "password": parsed.password,
            "host": parsed.host,
            "port": parsed.port,
            "path": parsed.path,
            "query": parsed.query,
            "fragment": parsed.fragment,
            "opaque": parsed.opaque,
            "normalized": parsed.to_string(),
        }
    except Exception as e:
        request.parsed_uri = {"error": f"URL parse failed: {e}"}


# ============================
# Helper Decorator (Template)
# ============================

def json_endpoint(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)
        return jsonify(response)
    return wrapper


# ============================
# CRUD Endpoints (Command)
# ============================

@app.route("/api/resource", methods=["GET", "HEAD"])
@json_endpoint
def list_resources():
    if request.method == "HEAD":
        return {}
    return {"interpreted_url": request.parsed_uri, "data": store.all()}


@app.route("/api/resource/<int:key>", methods=["GET"])
@json_endpoint
def get_resource(key):
    item = store.get(key)
    if not item:
        return {"error": "not found"}
    return {"interpreted_url": request.parsed_uri, "data": item}


@app.route("/api/resource", methods=["POST"])
@json_endpoint
def create_resource():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return {"error": "name required"}
    return store.create(name)


@app.route("/api/resource/<int:key>", methods=["PUT"])
@json_endpoint
def update_resource(key):
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return {"error": "name required"}
    updated = store.update(key, name)
    return updated or {"error": "not found"}


@app.route("/api/resource/<int:key>", methods=["DELETE"])
@json_endpoint
def delete_resource(key):
    deleted = store.delete(key)
    return {"deleted": key} if deleted else {"error": "not found"}


# ============================
# Universal URL Parser API
# ============================

@app.route("/api/parse", methods=["POST"])
@json_endpoint
def parse_any_url():
    """Interpret *any* URL input by the user."""
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return {"error": "no URL provided"}
    try:
        parsed = URIParser().parse(url)
        return {
            "input": url,
            "parsed": {
                "scheme": parsed.scheme,
                "username": parsed.username,
                "password": parsed.password,
                "host": parsed.host,
                "port": parsed.port,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "opaque": parsed.opaque,
                "normalized": parsed.to_string(),
            }
        }
    except Exception as e:
        return {"error": f"Failed to parse URL: {e}"}


# ============================
# Frontend (Observer)
# ============================

@app.route("/")
def index():
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dynamic HTTP & URL Interpreter</title>
<style>
body{font-family:system-ui,sans-serif;max-width:700px;margin:2rem auto;padding:1rem}
input,button{padding:.4rem;margin:.2rem;font-size:1rem}
pre{background:#f6f6f6;padding:.5rem;border-radius:6px;white-space:pre-wrap}
</style>
</head>
<body>

<h2>HTTP and the GET Method Task</h2>
<div>
  <input id="name" placeholder="Resource name">
  <input id="id" type="number" placeholder="Resource ID" style="width:7rem">
</div>

<div>
  <button onclick="doRequest('GET')">GET all</button>
  <button onclick="doRequest('GET', true)">GET id</button>
  <button onclick="doRequest('POST')">POST</button>
  <button onclick="doRequest('PUT')">PUT</button>
  <button onclick="doRequest('DELETE')">DELETE</button>
</div>

<h3>Universal URL Parser</h3>
<div>
  <input id="urlInput" placeholder="Enter any URL to parse" style="width:80%">
  <button onclick="parseUrl()">Parse URL</button>
</div>

<pre id="out">Ready.</pre>

<script>
async function doRequest(method, useId=false){
  const out=document.getElementById('out');
  out.textContent="...";
  let url='/api/resource';
  const id=document.getElementById('id').value;
  const name=document.getElementById('name').value;
  let body=null;
  if (useId && id) url += '/' + id;
  if (['PUT','DELETE'].includes(method) && id) url += '/' + id;
  if (['POST','PUT'].includes(method)) body = JSON.stringify({name});
  try {
    const res = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body});
    let text = await res.text();
    try{text = JSON.stringify(JSON.parse(text), null, 2);}catch{}
    out.textContent = res.status + ' ' + res.statusText + '\\n\\n' + text;
  } catch(err){ out.textContent = 'Fetch error: ' + err; }
}

async function parseUrl(){
  const out=document.getElementById('out');
  const url=document.getElementById('urlInput').value;
  out.textContent="Parsing...";
  try{
    const res = await fetch('/api/parse', {
      method: 'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({url})
    });
    let text = await res.text();
    try{text = JSON.stringify(JSON.parse(text), null, 2);}catch{}
    out.textContent = text;
  }catch(err){ out.textContent = 'Error: '+err; }
}
</script>

</body></html>
"""


# ============================
# Run (Singleton / Facade)
# ============================

if __name__ == "__main__":
    app.run(debug=True)

