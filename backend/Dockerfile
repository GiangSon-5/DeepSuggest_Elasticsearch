# Sử dụng base image Python 3.10
FROM python:3.10-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

# Cài đặt chỉ các thư viện cần thiết cho backend nhẹ
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt 

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]