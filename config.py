import os

class Config:
    SECRET_KEY = "webwatch_secret_key"

    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:merganki@localhost/webwatch"

    SQLALCHEMY_TRACK_MODIFICATIONS = False