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

    @staticmethod
    def create(request):
        data = request.form or request.get_json()

        challenge = ManualChallenge(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge

    @staticmethod
    def read(challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        challenge = ManualChallenge.query.filter_by(id=challenge.id).first()
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "initial": challenge.initial,
            "description": challenge.description,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": ManualGradingChallenge.id,
                "name": ManualGradingChallenge.name,
                "templates": ManualGradingChallenge.templates,
                "scripts": ManualGradingChallenge.scripts,
            },
        }
        return data

    @staticmethod
    def update(challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()

        for attr, value in data.items():
            setattr(challenge, attr, value)

        db.session.commit()

        return challenge

    @staticmethod
    def attempt(challenge, request):
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.

        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """

        return False, "Pending"

    @staticmethod
    def solve(user, team, challenge, request):
        """
        This method is used to insert Solves into the database in order to mark a challenge as solved.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(solve)
        db.session.commit()
        db.session.close()

    @staticmethod
    def fail(user, team, challenge, request):
        """
        This method is used to insert Fails into the database in order to mark an answer incorrect.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        wrong = Pending(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(wrong)
        db.session.commit()
        db.session.close()


class ManualChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "manual"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    initial = db.Column(db.Integer, default=0)

    def __init__(self, *args, **kwargs):
        super(ManualChallenge, self).__init__(**kwargs)
        self.initial = kwargs["value"]


class Pending(Submissions):
    __mapper_args__ = {"polymorphic_identity": "pending"}


@manual.route("/manual/grade", methods=['GET'])
@admins_only
def manual_list_to_grade():
    Model = get_model()

    submissions = (
        Pending.query.add_columns(
            Pending.id,
            Pending.type,
            Pending.challenge_id,
            Pending.provided,
            Pending.account_id,
            Pending.date,
            Challenges.name.label("challenge_name"),
            Model.name.label("team_name"),
        )
            .join(Challenges)
            .join(Model)
            .order_by(Pending.date.desc())
    ).all()

    return render_template('submissions.html', submissions=submissions)


@manual.route("/manual/submissions/<id>", methods=["GET"])
def manual_get_submissions(id):
    # {
    #   "data": {
    #       "correct": [],
    #       "pending": [
    #           {
    #               "date": "2020-05-12T04:05:39.437160Z",
    #               "provided": "WASD"
    #           }
    #       ]
    #   },
    #   "success": true
    # }
    team = get_current_team()
    user = get_current_user()

    pending = Pending.query.filter_by(
        team_id=team.id if team else None,
        user_id=user.id,
        challenge_id=id,
    ).with_entities(Pending.date, Pending.provided).all()

    correct = Solves.query.filter_by(
        team_id=team.id if team else None,
        user_id=user.id,
        challenge_id=id,
    ).with_entities(Solves.date, Solves.provided).all()

    return jsonify({"success": True, "data": {"correct": correct, "pending": pending}})


@manual.route("/manual/approve/<id>", methods=["GET"])
@admins_only
def manual_approve(id):
    submission = Pending.query.filter_by(id=id).first()

    submission.type = 'correct'

    solve = Solves(
        user_id=submission.user_id,
        team_id=submission.team_id if submission.team_id else None,
        challenge_id=submission.challenge_id,
        ip=submission.ip,
        provided=submission.provided,
    )

    db.session.add(solve)

    db.session.delete(submission)

    db.session.commit()
    db.session.close()

    return redirect(url_for('.manual_list_to_grade'))


def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["manual"] = ManualGradingChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/manual-challenges/assets/"
    )

    app.register_blueprint(manual)
