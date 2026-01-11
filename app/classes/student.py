from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.class_store import get_class_store

if TYPE_CHECKING:
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config

class_store = get_class_store()


@class_store.register(name="student")
class Student:
    """Example business class that demonstrates service access.

    Services (data_service, logger, config) are automatically injected
    if not explicitly provided in the constructor.
    """

    def __init__(
        self: Student,
        name: str,
        age: int,
        data_service: DataService | None = None,
        logger: Logger | None = None,
        config: Config | None = None,
    ):
        """Initialize Student with optional service injection.

        Args:
        ----
            name: student name
            age: student age
            data_service: data service (auto-injected if not provided)
            logger: logger service (auto-injected if not provided)
            config: config service (auto-injected if not provided)

        """
        self.name = name
        self.age = age
        # Services are automatically injected by ClassStore if available
        self.data_service = data_service
        self.logger = logger
        self.config = config

        if self.logger:
            self.logger.debug(
                f"Student created: {self.name}",
                extra={"student_name": self.name, "student_age": self.age},
            )

    def __str__(self: Student) -> str:
        """Return string representation of Student.

        Returns
        -------
            String representation of the student.

        """
        return f"Student(name={self.name}, age={self.age})"
