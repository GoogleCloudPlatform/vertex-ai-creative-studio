# MCP Common

This package provides common functionality for the MCP services in this repository.

## Configuration

The `config.go` file provides a way to load configuration from environment variables. The `LoadConfig` function returns a `Config` struct that contains the following fields:

* `ProjectID`: The Google Cloud project ID.
* `Location`: The Google Cloud location/region for services (configured via `GOOGLE_CLOUD_LOCATION`, `LOCATION`, or server-specific overrides).
* `GenmediaBucket`: The Google Cloud Storage bucket for general media.

Additionally, the `GetGCSDownloadTimeout` function reads the `GCS_DOWNLOAD_TIMEOUT` environment variable to configure the timeout for GCS download operations. It accepts Go duration strings (e.g. `"30s"`, `"5m"`) and defaults to `5m`.

## Model Configuration

The `models.go` file provides a centralized, configuration-driven system for managing model-specific parameters and constraints for the various generative media tools.

### Overview

This system allows for easy maintenance and ensures consistency across all MCP servers. When a tool supports different models (e.g., `Imagen 3` vs. `Imagen 4`), the specific constraints for each model (like max image count, supported aspect ratios, etc.) are defined in this package.

### Key Components

*   **`...ModelInfo` Structs**: Data structures (`ImagenModelInfo`, `VeoModelInfo`) that define the unique constraints for each model family.
*   **`Supported...Models` Maps**: A map for each model family (`SupportedImagenModels`, `SupportedVeoModels`) that holds the specific constraint values for every supported model and its aliases.
*   **Helper Functions**:
    *   `Resolve...Model`: Finds the canonical model name from a user-provided name or alias (e.g., `ResolveImagenModel`).
    *   `Build...ModelDescription`: Generates a formatted string of all supported models and their constraints, suitable for use in an MCP tool's parameter description.

### Usage

When developing an MCP server that uses different models, you should:

1.  Define the model's properties in the appropriate `Supported...Models` map in `models.go`.
2.  Use the `Build...ModelDescription` function to dynamically create the `description` for the `model` parameter in your tool definition.
3.  In your tool's handler, use the `Resolve...Model` function to get the canonical model name and then retrieve its constraints from the map.
4.  Use these constraints to validate and adjust user input.

## File Utilities

The `file_utils.go` file provides utility functions for working with files. The following functions are provided:

* `PrepareInputFile`: This function prepares an input file for processing. It can handle both local files and files in Google Cloud Storage. If the file is in Google Cloud Storage, it will be downloaded to a temporary local file. The function returns the path to the local file and a cleanup function that should be called to remove the temporary file.
* `HandleOutputPreparation`: This function prepares for writing an output file. It creates a temporary local file and returns the path to the file, the final output filename, and a cleanup function.
* `ProcessOutputAfterFFmpeg`: This function processes the output of an FFmpeg command. It can move the output file to a specified local directory and/or upload it to Google Cloud Storage.
* `GetTail`: This function returns the last n lines of a string.
* `FormatBytes`: This function formats a size in bytes to a human-readable string (KB, MB, GB).

## GCS Utilities

The `gcs_utils.go` file provides utility functions for working with Google Cloud Storage. The following functions are provided:

* `DownloadFromGCS`: This function downloads a file from Google Cloud Storage to a local file.
* `UploadToGCS`: This function uploads a file to Google Cloud Storage.
* `ParseGCSPath`: This function parses a Google Cloud Storage URI and returns the bucket name and object name.

## OpenTelemetry

The `otel.go` file provides a function for initializing OpenTelemetry. The `InitTracerProvider` function initializes a tracer provider and returns it. The tracer provider can be used to create tracers and spans.

## Testing

To test the `mcp-common` package, run the following command from the `mcp-common` directory:

```
go test
```
