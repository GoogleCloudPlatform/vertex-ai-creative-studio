#!/bin/bash

# This script provides a convenient way to install or upgrade the Go MCP servers
# in this project. It performs the following actions:
#
# 1. Discovers all available MCP servers (directories matching 'mcp-*-go').
# 2. Checks if Go is installed and provides instructions if it is not.
# 3. Checks if the user's PATH includes the Go binary directory and provides
#    instructions on how to add it if it is missing.
# 4. Presents an interactive menu to install a specific server or all of them.
# 5. Compiles and installs the selected server(s) using 'go install'.

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#
# Function to find all MCP servers.
#
# This function searches for all directories in the current directory that match
# the pattern 'mcp-*-go' and prints them to standard output.
find_mcp_servers() {
  find . -mindepth 1 -maxdepth 1 -type d -name 'mcp-*-go' | sed 's|./||'
}

#
# Function to check if Go is installed.
#
# This function checks if the 'go' command is available in the system's PATH.
# If it is not found, it prints an error message and exits the script.
check_go_installation() {
  if ! command -v go &> /dev/null; then
    echo -e "${RED}Go is not installed.${NC}"
    echo "Please install it from the official website: https://go.dev/dl/"
    echo "After installation, make sure that the Go binary is in your PATH, then run this script again."
    exit 1
  fi
}

#
# Function to check and configure the PATH.
#
# This function checks if the user's PATH includes the Go binary directory
# ($HOME/go/bin). If it does not, it prints a warning and instructions on how
# to add it to the user's shell configuration file.
check_path() {
  if [[ ! ":$PATH:" == *":$HOME/go/bin:"* ]]; then
    echo -e "${YELLOW}WARNING: Your PATH does not include the Go binary directory ($HOME/go/bin).${NC}"
    echo "The MCP server binaries will be installed there."
    echo "To run them from your command line, please add the following line to your shell configuration file (e.g., ~/.bashrc, ~/.zshrc):"
    echo ""
    echo -e "  ${BLUE}export PATH=\"\$PATH:$HOME/go/bin\"${NC}"
    echo ""
    echo "You will need to restart your shell or run 'source <your_config_file>' for the change to take effect."
    read -p "Press Enter to continue, or Ctrl+C to exit and configure your PATH."
  fi
}

#
# Main function.
#
# This is the main entry point of the script. It calls the other functions to
# perform the installation process.
main() {

  if [[ -z "${PROJECT_ID}" ]]; then
    echo -e "${YELLOW}PROJECT_ID not set, attempting to retrieve from gcloud config...${NC}"
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "${PROJECT_ID}" ]]; then
      echo -e "${RED}ERROR: Could not retrieve PROJECT_ID from gcloud. Please set it manually.${NC}"
      echo "For example: export PROJECT_ID=your-gcp-project-id"
      exit 1
    else
      echo -e "${GREEN}Successfully retrieved PROJECT_ID: ${PROJECT_ID}${NC}"
      export PROJECT_ID
    fi
  fi

  check_go_installation
  check_path

  echo -e "${BLUE}Please choose an MCP server to install:${NC}"
  select server in $(find_mcp_servers) "Install All" "Exit"; do
    case $server in
      "Install All")
        echo -e "${BLUE}Installing all MCP servers...${NC}"
        for d in $(find_mcp_servers); do
          echo "Installing $d..."
          # Run go mod tidy to prevent checksum mismatch errors
          if ! (cd "$d" && go mod tidy && go install); then
            echo -e "${RED}ERROR: Failed to install $d. Please check the output above for details.${NC}"
            exit 1
          fi
        done
        echo -e "${GREEN}All MCP servers have been installed successfully.${NC}"
        break
        ;;
      "Exit")
        echo "Exiting."
        exit 0
        ;;
      *) 
        if [ -n "$server" ]; then
          echo -e "${BLUE}Installing $server...${NC}"
                    # Run go mod tidy to prevent checksum mismatch errors
          if (cd "$server" && go mod tidy && go install); then
            echo -e "${GREEN}$server has been installed successfully.${NC}"
          else
            echo -e "${RED}ERROR: Failed to install $server. Please check the output above for details.${NC}"
            exit 1
          fi
        else
          echo -e "${RED}Invalid selection.${NC}"
        fi
        break
        ;;
    esac
  done
}

main
