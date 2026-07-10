import socket
import ssl
from datetime import datetime


def get_ssl_expiry(hostname):

    context = ssl.create_default_context()

    with socket.create_connection((hostname, 443)) as sock:

        with context.wrap_socket(sock, server_hostname=hostname) as ssock:

            certificate = ssock.getpeercert()

            expiry_date = certificate["notAfter"]

            return datetime.strptime(
                expiry_date,
                "%b %d %H:%M:%S %Y %Z"
            )