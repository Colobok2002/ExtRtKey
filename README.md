Созать окружение

```
poetry config virtualenvs.in-project true 
poetry env remove pythonrm -rf .venv
poetry env use python3
poetry install
```

uvicorn app_name.main:app --port 8080 --reload



alembic revision --autogenerate

alembic upgrade head
