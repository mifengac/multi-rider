from flask import Blueprint, redirect, render_template, request, url_for

profile_page_bp = Blueprint("profile_page", __name__)


@profile_page_bp.route("/profile")
def profile_search_page():
    zjhm = (request.args.get("zjhm", "") or "").strip()
    if zjhm:
        return redirect(url_for("profile_page.profile_page", zjhm=zjhm))
    return render_template("modules/profile/profile.html", zjhm=None, active_tab="profile")


@profile_page_bp.route("/profile/<zjhm>")
def profile_page(zjhm):
    return render_template("modules/profile/profile.html", zjhm=zjhm, active_tab="profile")
