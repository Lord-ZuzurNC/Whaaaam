from flask import Flask, request, jsonify, send_from_directory, render_template, render_template_string
from flask_cors import CORS
import os
from providers import PROVIDERS, detect_provider

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
        try:
            provider_name = detect_provider(url)
            get_mod_data = PROVIDERS[provider_name]
            mod_info = get_mod_data(url)
            results.append({
                "name": mod_info["name"],
                "provider": mod_info["provider"],
                "mod_id": mod_info["mod_id"],
                "versions": mod_info["versions"]
            })
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
