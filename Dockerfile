FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user:user . .
USER user
ENV HF_HOME=/home/user/.cache/huggingface HOST=0.0.0.0 PORT=7860 TOKENIZERS_PARALLELISM=false
EXPOSE 7860
CMD ["python", "app.py"]
