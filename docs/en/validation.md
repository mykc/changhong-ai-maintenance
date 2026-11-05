# Validation record

[中文（主要版本）](../validation.md) · [Home](../../README.en.md)

Prepared on 2026-11-05. Repository editing, translation and review took place offline on the computer; this work did not reconnect to or modify the TV.

## Device evidence

Tools checked Aerial installation, permissions, guard state and later background permission; physical HOME and reboot success were reported by the user. Tools checked Yecao installation, launch, raw policy files, ownership/mode and in-memory policy; the subsequent installation test was reported successful by the user. See [evidence](evidence.md) and the [Yecao case](yecao.md).

Yecao policy persistence after reboot, long-term vendor refresh and compatibility with every target APK remain untested. Permanent root and SSH/ADB boot startup were not configured.

## Tool boundaries

The existing `tvctl.py` connection and recovery logic has offline device-simulator tests. Generalized recovery scripts were not rerun against the final working TV. New `policy_lists.py` only supports read-only capture/verification and offline planning; it has no device-write action, and its tests do not contact the TV.

Final offline acceptance results:

- Python 3.12 collected 41 tests: 40 passed and 1 was skipped because Windows did not permit creating real symlinks; simulated symlink checks passed.
- Bash syntax, CLI help and the non-executing recovery preview passed.
- Local file links, anchors, code fences and language pairing passed for all 33 Markdown documents.
- All 41 public source files passed privacy-pattern and UTF-8 without BOM / LF checks; SHA256SUMS was generated separately. The ZIP contains 42 files and passed integrity and checksum checks, without caches or private records.

This revision corrected a test that depended on Python parser recursion behavior: deeply nested JSON must be safely rejected by either the parser or snapshot schema, without requiring identical error wording across Python versions. New rejection tests cover similar versions, different BuildTime values and custom build suffixes.

## Independent review

After the draft was complete, an independent agent with no inherited conversation context read only the release directory and reviewed all 33 Markdown documents, 4 scripts, 2 test files and publishing configuration. The review covered human procedures, AI boundaries, bilingual consistency, recovery, evidence and privacy. It did not access the TV or private working records.

The following findings were fixed and the independent reviewer rechecked all four revisions:

| Finding | Revision |
| --- | --- |
| Consecutive manual ADB commands could enter ordinary shell after root failed | Made the bounded tool the main path and added separate success gates for manual diagnosis |
| Firmware substring matching accepted unverified similar builds | Require the complete exact build and add rejection tests |
| Web uploads could include bytecode caches containing local paths | Remove caches, use `python -B` in examples, and limit web uploads to extracted release ZIP content |
| Windows line-ending conversion could invalidate checksums | Fix all text to LF and check raw byte formatting |

Follow-up documentation also adds English meanings for Chinese tool messages, clarifies that snapshots do not store device identity, requires retained post-change snapshots, and explains limits on security-context comparison. The independent review found no remaining P1/P2 issues. Review does not replace device testing or provide a security or legal guarantee.

After edits, run `python -B scripts/check_release.py`, then `--check --zip` to verify and package current checksums.
