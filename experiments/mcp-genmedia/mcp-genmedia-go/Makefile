# Makefile for the mcp-genmedia-go servers.
#
# The single source of truth for the version is the VERSION file in this
# directory. It is injected into each server's `main.version` variable at build
# time via -ldflags, so the per-file `version` const no longer needs hand-editing.
#
# For released artifacts, goreleaser injects the git tag instead (see
# .goreleaser.yaml); this Makefile is for local and CI builds.

VERSION := $(shell cat VERSION)
LDFLAGS := -s -w -X main.version=$(VERSION)
BIN_DIR := bin

# All server modules (each is `package main`).
SERVERS := \
	mcp-veo-go \
	mcp-nanobanana-go \
	mcp-chirp3-go \
	mcp-gemini-go \
	mcp-lyria-go \
	mcp-avtool-go \
	mcp-imagen-go \
	mcp-omni-go

.PHONY: all build clean version vet $(SERVERS)

all: build

## build: compile every server into ./bin with the VERSION injected.
build: $(SERVERS)

$(SERVERS):
	@echo "Building $@ (version $(VERSION))..."
	@cd $@ && GOWORK=off go build -ldflags "$(LDFLAGS)" -o ../$(BIN_DIR)/$@ .

## vet: run go vet across every server module.
vet:
	@for s in $(SERVERS); do \
		echo "go vet $$s..."; \
		(cd $$s && GOWORK=off go vet ./...) || exit 1; \
	done

## version: print the version that will be injected.
version:
	@echo $(VERSION)

## clean: remove built binaries.
clean:
	@rm -rf $(BIN_DIR)
