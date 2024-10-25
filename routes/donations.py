from flask import Blueprint, render_template

donations_bp = Blueprint('donations', __name__)

@donations_bp.route('/donate')
def donate():
    return render_template('donations.html')
