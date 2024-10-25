from flask import Blueprint, render_template, request, current_app
from models import Sermon
from sqlalchemy import or_, and_
from datetime import datetime

sermons_bp = Blueprint('sermons', __name__)

@sermons_bp.route('/sermons')
def sermons():
    """Display all sermons with optional search parameters."""
    try:
        # Get search parameters
        title = request.args.get('title', '').strip()
        preacher = request.args.get('preacher', '').strip()
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        media_type = request.args.get('media_type', '').strip()

        # Build query
        query = Sermon.query

        # Apply filters
        if title:
            query = query.filter(Sermon.title.ilike(f'%{title}%'))
        if preacher:
            query = query.filter(Sermon.preacher.ilike(f'%{preacher}%'))
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Sermon.date >= start_date)
            except ValueError:
                current_app.logger.warning(f"Invalid start_date format: {start_date}")
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Sermon.date <= end_date)
            except ValueError:
                current_app.logger.warning(f"Invalid end_date format: {end_date}")
        if media_type:
            query = query.filter(Sermon.media_type == media_type)

        # Execute query with sorting
        sermons_list = query.order_by(Sermon.date.desc()).all()
        return render_template('sermons.html', sermons=sermons_list)

    except Exception as e:
        current_app.logger.error(f"Error in sermons route: {str(e)}")
        return render_template('sermons.html', sermons=[])

@sermons_bp.route('/sermons/search')
def search_sermons():
    """Advanced search endpoint for sermons."""
    return sermons()  # Reuse the main sermons route as it already handles search
