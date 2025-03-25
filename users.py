from flask import Blueprint

users = Blueprint('users', __name__)

@users.route('/user/<username>')
def profile(username):
    return f"User: {username}"
