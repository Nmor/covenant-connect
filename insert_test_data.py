from datetime import datetime, timedelta

from app import create_app, db
from models import Event, PrayerRequest, Sermon


def insert_test_data():
    app = create_app()
    with app.app_context():
        try:
            # Sample Prayer Requests
            prayer_requests = [
                PrayerRequest(
                    name="Sarah Johnson",
                    email="sarah.j@example.com",
                    request="Please pray for my mother's recovery from surgery. She's been in the hospital for a week.",
                    is_public=True
                ),
                PrayerRequest(
                    name="Michael Chen",
                    email="m.chen@example.com",
                    request="Seeking prayers for guidance in my career decisions and that God would lead me in the right direction.",
                    is_public=True
                ),
                PrayerRequest(
                    name="Emily Williams",
                    email="emily.w@example.com",
                    request="Private prayer request for family healing.",
                    is_public=False
                ),
                PrayerRequest(
                    name="David Thompson",
                    email="david.t@example.com",
                    request="Please join me in praying for our youth ministry and its growth.",
                    is_public=True
                )
            ]

            # Sample Events
            today = datetime.now()
            events = [
                Event(
                    title="Sunday Worship Service",
                    description="Join us for our weekly worship service. All are welcome!",
                    start_date=today + timedelta(days=2, hours=10),
                    end_date=today + timedelta(days=2, hours=12),
                    location="Main Sanctuary"
                ),
                Event(
                    title="Youth Bible Study",
                    description="Weekly Bible study session for young adults (ages 15-25).",
                    start_date=today + timedelta(days=4, hours=18),
                    end_date=today + timedelta(days=4, hours=19, minutes=30),
                    location="Youth Center"
                ),
                Event(
                    title="Community Outreach",
                    description="Monthly community service event. We'll be serving at the local food bank.",
                    start_date=today + timedelta(days=7, hours=9),
                    end_date=today + timedelta(days=7, hours=12),
                    location="Downtown Food Bank"
                ),
                Event(
                    title="Prayer & Worship Night",
                    description="An evening of prayer, worship, and fellowship.",
                    start_date=today + timedelta(days=14, hours=19),
                    end_date=today + timedelta(days=14, hours=21),
                    location="Chapel"
                )
            ]

            # Sample Sermons
            sermons = [
                Sermon(
                    title="Walking in Faith",
                    description="Exploring Hebrews 11 and understanding what it means to live by faith in today's world.",
                    preacher="Pastor John Anderson",
                    date=today - timedelta(days=7),
                    media_url="https://example.com/sermons/walking-in-faith.mp4",
                    media_type="video"
                ),
                Sermon(
                    title="The Power of Prayer",
                    description="Understanding the importance and impact of prayer in our daily lives.",
                    preacher="Pastor Sarah Martinez",
                    date=today - timedelta(days=14),
                    media_url="https://example.com/sermons/power-of-prayer.mp3",
                    media_type="audio"
                ),
                Sermon(
                    title="Building Strong Foundations",
                    description="A study of Matthew 7:24-27 and the importance of building our lives on God's Word.",
                    preacher="Pastor John Anderson",
                    date=today - timedelta(days=21),
                    media_url="https://example.com/sermons/strong-foundations.mp4",
                    media_type="video"
                )
            ]

            # Insert all test data
            db.session.add_all(prayer_requests)
            db.session.add_all(events)
            db.session.add_all(sermons)
            db.session.commit()
            print("Test data inserted successfully!")

        except Exception as e:
            print(f"Error inserting test data: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    insert_test_data()
