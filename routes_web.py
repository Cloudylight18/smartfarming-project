from flask import Blueprint, render_template

# Membuat Blueprint khusus untuk Web UI
web_bp = Blueprint('web_bp', __name__)

@web_bp.route("/")
def index():
    # Hanya me-render template HTML
    return render_template("index.html")