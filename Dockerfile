FROM python:3.9-alpine

WORKDIR /app

EXPOSE 8080

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app

CMD ["python", "server.py", "-r", "0.1"]
