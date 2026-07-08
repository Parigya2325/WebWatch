import requests
import time


def check_website(url):

    try:

        start = time.time()

        response = requests.get(
            url,
            timeout=10
        )

        end = time.time()

        response_time = round((end - start) * 1000, 2)

        return {

            "status_code": response.status_code,

            "response_time": response_time,

            "is_online": response.status_code == 200

        }

    except requests.exceptions.RequestException:

        return {

            "status_code": 0,

            "response_time": 0,

            "is_online": False

        }