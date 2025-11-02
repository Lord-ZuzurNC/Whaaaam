from .curseforge import get_mod_data as curseforge
from .modrinth import get_mod_data as modrinth

def detect_provider(url: str):
    if "curseforge.com" in url:
        return "curseforge"
    elif "modrinth.com" in url:
        return "modrinth"
    else:
        raise ValueError("Unsupported provider in URL.")

PROVIDERS = {
    "curseforge": curseforge,
    "modrinth": modrinth
}

