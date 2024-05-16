from flask import Blueprint

bp = Blueprint('dashboard', __name__, static_folder="./app/static", template_folder="./app/templates")

from app.handlers import routes
