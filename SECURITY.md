# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| develop | :white_check_mark: |
| main    | :white_check_mark: |
| < 0.1   | :x: |

## Reporting a Vulnerability

Please report security vulnerabilities through **GitHub Security Advisories (private vulnerability reporting)**:

- Repository **Security** tab → **Report a vulnerability**
- Direct link: https://github.com/zln02/urban-immune-system/security/advisories/new

GitHub Security Advisories provides an encrypted channel readable only by repository maintainers. Reports are acknowledged within 3 business days per the timeline below.

Do NOT open public issues for security concerns. Public disclosure before coordinated patching exposes operational systems (KDCA, local governments) consuming our alerts to active exploitation.

## Disclosure Timeline

| Day | Action |
|-----|--------|
| 0   | Initial report received |
| 1-3 | Acknowledgment + triage |
| 4-30 | Patch development + private review |
| 30+ | Coordinated public disclosure |

## Scope

In scope:
- backend/ (FastAPI endpoints, auth, middleware)
- pipeline/ (data collection, normalization)
- ml/ (inference service)
- infra/k8s/ (security context, secrets handling)

Out of scope:
- Dependencies (report to upstream)
- Test code (tests/)
