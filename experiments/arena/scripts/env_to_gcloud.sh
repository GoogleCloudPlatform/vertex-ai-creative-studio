#!/bin/bash

# Script to convert a .env file into a gcloud --set-env-vars argument string.
# Usage: ./env_to_gcloud.sh [path/to/.env.file]
# If no path is provided, it defaults to looking for '.env' in the current directory.
# Example: gcloud run deploy my-service --image gcr.io/my-project/my-image $(./env_to_gcloud.sh .env.prod) --region us-central1

# --- Configuration ---
# Set the default environment file path
DEFAULT_ENV_FILE=".env"

# --- Argument Parsing ---
# Use the first argument as the ENV_FILE path if provided, otherwise use the default.
ENV_FILE="${1:-$DEFAULT_ENV_FILE}"

# --- File Validation ---
# Verify that the environment file exists and is readable.
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file '$ENV_FILE' not found." >&2 # Print errors to stderr
    exit 1
fi
if [ ! -r "$ENV_FILE" ]; then
    echo "Error: Environment file '$ENV_FILE' is not readable." >&2
    exit 1
fi

# --- Processing ---
# Initialize an empty array to hold the processed KEY=VALUE pairs.
declare -a env_vars_array

# Read the environment file line by line using a while loop and process substitution.
# This approach is generally safer for handling various line endings and special characters.
while IFS= read -r line || [[ -n "$line" ]]; do
    # Trim leading/trailing whitespace from the line using sed.
    trimmed_line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Skip empty lines and lines that start with '#' (comments).
    if [[ -z "$trimmed_line" ]] || [[ "$trimmed_line" =~ ^# ]]; then
        continue
    fi

    # Use regex to capture the key and value parts from lines like KEY=VALUE.
    # The key must start with a letter or underscore, followed by letters, numbers, or underscores.
    # The value is everything after the first '=' sign.
    if [[ "$trimmed_line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"

        # Remove potential surrounding quotes (single or double) from the value.
        # Check for double quotes first.
        if [[ "$value" =~ ^\"(.*)\"$ ]]; then
            # Extract content within double quotes.
            value="${BASH_REMATCH[1]}"
        # Then check for single quotes.
        elif [[ "$value" =~ ^\'(.*)\' ]]; then
            # Extract content within single quotes.
            value="${BASH_REMATCH[1]}"
        fi
        # Note: This doesn't handle escaped quotes within the value itself.
        # gcloud might require specific escaping for complex values.

        # Add the formatted KEY=VALUE pair to the array.
        env_vars_array+=("$key=$value")
    else
        # Warn about lines that don't match the expected KEY=VALUE format.
        echo "Warning: Skipping malformed line in '$ENV_FILE': $trimmed_line" >&2
    fi
done < "$ENV_FILE"

# --- Output Generation ---
# Check if any environment variables were successfully processed.
if [ ${#env_vars_array[@]} -eq 0 ]; then
    echo "Warning: No valid environment variables found in '$ENV_FILE'. No output generated." >&2
    exit 0 # Exit successfully, but indicate nothing was found.
fi

# Join the array elements into a single string, separated by commas.
# Using printf ensures each element is treated as a separate argument,
# preventing issues if values contain spaces or special characters interpreted by the shell.
# However, commas *within* values might still be an issue for gcloud itself.
joined_vars=$(printf "%s," "${env_vars_array[@]}")

# Remove the trailing comma that results from the printf command.
joined_vars=${joined_vars%,}

# Output the final gcloud flag string. This can be used directly in a gcloud command.
# Example: gcloud run deploy ... $(./this_script.sh) ...
echo "--set-env-vars $joined_vars"

exit 0

