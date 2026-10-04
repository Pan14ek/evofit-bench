"""Prometheus metrics with bounded label cardinality."""

from prometheus_client import Counter, Histogram

http_requests_total = Counter("http_requests_total", "HTTP requests", ["method", "path"])
http_responses_total = Counter(
    "http_responses_total", "HTTP responses by status class", ["status_class"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "path"]
)
users_created_total = Counter("users_created_total", "Users created")
tasks_created_total = Counter("tasks_created_total", "Tasks created")
tasks_assigned_total = Counter("tasks_assigned_total", "Tasks assigned")
task_status_changes_total = Counter("task_status_changes_total", "Task status changes")
notifications_created_total = Counter("notifications_created_total", "Notifications created")
business_operation_failures_total = Counter(
    "business_operation_failures_total", "Failed business operations", ["operation"]
)
