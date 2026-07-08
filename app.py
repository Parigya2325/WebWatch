from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database.models import db, User

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

    return render_template(
        "dashboard.html",
        username=session["username"]
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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)