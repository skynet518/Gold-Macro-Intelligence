# Contributing

[简体中文](CONTRIBUTING.zh-CN.md) · [Home](README.md)

GMI is a small research project. The most helpful contributions are reproducible: a broken unit test, a documented mismatch in a CFTC category, a source release-time correction, or a clearer explanation of a limitation.

Before opening a pull request, please explain the research question and the exact change, include a minimal input that reproduces the behavior, and run `python3 -m unittest discover -s tests -v` in a clean source checkout. If your test needs restricted or third-party source data, **do not** attach that data to a public issue or PR; instead provide a lawful acquisition method and a synthetic fixture.

Keep data-source provenance and timestamp semantics intact. Do not introduce trade execution, undisclosed external requests, hidden credentials, fabricated performance figures or automatic bullish/bearish actions as a side effect of a software patch.

Code and original docs contributed to this project are intended to be distributed under its MIT license. Ensure you have the necessary rights before submitting material. For possible security issues, follow [SECURITY.md](SECURITY.md) rather than disclosing a vulnerability publicly.
