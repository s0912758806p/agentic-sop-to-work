# Hardening & Security Checklist

How this repo is protected, plus the one-time GitHub settings the owner should enable.
See also [`SECURITY.md`](../SECURITY.md), [`LICENSE`](../LICENSE), [`NOTICE`](../NOTICE).

> **Reality check.** This is a **public** repo meant to be installed by anyone — the code is
> readable and copyable *by design*. "Protection" here means **legal terms (MIT + attribution)**,
> **author provenance**, and **repo integrity** — not preventing copying.

## Already in place (in the repo)
- **MIT + enforced attribution** — `LICENSE`, `NOTICE`, and a per-file `SPDX-License-Identifier: MIT`
  + copyright header on every `.py` / `.tmpl`. Reusers must keep the notice — including single files
  (the kit is designed to be copied file-by-file).
- **Signed commits** — commits are SSH-signed; `git log --show-signature` shows a good signature.
- **CI gate** — `.github/workflows/ci.yml` validates the manifests + every plugin skill's frontmatter
  and runs the kit regression (`selftest` + `verify --all`) on every push / PR.
- **Security policy** — `SECURITY.md` (private vulnerability reporting; provided as-is; no secrets in examples).

## Enable in GitHub (owner, one-time — web UI)
1. **Verified commits** — Settings → *SSH and GPG keys* → *New SSH key* → **Key type: Signing Key** →
   paste the same `~/.ssh/id_ed25519.pub`. Signed commits then show **Verified**.
2. **Two-factor auth** — Settings → *Password and authentication* → enable. (Securing the account is the
   root of repo integrity.)
3. **Secret scanning + push protection** — repo Settings → *Code security and analysis* → enable both
   (free for public repos).
4. **Protect `main`** — repo Settings → *Rules → Rulesets* (or *Branches*): block force pushes,
   restrict deletions; optionally **require signed commits** and **require a pull request**.
   - ⚠️ If you require signed commits, set up SSH signing on every machine you push from (below), or
     pushes will be rejected.
5. **Minimal access** — Settings → *Collaborators*: keep it to just you.

## Set up commit signing on a new machine
```
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
```
(This repository already has these configured locally.)
