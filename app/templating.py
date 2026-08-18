"""Single shared Jinja2Templates instance so `settings` (for the DRY_RUN
banner, base_url, etc.) is available in every template without every router
having to pass it explicitly."""
from fastapi.templating import Jinja2Templates

from app.config import get_settings

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["settings"] = get_settings()
