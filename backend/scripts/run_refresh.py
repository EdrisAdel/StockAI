from app.database import SessionLocal
from app.services.ingestion import refresh_prices_and_fundamentals
from app.services.universe import SP500_SAMPLE


def main():
    db = SessionLocal()
    try:
        stats = refresh_prices_and_fundamentals(db=db, tickers=SP500_SAMPLE, period="2y")
        print(stats)
    finally:
        db.close()


if __name__ == "__main__":
    main()
