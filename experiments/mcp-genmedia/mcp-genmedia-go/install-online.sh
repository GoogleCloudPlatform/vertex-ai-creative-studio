#!/usr/bin/env bash
set -e

# GenMedia MCP Servers Online Installation Script
# This script downloads and installs the pre-compiled binaries for your OS and Architecture.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/GoogleCloudPlatform/vertex-ai-creative-studio/main/experiments/mcp-genmedia/mcp-genmedia-go/install-online.sh | bash

REPO="GoogleCloudPlatform/vertex-ai-creative-studio"
INSTALL_DIR="$HOME/.local/bin"
ARCHIVE_PREFIX="genmedia-mcp-servers"

echo_info() { printf "\033[1;34m==>\033[0m %s\n" "$1"; }
echo_success() { printf "\033[1;32m==>\033[0m %s\n" "$1"; }
echo_err() { printf "\033[1;31mError:\033[0m %s\n" "$1" >&2; }

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *) echo_err "Unsupported architecture: $ARCH"; exit 1 ;;
esac

OS_TITLE="$(tr '[:lower:]' '[:upper:]' <<< ${OS:0:1})${OS:1}"
if [ "$ARCH" = "amd64" ]; then ARCH_MAP="x86_64"; else ARCH_MAP="$ARCH"; fi

LATEST_URL="https://api.github.com/repos/${REPO}/releases"
echo_info "Checking GitHub for the latest MCP release..."

if command -v curl >/dev/null 2>&1; then
    RELEASE_DATA=$(curl -sL "$LATEST_URL")
else
    RELEASE_DATA=$(wget -qO- "$LATEST_URL")
fi

TAG=$(echo "$RELEASE_DATA" | grep '"tag_name": "mcp-v' | head -n 1 | cut -d '"' -f 4)

if [ -z "$TAG" ]; then
    echo_err "Could not find a valid mcp-v* release tag on GitHub."
    echo_err "Make sure an automated release has been published for the MCP servers."
    exit 1
fi
echo_info "Found version: ${TAG}"

TARBALL="${ARCHIVE_PREFIX}_${OS_TITLE}_${ARCH_MAP}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}/${TARBALL}"

echo_info "Downloading ${TARBALL}..."
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

if command -v curl >/dev/null 2>&1; then
    curl -sL -f "$DOWNLOAD_URL" -o "$TMP_DIR/$TARBALL" || { echo_err "Failed to download $DOWNLOAD_URL. The binaries for your architecture might not be available yet."; exit 1; }
else
    wget -qO "$TMP_DIR/$TARBALL" "$DOWNLOAD_URL" || { echo_err "Failed to download $DOWNLOAD_URL."; exit 1; }
fi

echo_info "Extracting binaries..."
tar -xzf "$TMP_DIR/$TARBALL" -C "$TMP_DIR"

mkdir -p "$INSTALL_DIR"
# Install Gemini Extensions if present in the tarball
if [ -d "$TMP_DIR/gemini-extensions" ]; then
    echo ""
    read -p "Are you using Gemini CLI? Would you like to install the Google GenMedia extensions for it? (y/N): " install_ext
    case "$install_ext" in
        [yY]|[yY][eE][sS])
            echo_info "Installing Gemini CLI Extensions..."
            GEMINI_EXT_DIR="$HOME/.gemini/extensions"
            mkdir -p "$GEMINI_EXT_DIR"
            cp -R "$TMP_DIR/gemini-extensions/"* "$GEMINI_EXT_DIR/"
            echo_success "Extensions installed to $GEMINI_EXT_DIR"
            echo_info "Restart Gemini CLI and run '/extensions list' to configure them!"
            ;;
        *)
            echo_info "Skipping Gemini CLI extensions installation."
            ;;
    esac
fi


echo_info "Installing binaries to ${INSTALL_DIR}..."
mv "$TMP_DIR"/mcp-*-go "$INSTALL_DIR/" 2>/dev/null || true
if ls "$INSTALL_DIR"/mcp-*-go 1> /dev/null 2>&1; then
    chmod +x "$INSTALL_DIR"/mcp-*-go
else
    echo_err "No binaries found in the archive."
    exit 1
fi

echo_success "Installation successful!"
echo_info "The following servers were installed:"
ls -1 "$INSTALL_DIR"/mcp-*-go | xargs -n 1 basename | sed 's/^/  - /'

if [[ ! ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo -e "\033[1;33mWARNING: Your PATH does not include $INSTALL_DIR\033[0m"
    echo "To run these servers, please add the following to your shell configuration file (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
fi
