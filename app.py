from monitoring.scheduler import scheduler
from monitoring.auto_monitor import monitor_all_websites
from monitoring.http_monitor import check_website
from monitoring.ssl_monitor import get_ssl_expiry
from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database.models import db, User, Website, MonitoringLog

app = Flask(__name__)
app.secret_key = "webwatch_secret_key"
app.config.from_object(Config)

db.init_app(app)

@app.route("/")
def home():
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
        ssl_info=ssl_info
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

    websites = Website.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "websites.html",
        websites=websites
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

    # HTTP Monitoring
    result = check_website(website.url)

    website.status = result["is_online"]

    # SSL Monitoring
    ssl_expiry = get_ssl_expiry(website.url)

    website.ssl_expiry = ssl_expiry

    if ssl_expiry:
        days_left = (ssl_expiry - datetime.utcnow()).days
        website.ssl_warning = days_left <= 30
    else:
        website.ssl_warning = False

    # Save Monitoring Log
    log = MonitoringLog(
        website_id=website.id,
        status_code=result["status_code"],
        response_time=result["response_time"],
        is_online=result["is_online"]
    )

    db.session.add(log)
    db.session.commit()

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

@app.route("/test-ssl")
def test_ssl():

    expiry = get_ssl_expiry("google.com")

    return str(expiry)

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

        scheduler.add_job(
            func=lambda: app.app_context().push() or monitor_all_websites(),
            trigger="interval",
            minutes=1,
            id="website_monitor"
        )

        scheduler.start()

    app.run(debug=True)

