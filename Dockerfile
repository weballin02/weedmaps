FROM multiarch/crossbuild

# Set the working directory
WORKDIR /app

# Copy all files from the local directory to the container
COPY . .

# Install necessary dependencies for cross-compilation
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wine64 \
    wine32 \
    mingw-w64 \
    && rm -rf /var/lib/apt/lists/*

# Install PyInstaller
RUN pip3 install --no-cache-dir pyinstaller

# Set the wine environment for Windows cross-compilation
ENV WINEARCH=win64
ENV WINEPREFIX=/root/.wine

# Build the Windows executable
RUN wine python3 -m PyInstaller --onefile windows_order_scraper.py

# Set the entry point to be the compiled executable
CMD ["/bin/bash"]
