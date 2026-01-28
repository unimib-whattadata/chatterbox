FROM yanwk/comfyui-boot:xpu

WORKDIR /app

COPY . .

ENV PIP_PREFER_BINARY=1

# Upgrade pip and build tools
# Force uninstall existing numpy/ml_dtypes to avoid conflicts with system versions (e.g. numpy 2.x)
# Then install compatible versions
RUN pip install --no-cache-dir --upgrade pip setuptools wheel build &&     pip uninstall -y numpy ml_dtypes || true &&     pip install --no-cache-dir "numpy>=1.24.0,<2.0.0" "ml_dtypes>=0.5.0" "onnx>=1.16.0" &&     pip install --no-cache-dir fastapi uvicorn pydantic python-multipart &&     pip install --no-cache-dir -e .

ENV PORT=8000

EXPOSE 8000

# Run the API using uvicorn
CMD ["uvicorn", "chatterbox.api:app", "--host", "0.0.0.0", "--port", "8000"]
