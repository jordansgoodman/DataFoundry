from typing import Any, Callable


class PythonOperator:
    def __init__(self, task_id: str, python_callable: Callable[..., Any], **kwargs: Any) -> None:
        self.task_id = task_id
        self.python_callable = python_callable
