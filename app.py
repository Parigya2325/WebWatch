import pandas as pd
import csv
import io
from flask import Response
from monitoring.scheduler import scheduler
from monitoring.auto_monitor import monitor_all_websites
from monitoring.http_monitor import check_website
from monitoring.ssl_monitor import get_ssl_expiry
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database.models import (
    db,
    User,
    Website,
    MonitoringLog,
    Notification
)
from flask_mail import Mail
from monitoring.email_alert import init_mail, send_alert
from flask import send_file
from reports.pdf_report import generate_pdf
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    session,
    send_file
)
from monitoring.security_headers import analyze_security_headers

# Create Flask app FIRST
app = Flask(__name__)
app.secret_key = "webwatch_secret_key"
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

mail = Mail(app)
init_mail(app, mail)

@app.route("/")
def home():

    if "user_id" in session:
        return redirect("/dashboard")

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["username"] = user.username

            flash("Login Successful!")
            return redirect("/dashboard")

        flash("Invalid Email or Password")
        return redirect("/login")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    websites = Website.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_websites = len(websites)

    online = sum(1 for website in websites if website.status)

    offline = total_websites - online

    ssl_alerts = Website.query.filter_by(
        user_id=session["user_id"],
        ssl_warning=True
    ).count()

    recent_logs = (
        MonitoringLog.query
        .join(Website)
        .filter(Website.user_id == session["user_id"])
        .order_by(MonitoringLog.checked_at.desc())
        .limit(5)
        .all()
    )

    website_names = []
    avg_response_times = []
    uptime_data = []

    for website in websites:

        total_logs = MonitoringLog.query.filter_by(
            website_id=website.id
        ).count()

        online_logs = MonitoringLog.query.filter_by(
            website_id=website.id,
            is_online=True
        ).count()

        if total_logs == 0:
            uptime = 0
        else:
            uptime = round((online_logs / total_logs) * 100, 2)
        
        uptime_data.append({
            "name": website.website_name,
            "uptime": uptime
        })

    for website in websites:

        logs = (
            MonitoringLog.query
            .filter_by(website_id=website.id)
            .order_by(MonitoringLog.checked_at.desc())
            .limit(10)
            .all()
        )

        if logs:
            avg = sum(log.response_time for log in logs) / len(logs)
            website_names.append(website.website_name)
            avg_response_times.append(round(avg, 2))

    print("Session User ID:", session["user_id"])
    print("Total recent logs:", len(recent_logs))

    for log in recent_logs:
        print(
            log.id,
            log.website.website_name,
            log.website.user_id,
            log.checked_at
        )

    ssl_info = []

    for website in websites:
        if website.ssl_expiry:
            days_left = (website.ssl_expiry - datetime.utcnow()).days
        else:
            days_left = None
        ssl_info.append({
            "name": website.website_name,
            "expiry": website.ssl_expiry,
            "days_left": days_left
        })

    response_history = (
        MonitoringLog.query
        .join(Website)
        .filter(Website.user_id == session["user_id"])
        .order_by(MonitoringLog.checked_at.asc())
        .limit(20)
        .all()
    )

    history_labels = [
        log.checked_at.strftime("%H:%M")
        for log in response_history
    ]

    history_times = [
        round(log.response_time, 2)
        for log in response_history
    ]

    # ----------------------------------------
    # Dashboard Analytics
    # ----------------------------------------
  
    all_logs = (
        MonitoringLog.query
        .join(Website)
        .filter(Website.user_id == session["user_id"])
        .all()
    )

    total_checks = len(all_logs)

    if total_checks > 0:
        
        average_response = round(
            sum(log.response_time for log in all_logs) / total_checks,
            2
        )

        fastest_response = min(
            log.response_time for log in all_logs
        )

        slowest_response = max(
            log.response_time for log in all_logs
        )

        last_scan = max(
            log.checked_at for log in all_logs
        )

    else:
        
        average_response = 0
        fastest_response = 0
        slowest_response = 0
        last_scan = None


    # ----------------------------------------
    # Overall Security Score
    # ----------------------------------------

    security_score = 100
    
    security_score -= offline * 15
    
    security_score -= ssl_alerts * 10
    
    if security_score < 0:
        security_score = 0

    critical_alerts = []
    
    for website in websites:
        
        if not website.status:
            
            critical_alerts.append(
                f"🔴 {website.website_name} is Offline"
            )

        if website.ssl_warning:

            critical_alerts.append(
                f"⚠ SSL Certificate Expiring for {website.website_name}"
            )

    dashboard_status = []

    for website in websites:

        logs = (
            MonitoringLog.query
            .filter_by(website_id=website.id)
            .order_by(MonitoringLog.checked_at.desc())
            .first()
        )

        response = logs.response_time if logs else 0

        health = 100

        if not website.status:
            health -= 40

        if website.ssl_warning:
            health -= 20

        dashboard_status.append({

            "name": website.website_name,

            "status": website.status,

            "response": response,

            "ssl": website.ssl_warning,

            "health": health

        })

    # ----------------------------------------
    # Overall Website Availability
    # ----------------------------------------

    overall_logs = (
        MonitoringLog.query
        .join(Website)
        .filter(Website.user_id == session["user_id"])
        .count()
    )

    online_logs = (
        MonitoringLog.query
        .join(Website)
        .filter(
            Website.user_id == session["user_id"],
            MonitoringLog.is_online == True
        )
        .count()
    )

    if overall_logs > 0:
        availability = round((online_logs / overall_logs) * 100, 2)
    else:
        availability = 0

    system_status = {
        "monitoring": "Running",
        "scheduler": "Active",
        "database": "Connected",
        "email": "Enabled",
        "refresh": "Every 60 Seconds"
}

    return render_template(
        "dashboard.html",
        username=session["username"],
        total_websites=total_websites,
        online=online,
        offline=offline,
        ssl_alerts=ssl_alerts,
        recent_logs=recent_logs,
        website_names=website_names,
        avg_response_times=avg_response_times,
        uptime_data=uptime_data,
        ssl_info=ssl_info,
        history_labels=history_labels,
        history_times=history_times,
        average_response=average_response,
        total_checks=total_checks,
        fastest_response=fastest_response,
        slowest_response=slowest_response,
        last_scan=last_scan,
        security_score=security_score,
        critical_alerts=critical_alerts,
        dashboard_status=dashboard_status,
        availability=availability,
        system_status=system_status
    )

@app.route("/add-website", methods=["GET", "POST"])
def add_website():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    if request.method == "POST":

        website = Website(

            website_name=request.form["website_name"],

            url=request.form["url"],

            monitoring_interval=request.form["interval"],

            user_id=session["user_id"]

        )

        db.session.add(website)
        db.session.commit()

        flash("Website added successfully!")

        return redirect("/websites")

    return render_template("add_website.html")

@app.route("/websites")
def websites():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    search = request.args.get("search", "").strip()

    query = Website.query.filter_by(
        user_id=session["user_id"]
    )

    if search:
        query = query.filter(
            Website.website_name.ilike(f"%{search}%")
        )

    websites = query.all()

    return render_template(
        "websites.html",
        websites=websites,
        search=search,
        now=datetime.utcnow()
    )

@app.route("/website/<int:id>")
def website_details(id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    website = Website.query.get_or_404(id)

    if website.user_id != session["user_id"]:
        flash("Unauthorized access.")
        return redirect("/websites")

    logs = (
        MonitoringLog.query
        .filter_by(website_id=id)
        .order_by(MonitoringLog.checked_at.desc())
        .limit(20)
        .all()
    )

    logs.reverse()

    chart_labels = [
        log.checked_at.strftime("%d-%m %H:%M")
        for log in logs
    ]

    chart_values = [
        log.response_time
        for log in logs
    ]

    total_logs = len(logs)

    online_logs = sum(
        1 for log in logs if log.is_online
    )

    uptime = (
        round((online_logs / total_logs) * 100, 2)
        if total_logs else 0
    )

    average_response = (
        round(
            sum(log.response_time for log in logs) / total_logs,
            2
        )
        if total_logs else 0
    )

    days_left = None

    if website.ssl_expiry:
        days_left = (
            website.ssl_expiry - datetime.utcnow()
        ).days

    # -----------------------------
    # NEW SECURITY HEADER ANALYSIS
    # -----------------------------
    security = analyze_security_headers(
        website.url
    )

    # -----------------------------
    # WEBSITE HEALTH SCORE
    # -----------------------------
    health_score = 0

    # Website Online
    if website.status:
        health_score += 40

    # SSL Valid
    if website.ssl_expiry and days_left is not None and days_left > 0:
        health_score += 30

    # Security Headers
    header_score = (
        security["score"] / security["total"]
    ) * 30

    health_score += round(header_score)

    health_score = min(100, health_score)

    if health_score >= 80:
        risk_level = "Low"
        risk_color = "success"
        
    elif health_score >= 50:
        risk_level = "Medium"
        risk_color = "warning"
        
    else:
        risk_level = "High"
        risk_color = "danger"

    recommendations = []

    if website.status:
        recommendations.append("✅ Website is online.")
    else:
        recommendations.append("❌ Website is currently offline.")

    if average_response > 1000:
        recommendations.append(
            "⚠ High response time detected. Consider optimizing server performance."
        )

    if days_left is not None:
        if days_left <= 30:
            recommendations.append(
                "⚠ SSL certificate is close to expiry."
            )
        else:
            recommendations.append(
                "✅ SSL certificate is valid."
            )

    for header, info in security["results"].items():

        if not info["present"]:

            recommendations.append(
                f"⚠ Add '{header}' security header."
            )

    if security["percentage"] == 100:
        recommendations.append(
            "✅ Excellent security configuration."
        )

    return render_template(
        "website_details.html",
        website=website,
        logs=logs,
        uptime=uptime,
        average_response=average_response,
        total_logs=total_logs,
        days_left=days_left,
        chart_labels=chart_labels,
        chart_values=chart_values,
        security=security,
        health_score=health_score,
        risk_level=risk_level,
        risk_color=risk_color,
        recommendations=recommendations
    )

@app.route("/security-scan/<int:id>")
def security_scan(id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    website = Website.query.get_or_404(id)

    if website.user_id != session["user_id"]:
        flash("Unauthorized access.")
        return redirect("/websites")

    headers = scan_security_headers(website.url)

    score = sum(headers.values())
    percentage = int((score / len(headers)) * 100)

    return render_template(
        "security_scan.html",
        website=website,
        headers=headers,
        percentage=percentage
    )

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully.")

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("Username already exists.")
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect("/login")

    return render_template("register.html")

@app.route("/edit-website/<int:id>", methods=["GET", "POST"])
def edit_website(id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    website = Website.query.get_or_404(id)

    # Prevent users editing someone else's website
    if website.user_id != session["user_id"]:
        flash("Unauthorized access.")
        return redirect("/websites")

    if request.method == "POST":

        website.website_name = request.form["website_name"]
        website.url = request.form["url"]
        website.monitoring_interval = request.form["interval"]

        db.session.commit()

        flash("Website updated successfully!")

        return redirect("/websites")

    return render_template(
        "edit_website.html",
        website=website
    )

@app.route("/delete-website/<int:id>")
def delete_website(id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    website = Website.query.get_or_404(id)

    # Prevent users deleting someone else's website
    if website.user_id != session["user_id"]:
        flash("Unauthorized access.")
        return redirect("/websites")
    
    # Delete monitoring logs first
    MonitoringLog.query.filter_by(
        website_id=website.id
    ).delete()

    # Now delete website
    db.session.delete(website)
    db.session.commit()

    flash("Website deleted successfully!")

    return redirect("/websites")


@app.route("/monitor/<int:id>")
def monitor(id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    website = Website.query.get_or_404(id)

    db.session.refresh(website)

    # Ensure the logged-in user owns this website
    if website.user_id != session["user_id"]:
        flash("Unauthorized access.")
        return redirect("/websites")

    # ---------------------------------------
    # Website Monitoring
    # ---------------------------------------
    result = check_website(website.url)

    print("=" * 70)
    print("MONITOR ROUTE CALLED")
    print("Website ID:", id)
    print("=" * 70)

    previous_status = website.status
    current_status = result["is_online"]

    print(f"Transition: {previous_status} -> {current_status}")

    website.status = current_status

    print("=" * 60)
    print("Website:", website.website_name)
    print("Previous:", previous_status)
    print("Current :", current_status)
    print("=" * 60)

    # ---------------------------------------
    # WEBSITE DOWN
    # ---------------------------------------
    if previous_status and not current_status:

        if website.last_alert_sent != "down":

            send_alert(
                subject="🚨 Website Down!",
                recipient="parigyasingh2710@gmail.com",
                body=f"""
Website: {website.website_name}

URL: {website.url}

The website is currently OFFLINE.

Status Code: {result['status_code']}
"""
            )

            notification = Notification(
                user_id=website.user_id,
                title="Website Down",
                message=f"{website.website_name} is currently offline.",
                type="danger"
            )
            db.session.add(notification)
            
            print("Notification object created:")
            print(notification.user_id)
            print(notification.title)
            print(notification.message)

            website.last_alert_sent = "down"
            website.last_alert_time = datetime.utcnow()

            print("DOWN notification created.")

    # ---------------------------------------
    # WEBSITE RECOVERED
    # ---------------------------------------
    elif (not previous_status) and current_status:

        if website.last_alert_sent != "recovered":

            send_alert(
                subject="✅ Website Recovered",
                recipient="parigyasingh2710@gmail.com",
                body=f"""
Website: {website.website_name}

URL: {website.url}

The website is ONLINE again.

Status Code: {result['status_code']}
"""
            )

            notification = Notification(
                user_id=website.user_id,
                title="Website Recovered",
                message=f"{website.website_name} is back online.",
                type="success"
            )
            
            db.session.add(notification)
            print("Notification object created:")
            print(notification.user_id)
            print(notification.title)
            print(notification.message)

            website.last_alert_sent = "recovered"
            website.last_alert_time = datetime.utcnow()

            print("RECOVERY notification created.")

    # ---------------------------------------
    # SSL Monitoring
    # ---------------------------------------
    ssl_expiry = get_ssl_expiry(website.url)

    website.ssl_expiry = ssl_expiry

    if ssl_expiry:

        days_left = (ssl_expiry - datetime.utcnow()).days

        website.ssl_warning = days_left <= 30

        if website.ssl_warning:

            if website.last_alert_sent != "ssl":

                send_alert(
                    subject="⚠️ SSL Certificate Expiring",
                    recipient="parigyasingh2710@gmail.com",
                    body=f"""
Website: {website.website_name}

URL: {website.url}

SSL certificate expires in {days_left} days.

Expiry Date: {ssl_expiry}
"""
                )

                notification = Notification(
                    user_id=website.user_id,
                    title="SSL Certificate Expiring",
                    message=f"The SSL certificate for {website.website_name} expires in {days_left} days.",
                    type="warning"
                )
                
                db.session.add(notification)
                
                print("Notification object created:")
                print(notification.user_id)
                print(notification.title)
                print(notification.message)

                website.last_alert_sent = "ssl"
                website.last_alert_time = datetime.utcnow()

                print("SSL notification created.")

    else:
        website.ssl_warning = False

    # ---------------------------------------
    # Save Monitoring Log
    # ---------------------------------------
    log = MonitoringLog(
        website_id=website.id,
        status_code=result["status_code"],
        response_time=result["response_time"],
        is_online=current_status
    )

    db.session.add(log)

    print("=" * 60)
    print("About to commit changes...")
    print("Last Alert:", website.last_alert_sent)
    print("=" * 60)

    # ---------------------------------------
    # Commit Everything
    # ---------------------------------------
    try:
        db.session.commit()
        print("Database commit successful.")
    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", e)

    flash("Website monitored successfully!")

    return redirect("/websites")

@app.route("/monitoring-history")
def monitoring_history():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    logs = (
        MonitoringLog.query
        .join(Website)
        .filter(Website.user_id == session["user_id"])
        .order_by(MonitoringLog.checked_at.desc())
        .all()
    )

    return render_template(
        "monitoring_logs.html",
        logs=logs
    )

@app.route("/export-csv")
def export_csv():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    logs = (
        MonitoringLog.query
        .join(Website)
        .filter(Website.user_id == session["user_id"])
        .order_by(MonitoringLog.checked_at.desc())
        .all()
    )

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Website",
        "Status Code",
        "Response Time (ms)",
        "Online",
        "Checked At"
    ])

    for log in logs:

        writer.writerow([
            log.website.website_name,
            log.status_code,
            round(log.response_time, 2),
            "Online" if log.is_online else "Offline",
            log.checked_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=monitoring_history.csv"
        }
    )

@app.route("/download-report")
def download_report():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    websites = Website.query.filter_by(
        user_id=session["user_id"]
    ).all()

    pdf = generate_pdf(
        session["username"],
        websites
    )

    return send_file(
        pdf,
        download_name="WebWatch_Report.pdf",
        as_attachment=True,
        mimetype="application/pdf"
    )

@app.route("/test-ssl")
def test_ssl():

    expiry = get_ssl_expiry("google.com")

    return str(expiry)

@app.route("/test-email")
def test_email():

    send_alert(
        subject="✅ WebWatch Test Email",
        recipient="parigyasingh2710@gmail.com",
        body="""
Congratulations!

Your email notifications are working correctly.

This message was sent from your WebWatch application.
"""
    )

    return "Email sent successfully!"

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if request.method == "POST":

        user.username = request.form["username"]
        user.email = request.form["email"]

        db.session.commit()

        session["username"] = user.username

        flash("Profile updated successfully!")

        return redirect("/profile")

    return render_template(
        "profile.html",
        user=user
    )

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    notifications = (
        Notification.query
        .filter_by(user_id=session["user_id"])
        .order_by(Notification.created_at.desc())
        .all()
    )

    return render_template(
        "notifications.html",
        notifications=notifications
    )

@app.context_processor
def inject_notifications():

    if "user_id" not in session:
        return dict(
            notifications=[],
            unread_notifications=0
        )

    notifications = (
        Notification.query
        .filter_by(user_id=session["user_id"])
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )

    unread_notifications = (
        Notification.query
        .filter_by(
            user_id=session["user_id"],
            is_read=False
        )
        .count()
    )

    return dict(
        notifications=notifications,
        unread_notifications=unread_notifications
    )

@app.route("/notifications/read-all")
def read_all_notifications():

    if "user_id" not in session:
        return redirect("/login")

    Notification.query.filter_by(
        user_id=session["user_id"],
        is_read=False
    ).update(
        {"is_read": True}
    )

    db.session.commit()

    flash("All notifications marked as read.")

    return redirect(request.referrer or "/dashboard")

@app.route("/notifications/clear")
def clear_notifications():

    if "user_id" not in session:
        return redirect("/login")

    Notification.query.filter_by(
        user_id=session["user_id"]
    ).delete()

    db.session.commit()

    flash("All notifications cleared.")

    return redirect(request.referrer or "/dashboard")

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    def scheduled_monitor():
        with app.app_context():
            monitor_all_websites()

    if not scheduler.running:
        scheduler.add_job(
            func=scheduled_monitor,
            trigger="interval",
            minutes=1,
            id="website_monitor",
            replace_existing=True
        )

        scheduler.start()

    app.run(debug=True, use_reloader=False)