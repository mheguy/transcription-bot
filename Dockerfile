FROM python:3.11

WORKDIR /app

RUN pip install poetry

COPY poetry.lock pyproject.toml README.md .

RUN poetry install --no-root

COPY . .

RUN poetry install

RUN python sgu_tool/get_models.py
