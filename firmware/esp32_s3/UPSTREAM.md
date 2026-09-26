# XiaoZhi upstream provenance

- Upstream: <https://github.com/78/xiaozhi-esp32>
- Imported commit: `8ce50d27cd7c72c777673f46cbfc3ef7454d1b5c`
- Imported on: 2026-09-26
- License: MIT (see `LICENSE`)
- Supported SDK at import: ESP-IDF 6.0.1 or newer; ESP-IDF 6.1 recommended

The upstream tree is vendored so WheelBot can carry a reviewable custom board and
MCP integration in the same repository. WheelBot-specific changes are limited to
the `wheelbot-s3-audio` board, its selection entries, and project documentation.
When updating, import a deliberate upstream commit and review these integration
points instead of overwriting the directory blindly.
