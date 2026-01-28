FROM yanwk/comfyui-boot:xpu

WORKDIR /app

COPY . .

ENV PIP_PREFER_BINARY=1

# Upgrade pip, setuptools, wheel, and build tools
# Explicitly install ml_dtypes and numpy first to ensure compatibility and prefer binaries
RUN pip install --no-cache-dir --upgrade pip setuptools wheel build &&     pip install --no-cache-dir "ml_dtypes>=0.5.0" "numpy>=1.24.0,<2.0.0" &&     pip install --no-cache-dir fastapi uvicorn pydantic python-multipart &&     pip install --no-cache-dir -e .

ENV PORT=8000

EXPOSE 8000

# Run the API using uvicorn
CMD ["uvicorn", "chatterbox.api:app", "--host", "0.0.0.0", "--port", "8000"]
