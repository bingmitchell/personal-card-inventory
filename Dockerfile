FROM python:3.11-slim
WORKDIR /app
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir Flask==3.0.0 python-dotenv==1.0.0
COPY scripts/ .
EXPOSE 8000
CMD ["python", "forms.py"]
