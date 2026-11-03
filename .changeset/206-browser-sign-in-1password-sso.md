---
operating-doctrine: patch
---

Browser Automation and Ember Browser Routing now let any AI sign in on Ember's M2 without waiting for Allison when 1Password in Chrome offers a saved login or a site offers Sign in with Google or another single sign-on for an account already signed in there (Decision Log 2026-11-03, AI uses the sign-ins Allison set up, without waiting for her). 1Password fills the credential itself, so no session reads a password with `op` for a browser sign-in. A sign-in page by itself is no longer a block or a human-only action. MFA, CAPTCHA and human approval screens still are, and new account access, live releases, messages outside approved campaigns and anything irreversible still need Allison's yes.
