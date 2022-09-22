FROM python:3.9-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN apt-get update \
    && apt-get -y install libpq-dev gcc
RUN python -m pip install -r requirements.txt
WORKDIR /app
COPY . /app
# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

CMD ["python", "manage.py","runserver", "0.0.0.0:8000"]