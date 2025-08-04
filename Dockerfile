# Use official Python image as base
FROM python:3.10-slim

# Install system dependencies for Qt/PySide6 and other requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Qt/PySide6 dependencies
    libxkbcommon-x11-0 \
    libxkbcommon0 \
    libxcb-xinerama0 \
    libegl1 \
    libgl1 \
    libglx0 \
    libglvnd0 \
    libgles2 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xkb1 \
    # Other potential dependencies
    libssl-dev \
    libffi-dev \
    # For Pillow
    libjpeg-dev \
    zlib1g-dev \
    # For pandas (optional)
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*


# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install Python dependencies
RUN pipenv install --system --deploy

# Copy application code
COPY . .

# Command to run the application
CMD ["python", "ui/main_window.py"]