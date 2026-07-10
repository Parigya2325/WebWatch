from monitoring.http_monitor import check_website
from database.models import db, Website, MonitoringLog


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

    db.session.commit()

    print("Automatic monitoring completed.")