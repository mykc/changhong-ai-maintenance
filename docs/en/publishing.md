# Manual publishing and maintenance

[中文（主要版本）](../publishing.md) · [Home](../../README.en.md)

The release directory is `changhong-ai-maintenance`, also a suggested repository name. Publish only its public files, not adjacent private backups, old working folders or raw logs. The release does not depend on the original computer paths.

## Before publishing

- Chinese is primary, with complete English counterparts. Human entry points are `README.md` / `README.en.md`; AI entry points are `agent.md` / `agent.en.md` and `AGENTS.md`.
- Read the [disclaimer](../../DISCLAIMER.en.md) and choose a license yourself. A disclaimer is not a LICENSE; no license does not imply unrestricted reuse.
- Exclude actual IPs, personal paths, actual Termux UIDs, private/public keys, known_hosts, Wi-Fi passwords, tokens, raw screenshots/logs, firmware and APKs.
- `.gitignore` does not remove tracked files or secrets from history. Check `git ls-files` and history when relevant.
- Users obtain third-party tools and APKs from trusted sources. Case fingerprints identify those versions only and do not replace source verification.

## Offline validation and packaging

Run from the repository root. These commands do not contact the TV:

```text
python -B -m unittest discover -s tests -v
python -B scripts/tvctl.py --help
python -B scripts/policy_lists.py --help
python -B scripts/tvctl.py emergency-stop --ip 192.0.2.10
python -B scripts/check_release.py
python -B scripts/check_release.py --check --zip
```

The sample IP is reserved for documentation. The preview omits `--execute`. `-B` prevents Python from generating bytecode caches containing local paths; it does not remove existing caches. If Bash is available, also run `bash -n scripts/termux-ssh.sh`.

`check_release.py` accepts only explicitly listed public files, checks language-pair existence, local file links, common sensitive-data patterns, and UTF-8 without BOM / LF formatting, then refreshes `SHA256SUMS`. `.gitattributes` fixes LF endings so a clone on another system retains the same bytes. `--check` verifies existing checksums; `--zip` creates a ZIP beside the directory. Review new public files and update the script's file inventory. Ignored `.local/`, caches and work directories are excluded; other unexpected files fail validation.

Automated scanning cannot detect every secret; manually inspect staged content. Offline tests do not replace device acceptance tests; see [validation](validation.md).

## Push manually to GitHub

Create the GitHub repository yourself, then run the following in the release directory after replacing the remote URL:

```text
git init
git add README.md README.en.md agent.md agent.en.md AGENTS.md DISCLAIMER.md DISCLAIMER.en.md docs scripts tests .gitignore .gitattributes SHA256SUMS
git diff --cached --stat
git diff --cached
git commit -m "Document AI-assisted Changhong TV maintenance"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

These are instructions only; no remote, commit or push was created for this delivery. For web upload, extract the verified release ZIP into a new directory and upload only that public content, including `.gitignore` and `.gitattributes`. GitHub web uploads do not apply `.gitignore`; do not drag in a working directory where scripts have run, because it may contain caches, `.local/` backups or keys. Adding LICENSE also requires updating the release script's allowed file inventory.

## Add new cases

Collect model, full firmware build, SDK, app version/signature, user objective, minimal reproduction, exact changes, backup, recovery and the evidence source for each result. Mark untested items explicitly. Record different models separately instead of expanding the original case's claims.

Update English with Chinese, especially authorization, recovery, parameters and limitations. Have an independent reviewer inspect the repository without the original conversation. Fix findings, rerun relevant offline checks and refresh checksums. Do not contact the user's TV merely to review documentation.
