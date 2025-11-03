from flask import Flask, request, jsonify, send_from_directory, render_template, render_template_string
from flask_cors import CORS
import os
from providers import PROVIDERS, detect_provider
from urllib.parse import urlparse

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    urls = data.get("urls", [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    results = []
    for url in urls:
        provider_name = None
        try:
            provider_name = detect_provider(url)
            if not urlparse(url).scheme:
                continue
        except Exception as e:
            results.append({"url": url, "error": f"Unknown provider: {e}"})
            continue

        get_mod_data = PROVIDERS.get(provider_name)
        if get_mod_data is None:
            results.append({"url": url, "error": f"No provider implementation for '{provider_name}'"})
            continue

        try:
            mod_info = get_mod_data(url)
            # ensure the original URL is included so frontend has an absolute link
            results.append({
                "name": mod_info.get("name"),
                "provider": mod_info.get("provider"),
                "mod_id": mod_info.get("mod_id"),
                "versions": mod_info.get("versions", []),
                "url": mod_info.get("url") or url  # provider url if present, otherwise original input
            })
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", threaded=True, debug=True)
