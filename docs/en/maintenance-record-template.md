# Maintenance record template

[中文](../maintenance-record-template.md) · [Home](../../README.en.md)

Copy this template into `.local/` before filling it in. Write a separate sanitized summary for publication; do not publish the working record directly.

## Request and authorization

- Date, model, full firmware and SDK:
- Behavior the user wants:
- Authorized actions, prohibited actions and whether reboot is allowed:
- Expected effects and recovery method:

## Before changes

- Current maintenance channel, identity and device verification:
- Computer backup location:
- Original file bytes, SHA-256, ownership, mode, size and modification time:
- APK source, package name, version, signature and existing installation:
- Original launcher, relevant permissions and runtime state:

## Execution and verification

- Expected diff and actual diff:
- Whether the original files were confirmed unchanged immediately before writing:
- Bytes, permissions and actual system behavior after writing:
- Explicit success results from installation/recovery commands:
- User's exact feedback:
- Untested items:

## Completion and recovery

- Cleanup results for temporary files and installation packages:
- Computer backups retained:
- Current ADB/SSH status and limits on boot startup:
- Recovery steps and other new changes that must be preserved:
- Personal information, logs and screenshots excluded from the public summary:
