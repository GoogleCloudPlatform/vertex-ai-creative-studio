---
title: "Migration Guide"
---

If you previously installed the `google-genmedia` extension before we introduced interactive settings and bundled skills, follow these steps to cleanly upgrade your setup.

## 1. Re-install the MCP Server Binaries

First, ensure you have the latest MCP Go binaries, which include the new `mcp-nanobanana-go` server and the updated default models.

Navigate to the `mcp-genmedia-go` directory and run the installer:

```bash
cd ../../mcp-genmedia-go
./install.sh
```
Select "Install All".

## 2. Update the Gemini CLI Extension

Because the new extension format uses interactive `.env` settings instead of hardcoded JSON `env` blocks, the cleanest path is to uninstall the old extension and install the new one.

```bash
# 1. Uninstall the existing extension
gemini extensions uninstall google-genmedia-extension

# 2. Install the new extension (from the geminicli directory)
cd ../sample-agents/geminicli
gemini extensions install ./sample_extensions/google-genmedia
```

*Note: The new extension is named `google-genmedia` instead of `google-genmedia-extension`.*

## 3. Provide Your Settings

During the installation step above, Gemini CLI will interactively ask you for your Google Cloud configuration:

```text
? Google Cloud Project ID: [Enter your project ID]
? GenMedia GCS Bucket: [Enter gs://your-bucket]
```

These are stored securely in `~/.gemini/extensions/google-genmedia/.env`. You no longer need to edit JSON files manually!

## 4. (Optional) Cleanup Old Settings

If you previously added the servers directly to your global `~/.gemini/settings.json` file instead of using the extension folder, you can safely open that file and remove the `mcpServers` block (unless you are using it for other servers). The new extension handles loading the GenMedia servers automatically.

## 5. Restart and Test

Restart the Gemini CLI. You can verify the new features by typing:

```text
/extensions list
```
*(You should see `google-genmedia` installed)*

```text
/skill producer
```
*(You should see the new producer skill activate)*
