import os

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:merganki27@localhost/webwatch"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False