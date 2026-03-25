import os

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from config import (
    APP_HOST,
    APP_PORT,
    FLASK_SECRET_KEY,
    INSTANT_CLIENT_DIR,
    MAX_UPLOAD_BYTES,
    MODEL_DEFAULT,
    logger,
)
from db.sqlite import cleanup_old_jobs, init_db, mark_running_jobs_interrupted
from routes.face_routes import face_bp
from routes.file_routes import file_bp
from routes.job_routes import job_bp
from routes.upload_routes import upload_bp
from service.infer_service import get_model


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = FLASK_SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(exc):
        limit_mb = max(1, MAX_UPLOAD_BYTES // (1024 * 1024))
        logger.warning("Request too large: %s", exc)
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"上传文件过大，当前上限约为 {limit_mb} MB，请压缩后重试或调大 MAX_UPLOAD_BYTES。",
                    "code": 413,
                }
            ),
            413,
        )

    app.register_blueprint(job_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(face_bp)
    return app


def bootstrap_app() -> None:
    init_db()
    cleanup_old_jobs(7)
    mark_running_jobs_interrupted()

    if not os.path.isdir(INSTANT_CLIENT_DIR):
        logger.warning("instantclient directory not found: %s", INSTANT_CLIENT_DIR)

    try:
        get_model(MODEL_DEFAULT)
        logger.info("Model preloaded: %s", MODEL_DEFAULT)
    except Exception as exc:
        logger.warning("Model preload failed for %s: %s", MODEL_DEFAULT, exc)


app = create_app()


def main() -> None:
    bootstrap_app()
    app.run(host=APP_HOST, port=APP_PORT, debug=False)


if __name__ == "__main__":
    main()
