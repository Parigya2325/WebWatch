import os

class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "webwatch-secret-key"
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://neondb_owner:npg_0GWOxSP7FDfi@ep-ancient-snow-azlwimk1-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False