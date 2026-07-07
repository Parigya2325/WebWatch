from flask import Flask, render_template, request, redirect, flash
from werkzeug.security import generate_password_hash
from config import Config
from database.models import db, User

app = Flask(__name__)
app.secret_key = "webwatch_secret_key"
app.config.from_object(Config)

db.init_app(app)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


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