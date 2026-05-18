from flask import Blueprint, render_template

profile_page_bp = Blueprint("profile_page", __name__)


@profile_page_bp.route("/profile/<zjhm>")
def profile_page(zjhm):
    return render_template("modules/profile/profile.html", zjhm=zjhm)
