# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are currently being supported with security updates.

| Python | Supported           |
| ------ | ------------------- |
| <=3.9  | :x: (not supported) |
| 3.10   | :white_check_mark:  |
| 3.11   | :white_check_mark:  |
| 3.12   | :white_check_mark:  |

Only stable Flask 3.1.3+ are supported.

Flask CORS is no longer a dependency — the page and the API are the same origin,
so the app ships without a CORS layer.

Do only install pip packages that are explicitly described in the
[requirements.txt](requirements.txt). Tooling that the application does not
import belongs in [requirements-dev.txt](requirements-dev.txt) and should not be
installed alongside a deployment.

## Reporting a Vulnerability

If you find a security vulnerability, please:

1. Open a **private security advisory** on GitHub.
2. Or email: [LordZNC@zcastle.nexus](mailto:LordZNC@zcastle.nexus)

**Please don't disclose vulnerabilities publicly until they've been fixed.**
