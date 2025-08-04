# Use official Python image as base
FROM python:3.10-slim

# Install system dependencies for Qt/PySide6 and virtual display
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt and PySide6 requirements
    libxkbcommon-x11-0 \
    libxkbcommon0 \
    libegl1 \
    libgl1 \
    libglx0 \
    libglvnd0 \
    libgles2 \
    libxcb1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libx11-xcb1 \
    libxcb-cursor0 \
    # VNC + Window manager (for GUI rendering in Gitpod)
    xvfb \
    x11vnc \
    fluxbox \
    # Additional common dependencies
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt-dev \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install Python dependencies
RUN pipenv install --system --deploy

# Copy application code
COPY . .

# Set default command 
CMD ["bash", "start_gui.sh"]
