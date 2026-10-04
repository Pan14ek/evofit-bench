"""Prometheus metrics with bounded label cardinality."""

from prometheus_client import Counter, Histogram

http_requests_total = Counter(
    "http_requests_total", "HTTP requests", ["method", "path", "traffic_class"]
)
http_responses_total = Counter(
    "http_responses_total",
    "HTTP responses by status class",
    ["method", "path", "status_class", "traffic_class"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "path", "traffic_class"]
)
users_created_total = Counter("users_created_total", "Users created")
tasks_created_total = Counter("tasks_created_total", "Tasks created")
tasks_assigned_total = Counter("tasks_assigned_total", "Tasks assigned")
task_status_changes_total = Counter("task_status_changes_total", "Task status changes")
notifications_created_total = Counter("notifications_created_total", "Notifications created")
business_operation_failures_total = Counter(
    "business_operation_failures_total", "Failed business operations", ["operation"]
)
business_rule_rejections_total = Counter(
    "business_rule_rejections_total", "Expected business rule rejections", ["operation", "reason"]
)
