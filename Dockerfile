FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py wsgi.py gunicorn.conf.py ./
COPY static ./static
RUN useradd --create-home mile && mkdir /data && chown mile:mile /data
USER mile
ENV MILE_DATA_DIR=/data
EXPOSE 8000
CMD ["gunicorn", "wsgi:application", "--config", "gunicorn.conf.py"]
