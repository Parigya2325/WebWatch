import os

class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "webwatch-secret-key"
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:merganki@localhost/webwatch"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False