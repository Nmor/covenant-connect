from redis import Redis
from rq import Worker, Connection
from app import create_app


def main() -> None:
    app = create_app()
    with app.app_context():
        conn = Redis.from_url(app.config['REDIS_URL'])
        with Connection(conn):
            worker = Worker(['default'])
            worker.work()


if __name__ == "__main__":
    main()
