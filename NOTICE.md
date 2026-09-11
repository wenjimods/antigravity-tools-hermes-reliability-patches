# Notice and Attribution

## Antigravity Manager

- Upstream: https://github.com/lbjlaq/Antigravity-Manager
- Author: lbjlaq and contributors.
- Baseline: v4.6.7, commit prefix `4987bfb`; exact supported file hashes are recorded beside the patch.
- License: CC-BY-NC-SA 4.0; complete upstream license retained in `LICENSE`.
- This kit is an unofficial modification, not an upstream release or endorsement.

AGT changes replace the 5-second acquisition guard with a 40-second overall budget, use a 1-second per-account lock budget and a 15-second OAuth budget, reread token state after locking, and allow preferred/main selection to move away from refresh failures. The configuration helper separately reduces the background refresh interval to 2 minutes. These changes do not eliminate quota exhaustion, regional restrictions, upstream outages, or every HTTP 503.

## Hermes Agent

- Upstream: https://github.com/NousResearch/hermes-agent
- Copyright (c) 2025 Nous Research.
- License: MIT; the notice below applies to upstream Hermes code included in patches and fixtures. The kit's root CC license does not remove the upstream MIT grant.
- The client patch handles `All accounts limited. Wait Ns` as upstream rate limiting and waits `N + 1` before a bounded retry. It does not fix AGT OAuth refresh itself.

### Hermes MIT notice

MIT License

Copyright (c) 2025 Nous Research

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Distribution boundary

Original kit additions retain the root CC-BY-NC-SA 4.0 license. Third-party notices remain applicable to their respective material. No account database, credentials, private logs, installed executable or production configuration is part of this kit. Commercial use of AGT-derived material requires checking the upstream noncommercial restriction; this kit is not a grant of commercial permission.
