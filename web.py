from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

import modlist

app = Flask(__name__, static_folder="static", template_folder="templates")
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
    return jsonify(modlist.check_urls(urls))


@app.route("/clear_cache", methods=["POST"])
def clear_cache():
    try:
        modlist.clear_cache()
        return jsonify({"status": "ok", "message": "Cache cleared."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, threaded=True)
