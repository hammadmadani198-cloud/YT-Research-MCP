# Phase 8 dependency review - 2026-10-03 UTC

Python 3.12.14 and all 44 installed distributions match requirements-dev.lock; pip check passes. mcp 2.2.0, pydantic 2.13.5 and httpx 0.28.1 are the direct dependencies. No version was upgraded. Runtime/package versions are separately recorded in phase-8-dependency-inventory.json. Local wheel build of 0.9.0 succeeds without dependencies/network installation; the release bundle remains source-only.

This is a targeted current maintainer-advisory review, not an exhaustive CVE/SBOM scan. The selected published advisories below have patched versions at or below the installed pin. No matching unresolved issue was identified within this scope; do not infer absence of undisclosed or future vulnerabilities. Stdio deployment excludes remote HTTP/OAuth features, but pins are checked regardless.

| Package / installed | Selected official advisory | Patched version | Finding |
| --- | --- | --- | --- |
| mcp 2.2.0 | [GHSA-5h93-6whr-6q8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-5h93-6whr-6q8j) | 2.2.0 | Pin contains fix |
| mcp 2.2.0 | [GHSA-rwrf-2pqf-9j8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-rwrf-2pqf-9j8j) | 2.2.0 | Pin contains fix |
| mcp 2.2.0 | [GHSA-fmmv-w9g8-j3gc](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-fmmv-w9g8-j3gc) | 2.1.0 | Pin contains fix |
| mcp 2.2.0 | [GHSA-84m7-p3x7-pcfv](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-84m7-p3x7-pcfv) | 2.2.0 | Pin contains fix |
| mcp 2.2.0 | [GHSA-qx49-fqc8-xw99](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-qx49-fqc8-xw99) | 2.2.0 | Pin contains fix |
| starlette 1.7.0 | [GHSA-82w8-qh3p-5jfq](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq) | 1.3.1 | Pin contains fix |
| python-multipart 0.0.32 | [GHSA-5rvq-cxj2-64vf](https://github.com/Kludex/python-multipart/security/advisories/GHSA-5rvq-cxj2-64vf) | 0.0.30 | Pin contains fix |
| h11 0.16.0 | [GHSA-vqfr-h8mv-ghfj](https://github.com/python-hyper/h11/security/advisories/GHSA-vqfr-h8mv-ghfj) | 0.16.0 | Pin contains fix |
| anyio 4.15.1 | [GHSA-82r6-8w77-94w6](https://github.com/agronholm/anyio/security/advisories/GHSA-82r6-8w77-94w6) | 4.14.2 | Pin contains fix |
| anyio 4.15.1 | [GHSA-3w57-8xmc-8v26](https://github.com/agronholm/anyio/security/advisories/GHSA-3w57-8xmc-8v26) | 4.14.2 | Pin contains fix |
| PyJWT 2.15.1 | [GHSA-ffc3-869f-jxw9](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-ffc3-869f-jxw9) | 2.14.0 | Pin contains fix |
| PyJWT 2.15.1 | [GHSA-x33g-cr3x-6449](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-x33g-cr3x-6449) | 2.15.0 | Pin contains fix |
| cryptography 50.0.2 | [GHSA-jwv3-5hgf-82ww](https://github.com/pyca/cryptography/security/advisories/GHSA-jwv3-5hgf-82ww) | 49.0.0 | Pin contains fix |
| cryptography 50.0.2 | [GHSA-r6ph-v2qm-q3c2](https://github.com/pyca/cryptography/security/advisories/GHSA-r6ph-v2qm-q3c2) | 46.0.5 | Pin contains fix |

Reviewed [HTTPX](https://github.com/encode/httpx/security/advisories), [HTTPCore](https://github.com/encode/httpcore/security/advisories) and [Pydantic](https://github.com/pydantic/pydantic/security/advisories) maintainer indexes as well; HTTP indexes exposed no advisory entries in this review, and the Pydantic index lists a legacy datetime advisory. This limited index finding is not a general security guarantee. Package metadata lists upstream project URLs for further review. No pydantic-ai dependency is installed. No arbitrary upgrade was justified by these findings; any future dependency change requires renewed integration and restore checks.
