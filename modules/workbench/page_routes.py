from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
from shared.config.config import (
    MODEL_DEFAULT,
    CONF_THRESH,
    BATCH_SIZE,
    IMGSZ,
    get_upload_model_options,
    get_upload_model_default,
    get_train_base_model_options,
)

workbench_page_bp = Blueprint("workbench_page", __name__)

VALID_TABS = {"oracle", "upload", "dispatch", "train", "diagnostics"}


@workbench_page_bp.route("/workbench")
def workbench():
    tab = request.args.get("tab", "oracle")
    if tab not in VALID_TABS:
        tab = "oracle"

    # Generate default time (for form population in _oracle_tab.html)
    now = datetime.now()
    kssj_local = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    jssj_local = now.strftime("%Y-%m-%dT%H:%M:%S")

    # Get model info, inference parameters, and upload/training configs from config
    return render_template(
        "modules/workbench/workbench.html",
        active_tab="workbench",
        active_subtab=tab,
        model_default=MODEL_DEFAULT,
        kssj_local=kssj_local,
        jssj_local=jssj_local,
        conf_default=CONF_THRESH,
        batch_default=BATCH_SIZE,
        imgsz_default=IMGSZ,
        upload_models=get_upload_model_options(),
        upload_model_default=get_upload_model_default(),
        train_base_models=get_train_base_model_options(),
    )
