"""
数据库初始化模块
独立的数据库配置，避免循环导入
"""

try:
    from flask_sqlalchemy import SQLAlchemy
except ImportError:  # pragma: no cover - fallback for test environments
    # Minimal stubs to allow module imports when Flask-SQLAlchemy isn't installed.
    class _DummyType:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyColumn:
        def __init__(self, *args, **kwargs):
            pass

    class _DummySession:
        def add(self, *args, **kwargs):
            return None

        def delete(self, *args, **kwargs):
            return None

        def commit(self, *args, **kwargs):
            return None

        def rollback(self, *args, **kwargs):
            return None

    class SQLAlchemy:  # type: ignore
        # Provide lightweight attributes used in model definitions.
        Model = object
        Column = _DummyColumn
        Integer = _DummyType
        BigInteger = _DummyType
        String = _DummyType
        DateTime = _DummyType
        Text = _DummyType
        Boolean = _DummyType
        Float = _DummyType
        Numeric = _DummyType
        JSON = _DummyType
        ForeignKey = _DummyType
        Enum = _DummyType
        Index = _DummyType

        def __init__(self, *args, **kwargs):
            self.Model = object
            self.Column = _DummyColumn
            self.Integer = _DummyType
            self.BigInteger = _DummyType
            self.String = _DummyType
            self.DateTime = _DummyType
            self.Text = _DummyType
            self.Boolean = _DummyType
            self.Float = _DummyType
            self.Numeric = _DummyType
            self.JSON = _DummyType
            self.ForeignKey = _DummyType
            self.Enum = _DummyType
            self.Index = _DummyType
            self.relationship = lambda *args, **kwargs: None
            self.session = _DummySession()

        def init_app(self, app):
            return None

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
