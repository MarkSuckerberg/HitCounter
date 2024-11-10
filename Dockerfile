FROM python:3-slim

WORKDIR /usr/src/hitcounter

VOLUME /usr/src/hitcounter/data

COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "gunicorn", "--bind=172.17.0.2:8000", "--workers=4", "app:app"]
