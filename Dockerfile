# App image: the study web app. It never executes learner code itself when RUNNER_URL is set.
FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY skill_thermostat ./skill_thermostat
COPY pilot ./pilot
RUN pip install --no-cache-dir numpy scipy flask anthropic && useradd -r -u 10001 app && mkdir /data && chown app /data
USER app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/srv
EXPOSE 8001
CMD ["python", "-m", "pilot.study_app", "--db", "/data/study.db", "--host", "0.0.0.0", "--port", "8001"]
