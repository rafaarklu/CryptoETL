FROM apache/airflow:2.9.3-python3.11

USER root

WORKDIR /opt/airflow

COPY requirements.txt /tmp/requirements.txt
RUN chown airflow:0 /tmp/requirements.txt

USER airflow

RUN pip install --no-cache-dir -r /tmp/requirements.txt

USER root

COPY . /opt/airflow
RUN chown -R airflow:0 /opt/airflow
RUN rm /tmp/requirements.txt

USER airflow

