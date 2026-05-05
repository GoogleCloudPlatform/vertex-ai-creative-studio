
---

**`references/manual-build.md`**
```markdown
# Manual Build Reference

Use these commands if `scripts/build.sh` fails for any reason.

## 1. Install Go

```bash
GO_VERSION="1.26.2"
curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tar.gz
rm -rf /tmp/go
tar -xf /tmp/go.tar.gz -C /tmp
rm /tmp/go.tar.gz
/tmp/go/bin/go version   # should print: go version go1.26.2 linux/amd64

