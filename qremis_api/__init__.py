from flask import Flask
from .blueprint import BLUEPRINT
from flask_env import MetaFlaskEnv


class Configuration(metaclass=MetaFlaskEnv):
    ENV_PREFIX='QREMIS_API_'
    DEBUG = False
    DEFER_CONFIG = False


app = Flask(__name__)

app.config.from_object(Configuration)

# Hardcode any config values into
# app.config here, if you want to.
# Above the from_envvar call they'll
# get clobbered, below it they'll
# clobber things from the file

app.register_blueprint(BLUEPRINT)
