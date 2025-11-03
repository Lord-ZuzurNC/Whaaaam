from providers import PROVIDERS, detect_provider
from tabulate import tabulate
from flask import jsonify

def main():
    print("Enter one or more mod URLs (one per line). Empty line to start:")
    urls = []
    while True:
        line = input().strip()
        if not line:
            break
        urls.append(line)

    all_rows = []
    for url in urls:
        provider_name = detect_provider(url)
        get_mod_data = PROVIDERS[provider_name]
        try:
            mod_info = get_mod_data(url)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        continue
    for version, loader in mod_info["versions"]:
        all_rows.append([mod_info["name"], version, loader])

    print("\n=== Summary ===")
    print(tabulate(all_rows, headers=["Mod Name", "MC Version", "Mod Loader"], tablefmt="grid"))

if __name__ == "__main__":
    main()
