from flask import Blueprint, render_template
from models import Gallery

gallery_bp = Blueprint('gallery', __name__)

@gallery_bp.route('/gallery')
def gallery():
    images = Gallery.query.order_by(Gallery.created_at.desc()).all()
    return render_template('gallery.html', images=images)
