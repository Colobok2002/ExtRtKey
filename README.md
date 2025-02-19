Созать окружение

```
poetry config virtualenvs.in-project true 
poetry env remove pythonrm -rf .venv
poetry env use python3
poetry install
```

uvicorn ext_rt_key.main:app --port 8080 --reload

alembic revision --autogenerate

alembic upgrade head
