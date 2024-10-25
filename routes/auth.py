from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User
from sqlalchemy.exc import IntegrityError
import re

auth_bp = Blueprint('auth', __name__)

def is_valid_password(password):
    """Check if password meets minimum requirements"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home.home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if not is_valid_password(password):
            flash('Password must be at least 8 characters long and contain uppercase, lowercase, and numbers.', 'danger')
            return render_template('auth/register.html')

        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration.', 'danger')

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            current_app.logger.warning(f"Login attempt failed: Missing credentials for username: {username}")
            return render_template('auth/login.html')

        try:
            user = User.query.filter_by(username=username).first()
            
            if not user:
                flash('Invalid username or password.', 'danger')
                current_app.logger.warning(f"Login attempt failed: User not found - {username}")
                return render_template('auth/login.html')
            
            if not user.check_password(password):
                flash('Invalid username or password.', 'danger')
                current_app.logger.warning(f"Login attempt failed: Invalid password for user - {username}")
                return render_template('auth/login.html')

            login_user(user)
            current_app.logger.info(f"User logged in successfully: {username}")
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('home.home'))

        except Exception as e:
            current_app.logger.error(f"Login error for user {username}: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
            return render_template('auth/login.html')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home.home'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if not all([username, email]):
            flash('Username and email are required.', 'danger')
            return redirect(url_for('auth.profile'))

        # Check if username or email changed
        username_changed = username != current_user.username
        email_changed = email != current_user.email

        if username_changed or email_changed:
            # Check if new username or email already exists
            if username_changed and User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.profile'))
            if email_changed and User.query.filter_by(email=email).first():
                flash('Email already exists.', 'danger')
                return redirect(url_for('auth.profile'))

        # Update password if provided
        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.profile'))
                
            if new_password != confirm_new_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('auth.profile'))

            if not is_valid_password(new_password):
                flash('New password must be at least 8 characters long and contain uppercase, lowercase, and numbers.', 'danger')
                return redirect(url_for('auth.profile'))

            current_user.set_password(new_password)

        # Update user information
        current_user.username = username
        current_user.email = email
        db.session.commit()
        flash('Profile updated successfully.', 'success')

    except IntegrityError:
        db.session.rollback()
        flash('Username or email already exists.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile update error: {str(e)}")
        flash('An error occurred while updating profile.', 'danger')

    return redirect(url_for('auth.profile'))
