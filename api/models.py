from sqlalchemy import Column, Integer, String, create_engine, ForeignKey, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
# SQLALCHEMY_DATABASE_URL = "sqlite:///./remote.db"
# SQLite database file. Use "sqlite:///./test.db" for absolute path

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Association Table for the Many-to-Many relationship between Questions and Categories
question_category_table = Table('question_category', Base.metadata,
                                Column('question_id', ForeignKey('question.question_id'), primary_key=True),
                                Column('category_id', ForeignKey('category.category_id'), primary_key=True)
                                )


class Task(Base):
    __tablename__ = 'task'

    task_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    network = Column(String, nullable=False)
    contract_address = Column(String, nullable=False)

    responses = relationship(
        "Response",
        back_populates="task"
    )

    completions = relationship(
        "Completion",
        back_populates="task"
    )


class Category(Base):
    __tablename__ = 'category'

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('task.task_id'))
    name = Column(String, nullable=False)
    opposite_category_id = Column(Integer, ForeignKey('category.category_id'), nullable=True)

    opposite = relationship(
        "Category",
        remote_side=[category_id],
        uselist=False,
        backref="opposite_of"
    )

    questions = relationship(
        'Question',
        secondary=question_category_table,
        back_populates='categories'
    )


class Question(Base):
    __tablename__ = 'question'

    question_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('task.task_id'))
    sequence_num = Column(Integer, primary_key=False, nullable=False)
    text = Column(String, nullable=False)
    image_path = Column(String)
    image_ipfs_hash = Column(String, nullable=False)

    categories = relationship(
        "Category",
        secondary=question_category_table,
        back_populates="questions"
    )

    responses = relationship(
        "Response",
        back_populates="question"
    )


class Response(Base):
    __tablename__ = 'response'

    response_id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey('question.question_id'))
    task_id = Column(Integer, ForeignKey('task.task_id'), index=True)
    user_fid = Column(Integer, nullable=True, index=True)
    username = Column(Integer, nullable=True)
    value = Column(Integer, nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("Question", back_populates="responses")
    task = relationship("Task", back_populates="responses")


class Completion(Base):
    __tablename__ = 'completion'

    completion_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('task.task_id'), index=True)
    user_fid = Column(Integer, nullable=True, index=True)

    cluster_id = Column(Integer, ForeignKey('cluster.cluster_id'), index=True)
    cluster = relationship("Cluster", back_populates="completions")
    task = relationship("Task", back_populates="completions")

    token_id = Column(Integer, nullable=True)


class Cluster(Base):
    __tablename__ = 'cluster'

    cluster_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('task.task_id'), index=True)
    name = Column(String, nullable=False, index=True)
    image_ipfs_hash = Column(String, nullable=False)

    completions = relationship(
        "Completion",
        back_populates="cluster"
    )

