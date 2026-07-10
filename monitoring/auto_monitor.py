from monitoring.http_monitor import check_website
from database.models import db, Website, MonitoringLog
from monitoring.ssl_monitor import get_ssl_expiry
from datetime import datetime


def monitor_all_websites():

    websites = Website.query.all()

    for website in websites:

        result = check_website(website.url)

        log = MonitoringLog(
            website_id=website.id,
            status_code=result["status_code"],
            response_time=result["response_time"],
            is_online=result["is_online"]
        )

        db.session.add(log)

        website.status = result["is_online"]

        # SSL Monitoring
        ssl_expiry = get_ssl_expiry(website.url)

        website.ssl_expiry = ssl_expiry

        if ssl_expiry:
            days_left = (ssl_expiry - datetime.utcnow()).days
            website.ssl_warning = days_left <= 30

    db.session.commit()

    print("Automatic monitoring completed.")