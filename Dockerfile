FROM yanwk/comfyui-boot:xpu

WORKDIR /app

COPY . .

# Install dependencies including the package itself in editable mode
# Removed --no-deps so that dependencies in pyproject.toml (like librosa) are installed
RUN pip install --no-cache-dir fastapi uvicorn pydantic python-multipart &&     pip install --no-cache-dir -e .

ENV PORT=8000

EXPOSE 8000

# Run the API using uvicorn
CMD ["uvicorn", "chatterbox.api:app", "--host", "0.0.0.0", "--port", "8000"]
