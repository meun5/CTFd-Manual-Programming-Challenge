from flask import Blueprint, render_template, redirect, url_for, jsonify

from CTFd.models import Challenges, db, Solves, Submissions
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from CTFd.utils.decorators import admins_only
from CTFd.utils.modes import get_model
from CTFd.utils.user import get_ip, get_current_user, get_current_team

manual = Blueprint(
    "manual", __name__, template_folder="templates", static_folder="assets"
)


class ManualGradingChallenge(BaseChallenge):
    id = "manual"
    name = "manual"
    templates = {  # Templates used for each aspect of challenge editing & viewing
        "create": "/plugins/manual-challenges/assets/create.html",
        "update": "/plugins/challenges/assets/update.html",
        "view": "/plugins/manual-challenges/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/challenges/assets/create.js",
        "update": "/plugins/challenges/assets/update.js",
        "view": "/plugins/manual-challenges/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/manual-challenges/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = manual



def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["manual"] = ManualGradingChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/manual-challenges/assets/"
    )

    app.register_blueprint(manual)
