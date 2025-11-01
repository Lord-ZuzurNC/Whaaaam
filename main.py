from providers import PROVIDERS, detect_provider
from tabulate import tabulate

def main():
    url = input("Enter mod URL (CurseForge or Modrinth): ").strip()
    provider_name = detect_provider(url)
    get_mod_data = PROVIDERS[provider_name]

    try:
        mod_info = get_mod_data(url)
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"\n=== {mod_info['name']} ({mod_info['provider']}) ===")
    print(f"Mod ID: {mod_info['mod_id']}\n")

    table = [
        [version, loader]
        for version, loader in mod_info["versions"]
    ]

    if not table:
        print("No version/loader data found.")
    else:
        print(f"[DEBUG] Total versions found: {len(mod_info['versions'])}")
        print(tabulate(table, headers=["Minecraft Version", "Mod Loader"], tablefmt="grid"))


if __name__ == "__main__":
    main()
