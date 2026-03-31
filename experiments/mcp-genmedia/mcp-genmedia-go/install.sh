#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
  # Imagen deprecation as of June 30, 2026
  find . -mindepth 1 -maxdepth 1 -type d -name 'mcp-*-go' ! -name 'mcp-imagen-go' | sed 's|./||'
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
# Function to setup Agent Skills.
#
setup_agent_skills() {
  SKILLS_DIR="$(cd "$(dirname "$0")/../skills" && pwd)"
  if [ -d "$SKILLS_DIR" ]; then
    echo -e "\n${BLUE}Expert Agent Skills found at:${NC} $SKILLS_DIR"
    
    # Check if gemini CLI is installed for remote installation tip
    if command -v gemini &> /dev/null; then
      echo -e "${YELLOW}Tip: You can also install these skills remotely via Gemini CLI:${NC}"
      echo -e "  ${BLUE}gemini skills install https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git --path experiments/mcp-genmedia/skills${NC}\n"
    fi

    # Gemini CLI
    if [ -d "$HOME/.gemini" ]; then
      read -p "Would you like to link these skills to Gemini CLI locally? (y/N): " link_gemini
      case "$link_gemini" in
        [yY]|[yY][eE][sS])
          mkdir -p "$HOME/.gemini/skills"
          # Link all skill directories
          for skill in "$SKILLS_DIR"/*/; do
            if [ -d "$skill" ] && [ -f "${skill}SKILL.md" ]; then
              skill_name=$(basename "$skill")
              ln -sfn "$skill" "$HOME/.gemini/skills/$skill_name"
              echo -e "${GREEN}Linked $skill_name to Gemini CLI${NC}"
            fi
          done
          ;;
      esac
    fi

    # Antigravity
    if [ -d "$HOME/.gemini/antigravity" ]; then
      read -p "Would you like to install these skills for Antigravity? (y/N): " install_agy
      case "$install_agy" in
        [yY]|[yY][eE][sS])
          mkdir -p "$HOME/.gemini/antigravity/skills"
          cp -R "$SKILLS_DIR"/* "$HOME/.gemini/antigravity/skills/"
          echo -e "${GREEN}Skills installed to Antigravity global directory${NC}"
          ;;
      esac
    fi
  fi
}

#
# Main function.
#
# This is the main entry point of the script. It calls the other functions to
# perform the installation process.
main() {

  # Fallback to PROJECT_ID if GOOGLE_CLOUD_PROJECT is not set
  if [[ -z "${GOOGLE_CLOUD_PROJECT}" ]] && [[ -n "${PROJECT_ID}" ]]; then
    export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
  fi

  if [[ -z "${GOOGLE_CLOUD_PROJECT}" ]]; then
    echo -e "${YELLOW}GOOGLE_CLOUD_PROJECT not set, attempting to retrieve from gcloud config...${NC}"
    GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "${GOOGLE_CLOUD_PROJECT}" ]]; then
      echo -e "${RED}ERROR: Could not retrieve GOOGLE_CLOUD_PROJECT from gcloud. Please set it manually.${NC}"
      echo "For example: export GOOGLE_CLOUD_PROJECT=your-gcp-project-id"
      exit 1
    else
      echo -e "${GREEN}Successfully retrieved GOOGLE_CLOUD_PROJECT: ${GOOGLE_CLOUD_PROJECT}${NC}"
      export GOOGLE_CLOUD_PROJECT
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
        echo -e "\n${YELLOW}Reminder: Ensure ${BLUE}\$HOME/go/bin${YELLOW} is in your PATH to run the installed servers.${NC}"
        setup_agent_skills
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
            echo -e "\n${YELLOW}Reminder: Ensure ${BLUE}\$HOME/go/bin${YELLOW} is in your PATH to run the installed server.${NC}"
            setup_agent_skills
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
