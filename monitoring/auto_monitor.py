from monitoring.http_monitor import check_website
from monitoring.ssl_monitor import get_ssl_expiry
from monitoring.email_alert import send_alert

from database.models import db, Website, MonitoringLog

from datetime import datetime


def monitor_all_websites():

    websites = Website.query.all()

    for website in websites:

        previous_status = website.status

        result = check_website(website.url)

        website.status = result["is_online"]

        print("=" * 60)
        print("Checking:", website.website_name)
        print("Previous:", previous_status)
        print("Current :", result["is_online"])
        print("Last Alert:", website.last_alert_sent)
        print("=" * 60)

        # -----------------------------
        # WEBSITE DOWN ALERT
        # -----------------------------
        if (
            previous_status
            and not result["is_online"]
            and website.last_alert_sent != "down"
        ):

            print(">>> Sending DOWN Email")

            send_alert(
                subject="🚨 Website Down",
                recipient="parigyasingh2710@gmail.com",
                body=f"""
Hello,

WebWatch has detected that one of your monitored websites is DOWN.

Website:
{website.website_name}

URL:
{website.url}

Status Code:
{result['status_code']}

Time:
{datetime.now()}

Please investigate the issue.

Regards,
WebWatch
"""
            )

            website.last_alert_sent = "down"
            website.last_alert_time = datetime.utcnow()

        # -----------------------------
        # WEBSITE RECOVERED ALERT
        # -----------------------------
        elif (
            not previous_status
            and result["is_online"]
            and website.last_alert_sent != "recovered"
        ):

            print(">>> Sending RECOVERY Email")

            send_alert(
                subject="✅ Website Recovered",
                recipient="parigyasingh2710@gmail.com",
                body=f"""
Hello,

Good news!

Your website is back ONLINE.

Website:
{website.website_name}

URL:
{website.url}

Status Code:
{result['status_code']}

Time:
{datetime.now()}

Regards,
WebWatch
"""
            )

            website.last_alert_sent = "recovered"
            website.last_alert_time = datetime.utcnow()

        # -----------------------------
        # SSL CHECK
        # -----------------------------
        ssl_expiry = get_ssl_expiry(website.url)

        website.ssl_expiry = ssl_expiry

        if ssl_expiry:

            days_left = (ssl_expiry - datetime.utcnow()).days

            website.ssl_warning = days_left <= 30

            if (
                website.ssl_warning
                and website.last_alert_sent != "ssl"
            ):

                print(">>> Sending SSL Email")

                send_alert(
                    subject="⚠ SSL Certificate Expiring",
                    recipient="parigyasingh2710@gmail.com",
                    body=f"""
Hello,

The SSL certificate for your website is about to expire.

Website:
{website.website_name}

URL:
{website.url}

Days Remaining:
{days_left}

Expiry Date:
{ssl_expiry}

Please renew the certificate.

Regards,
WebWatch
"""
                )

                website.last_alert_sent = "ssl"
                website.last_alert_time = datetime.utcnow()

        else:
            website.ssl_warning = False

        # -----------------------------
        # SAVE LOG
        # -----------------------------
        log = MonitoringLog(
            website_id=website.id,
            status_code=result["status_code"],
            response_time=result["response_time"],
            is_online=result["is_online"]
        )

        db.session.add(log)

    db.session.commit()

    print("✅ Automatic monitoring completed.")