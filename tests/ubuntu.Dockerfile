FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -q && apt-get install -y --no-install-recommends \
    gcc-14 make pkg-config libibus-1.0-dev ibus dbus python3 neovim vim \
    ca-certificates libgtk-3-dev qtbase5-dev g++ xvfb xauth xdotool \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
RUN apt-get update -q && apt-get install -y --no-install-recommends ibus-gtk3 \
    && rm -rf /var/lib/apt/lists/*
CMD ["sh", "tests/ubuntu.sh"]
