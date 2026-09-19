from abc import ABC, abstractmethod
from typing import List, Optional
from sqlmodel import Session, select, create_engine
from models import Task


class TaskRepository(ABC):
    """Interface that any storage backend must implement."""

    @abstractmethod
    def get_all(self) -> List[Task]:
        pass

    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[Task]:
        pass

    @abstractmethod
    def create(self, title: str) -> Task:
        pass

    @abstractmethod
    def update(self, task_id: int, title: str, done: bool) -> Optional[Task]:
        pass

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        pass

    @abstractmethod
    def seed_if_empty(self) -> None:
        pass


class PostgresRepository(TaskRepository):
    """Postgres implementation of TaskRepository."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)

    def create_tables(self):
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(self.engine)

    def seed_if_empty(self) -> None:
        with Session(self.engine) as session:
            existing = session.exec(select(Task)).first()
            if existing is None:
                session.add(Task(title="Buy groceries", done=False))
                session.add(Task(title="Finish assignment", done=False))
                session.add(Task(title="Walk the dog", done=True))
                session.commit()

    def get_all(self) -> List[Task]:
        with Session(self.engine) as session:
            return session.exec(select(Task)).all()

    def get_by_id(self, task_id: int) -> Optional[Task]:
        with Session(self.engine) as session:
            return session.get(Task, task_id)

    def create(self, title: str) -> Task:
        with Session(self.engine) as session:
            new_task = Task(title=title, done=False)
            session.add(new_task)
            session.commit()
            session.refresh(new_task)
            return new_task

    def update(self, task_id: int, title: str, done: bool) -> Optional[Task]:
        with Session(self.engine) as session:
            task = session.get(Task, task_id)
            if task is None:
                return None
            task.title = title
            task.done = done
            session.add(task)
            session.commit()
            session.refresh(task)
            return task

    def delete(self, task_id: int) -> bool:
        with Session(self.engine) as session:
            task = session.get(Task, task_id)
            if task is None:
                return False
            session.delete(task)
            session.commit()
            return True