import os

class Config:

    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:merganki@localhost/webwatch"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = "smtp.gmail.com"

    MAIL_PORT = 587

    MAIL_USE_TLS = True

    MAIL_USERNAME = "parigyasingh2710@gmail.com"

    MAIL_PASSWORD = "yxtekuerxngammqb"

    MAIL_DEFAULT_SENDER = "WebWatch <parigyasingh2710@gmail.com>"