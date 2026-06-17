# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
where practical.

## [1.0.1] - 2026-06-17

### Changed

- Updated Docker-related GitHub Actions to current Node 24-compatible major versions.
- Changed Trivy scanning to report container security findings without blocking release publishing.

## [1.0.0] - 2026-06-17

### Added

- Added unit tests for formatting, metric history, rate calculation, and service parsing helpers.
- Added GitHub Actions test workflow for pushes and pull requests.
- Added Docker support with an Alpine-based hardened runtime image.
- Added Docker Compose configuration for local hardened container runs.
- Added Trivy container security scanning workflow.
- Added Docker Hub publish workflow for GitHub releases.
- Added MIT license.
- Added changelog.
