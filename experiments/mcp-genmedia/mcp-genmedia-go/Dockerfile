# Use the official Golang image to create a build artifact.
# This stage compiles the Go application.
FROM golang:1.26 as builder

WORKDIR /app

# Accept a build argument for the server name (e.g. mcp-imagen-go, mcp-avtool-go)
ARG SERVER_NAME
RUN if [ -z "$SERVER_NAME" ]; then echo "SERVER_NAME build arg is required" && exit 1; fi

# Copy the workspace files and all modules to compile.
COPY mcp-common/ mcp-common/
COPY ${SERVER_NAME}/ ${SERVER_NAME}/

# Build the binary inside the target module directory.
WORKDIR /app/${SERVER_NAME}
RUN CGO_ENABLED=0 GOOS=linux GOWORK=off go build -v -o /app/server-bin

# Use a minimal alpine image for the runtime.
FROM alpine:3.24

ARG SERVER_NAME
RUN apk --no-cache add ca-certificates \
    && if [ "$SERVER_NAME" = "mcp-avtool-go" ]; then \
         echo "Installing ffmpeg for avtool..." && apk --no-cache add ffmpeg; \
       fi

WORKDIR /app
COPY --from=builder /app/server-bin /app/server-bin

# Expose standard container port.
EXPOSE 8080

# Run the web service on container startup in HTTP transport mode.
# By default, the server will read the PORT environment variable to determine which port to bind to.
ENTRYPOINT ["/app/server-bin", "-transport", "http"]
