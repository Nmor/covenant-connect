from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger('covenant_connect')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash('Successfully logged in!', 'success')
                return redirect(url_for('home.home'))
            else:
                flash('Invalid email or password.', 'danger')
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            flash('An error occurred during login.', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        try:
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('auth.register'))
                
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.register'))
                
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('auth.register'))
            
            user = User(
                username=username,
                email=email,
                is_admin=False,
                notification_preferences={}
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            flash('An error occurred during registration.', 'danger')
            db.session.rollback()
            
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out.', 'success')
    return redirect(url_for('home.home'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')
