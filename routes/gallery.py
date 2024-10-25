from flask import Blueprint, render_template, current_app
from models import Gallery
from sqlalchemy.exc import SQLAlchemyError

gallery_bp = Blueprint('gallery', __name__)

@gallery_bp.route('/gallery')
def gallery():
    try:
        images = Gallery.query.order_by(Gallery.created_at.desc()).all()
        return render_template('gallery.html', images=images)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in gallery route: {str(e)}")
        return render_template('gallery.html', images=[], error="Failed to load gallery images.")
    except Exception as e:
        current_app.logger.error(f"Error in gallery route: {str(e)}")
        return render_template('gallery.html', images=[], error="An unexpected error occurred.")
