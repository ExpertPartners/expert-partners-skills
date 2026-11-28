---
operating-doctrine: patch
---

Add a macOS Keychain readiness helper so existing signed-in Chrome profiles can retain their saved state after windows close. Recover a locked login Keychain through 1Password without exposing credentials, creating profiles, restoring old tabs or opening a browser during the readiness check.
