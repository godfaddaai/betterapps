# REF-judge render worker. Brain (brain.py) stays on the Mac: it needs YouTube + the Codex login.
# Workers only read jobs/ and write out/, so they can run anywhere, as many as you like:
#   docker build -t dtv-refjudge .
#   docker run --rm -v $PWD/jobs:/app/jobs -v $PWD/out:/app/out dtv-refjudge      (repeat per core budget)
FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg python3 python3-pip tesseract-ocr ca-certificates fonts-noto-color-emoji fonts-liberation \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 libxkbcommon0 libxcomposite1 libxdamage1 \
      libxrandr2 libxfixes3 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --break-system-packages "opencv-python-headless<5"
RUN npm i -g hyperframes@0.8.79
WORKDIR /app
COPY render.py ./
COPY tpl ./tpl
COPY assets ./assets
ENV TMPDIR=/tmp
CMD ["python3", "render.py", "--queue"]
