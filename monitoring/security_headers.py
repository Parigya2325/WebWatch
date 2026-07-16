import requests


SECURITY_HEADERS = {

    "Content-Security-Policy":
        "Prevents Cross-Site Scripting (XSS)",

    "Strict-Transport-Security":
        "Forces HTTPS",

    "X-Frame-Options":
        "Prevents Clickjacking",

    "X-Content-Type-Options":
        "Prevents MIME Sniffing",

    "Referrer-Policy":
        "Protects Referrer Information",

    "Permissions-Policy":
        "Restricts Browser Features"

}


def analyze_security_headers(url):

    try:

        response = requests.get(
            url,
            timeout=10
        )

        headers = response.headers

        results = {}

        score = 0

        for header, description in SECURITY_HEADERS.items():

            present = header in headers

            results[header] = {
                "present": present,
                "description": description
            }

            if present:
                score += 1

        percentage = round(
            (score / len(SECURITY_HEADERS)) * 100
        )

        return {

            "results": results,

            "score": score,

            "total": len(SECURITY_HEADERS),

            "percentage": percentage

        }

    except Exception:

        return {

            "results": {},

            "score": 0,

            "total": len(SECURITY_HEADERS),

            "percentage": 0

        }