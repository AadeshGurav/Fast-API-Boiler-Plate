from __future__ import annotations
from app.core.class_store import ClassStore

class_store = ClassStore()


@class_store.register(name="student")
class Student:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def __str__(self):
        return f"Student(name={self.name}, age={self.age})"
