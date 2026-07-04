import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def send_alert(message: str) -> None:
    """Шлёт алерт в Telegram, если настроен; иначе пишет в лог с уровнем error."""
    if settings.alert_telegram_bot_token and settings.alert_telegram_chat_id:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{settings.alert_telegram_bot_token}/sendMessage",
                json={"chat_id": settings.alert_telegram_chat_id, "text": f"[DubaiCost] {message}"},
                timeout=10,
            )
            return
        except httpx.HTTPError as exc:
            log.error("alert_send_failed", error=str(exc))
    log.error("alert", message=message)
