from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.models import RunLog
from app.services.ingestion import refresh_prices_and_fundamentals
from app.services.universe import get_universe


scheduler = BackgroundScheduler()


def refresh_job():
    db = SessionLocal()
    try:
        tickers = get_universe(use_full_sp500=settings.use_sp500_universe)
        stats = refresh_prices_and_fundamentals(
            db=db,
            tickers=tickers,
            period="2y",
            batch_size=settings.refresh_batch_size,
            delay_seconds=settings.refresh_delay_seconds,
        )
        db.add(RunLog(status="success", message=str(stats)))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.add(RunLog(status="failed", message=str(exc)))
        db.commit()
        raise
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return
    trigger = CronTrigger.from_crontab(settings.scheduler_cron)
    scheduler.add_job(refresh_job, trigger=trigger, id="daily_refresh", replace_existing=True)
    scheduler.start()
