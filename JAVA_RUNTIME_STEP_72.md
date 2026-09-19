# Step 72 — Android OpenJDK runtime repair

- Enabled automatic Java 8 installation instead of forcing manual import.
- Switched runtime URLs to the versioned AngelAuraMC release tags: `download_jre8` for Java 8 and `release` for Java 17/21/25.
- Updated Java 25 SHA-256 values to the currently published release assets.
- Added verified Java 8 SHA-256 values for arm, arm64, x86 and x86_64.
- Kept archive path-traversal and runtime structure validation.
- Java 25 x86 remains unsupported because the upstream runtime release does not publish that architecture.

Upstream currently publishes Android JRE 8/17/21/25 assets for the supported architectures; Java 25 has no x86 package.
