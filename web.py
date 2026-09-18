"""HTTP interface.

Routing and input limits only — the checking and the verdict live in `modlist`
and `compat`, which `main.py` also calls, so the two interfaces cannot drift.

Every URL that gets past `analyze()` costs an outbound request against the
operator's CurseForge key, so the ceilings are enforced here, at the edge,
rather than somewhere down in a provider.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# Loaded here rather than relied on from a provider's import: HOST and PORT are
# read below, and CF_API_KEY is now only read per request.
load_dotenv()

import modlist

app = Flask(__name__, static_folder="static", template_folder="templates")

# A mod list is text. 256 KB holds far more than MAX_URLS lines of URL; a body
# larger than this is not a mod list, and Werkzeug rejects it with 413 before
# the handler ever runs.
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024

MAX_URLS = 200

# The page and the API are the same origin, so nothing here needs a CSP
# exception for scripts. Google Fonts is the only third party the page talks to
# (templates/index.html), and there are no inline scripts to need a nonce.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "script-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


@app.after_request
def add_security_headers(response):
    response.headers.update(SECURITY_HEADERS)
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # silent=True so a body that is not JSON gets the sentence below rather than
    # Werkzeug's own 400 page.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object with a list of URLs."}), 400

    urls = data.get("urls")
    # A bare `if not urls` accepted a number and a dict, then crashed on len()
    # and on iterating keys respectively.
    if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
        return jsonify({"error": "Send a list of URLs."}), 400
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400
    if len(urls) > MAX_URLS:
        return jsonify({"error": f"Check at most {MAX_URLS} mods at a time."}), 413

    return jsonify(modlist.check_urls(urls))


if __name__ == "__main__":
    # Loopback by default. This is Werkzeug's development server: it has no
    # request-size or slow-client protection of its own, so reaching the network
    # takes a deliberate HOST= and something in front of it. For deployment see
    # the gunicorn line in README.md.
    app.run(host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5000")), debug=False, threaded=True)
