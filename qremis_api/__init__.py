from flask import Flask
from .blueprint import BLUEPRINT

app = Flask(__name__)

app.config.from_envvar("QREMIS_API_CONFIG", silent=True)

# Hardcode any config values into
# app.config here, if you want to.
# Above the from_envvar call they'll
# get clobbered, below it they'll
# clobber things from the file

app.register_blueprint(BLUEPRINT)
