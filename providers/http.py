"""Shared HTTP helper for providers.

Retrying is for conditions that might clear on their own. A 403 from a bad API
key never will: retrying it five times turns an instant, diagnosable failure into
a six-second wait that reports the wrong cause.
"""

import time

import requests

# Statuses worth trying again. Everything else in the 4xx range is a decision the
# server has already made.
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class ProviderError(RuntimeError):
    """A provider failure with a message meant for the person who pasted the URL."""


def request(service, url, *, headers=None, params=None,
            retries=2, delay=1, timeout=10):
    """GET `url`, retrying only what is worth retrying.

    `service` is the user-facing name ("CurseForge"), used in error messages.
    Raises ProviderError with a reason a non-developer can act on.
    """
    last = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        except requests.Timeout:
            last = f"{service} timed out"
        except requests.ConnectionError:
            last = f"{service} could not be reached"
        except requests.RequestException:
            last = f"{service} did not respond"
        else:
            if response.ok:
                return response

            status = response.status_code
            if status in (401, 403):
                # Never retried, and named precisely: this is almost always a
                # missing or wrong CF_API_KEY, which no amount of waiting fixes.
                raise ProviderError(
                    f"{service} rejected the API key (HTTP {status}). Check CF_API_KEY."
                )
            if status == 404:
                raise ProviderError(f"Not found on {service}")
            if status not in RETRYABLE_STATUS:
                raise ProviderError(f"{service} refused the request (HTTP {status})")
            last = (
                f"{service} is rate-limiting requests"
                if status == 429
                else f"{service} is unavailable (HTTP {status})"
            )

        if attempt < retries:
            time.sleep(delay * attempt)  # back off instead of hammering

    raise ProviderError(last or f"{service} did not respond")
