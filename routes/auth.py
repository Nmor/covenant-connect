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
        
        logger.info(f"Login attempt for email: {email}")
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user:
                logger.info(f"User found with email: {email}")
                if user.check_password(password):
                    login_user(user)
                    logger.info(f"Successful login for user: {email}")
                    flash('Successfully logged in!', 'success')
                    return redirect(url_for('home.home'))
                else:
                    logger.warning(f"Invalid password for user: {email}")
                    flash('Invalid email or password.', 'danger')
            else:
                logger.warning(f"No user found with email: {email}")
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
            
            logger.info(f"New user registered: {email}")
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
    email = current_user.email
    logout_user()
    logger.info(f"User logged out: {email}")
    flash('Successfully logged out.', 'success')
    return redirect(url_for('home.home'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')
