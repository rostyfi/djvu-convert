FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LC_ALL=C.UTF-8 \
    HOST=0.0.0.0 \
    PORT=5000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/calibre.txz https://download.calibre-ebook.com/8.5.0/calibre-8.5.0-x86_64.txz

# calibre's bundled lib/ contains its own libssl/libcrypto — setting
# LD_LIBRARY_PATH globally would shadow the system OpenSSL and break pip and
# the app's HTTPS calls. Use a wrapper so only ebook-convert sees it.
# QT_QPA_PLATFORM=offscreen lets calibre's Qt run headless (no X server).
RUN mkdir -p /opt/calibre \
    && tar -xJf /tmp/calibre.txz -C /opt/calibre \
    && rm /tmp/calibre.txz \
    && chmod -R a+rX /opt/calibre \
    && printf '#!/bin/sh\nexport LD_LIBRARY_PATH=/opt/calibre/lib\nexport QT_QPA_PLATFORM=offscreen\nexec /opt/calibre/bin/ebook-convert "$@"\n' > /usr/local/bin/ebook-convert \
    && chmod +x /usr/local/bin/ebook-convert

# Runtime libraries: djvulibre renders the DJVU pages. calibre's bundled Qt
# (PyQt6.QtGui and friends, imported by the MOBI output plugin) needs EGL,
# GLX/OpenGL, fontconfig and freetype from the system. WeasyPrint (PDF output)
# needs Pango/HarfBuzz, and the PDF body text needs a real font.
RUN apt-get update \
    && apt-get install -y --no-install-recommends djvulibre-bin \
       libxcb1 libx11-6 libxkbcommon0 \
       libegl1 libopengl0 libglx0 libfontconfig1 libfreetype6 \
       libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
       fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY book_converter ./book_converter
COPY templates ./templates
RUN chmod -R a+rX /app

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2)" || exit 1

CMD ["python", "app.py"]
