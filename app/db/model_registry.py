"""Register capability models on the single shared SQLAlchemy Base."""

from app.models.base import Base
from app.modules.audit.model import AuditEvent
from app.modules.notifications.model import Notification
from app.modules.tasks.model import Task
from app.modules.users.model import User

__all__ = ["AuditEvent", "Base", "Notification", "Task", "User"]
