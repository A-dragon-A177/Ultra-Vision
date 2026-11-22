FROM python:3.12-slim
WORKDIR /vision
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# libatomic1 is required by Playwright's Node.js runtime on slim images
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/*

# Install Playwright browser binaries + system deps
RUN python -m playwright install chromium --with-deps

COPY app ./app
ENV VISION_HOME=/vision PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.main"]
