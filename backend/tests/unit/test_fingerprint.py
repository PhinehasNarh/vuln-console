from vulnconsole.contexts.normalization.domain.fingerprint import compute_fingerprint


def test_fingerprint_is_deterministic() -> None:
    kwargs = {
        "finding_class": "sast",
        "rule_key": "semgrep:python.sqli",
        "asset_key": "org/repo",
        "location_key": "app/db.py",
    }
    assert compute_fingerprint(**kwargs) == compute_fingerprint(**kwargs)


def test_fingerprint_changes_with_each_component() -> None:
    base = compute_fingerprint(
        finding_class="sast",
        rule_key="semgrep:python.sqli",
        asset_key="org/repo",
        location_key="app/db.py",
    )
    variants = [
        compute_fingerprint(
            finding_class="sca",
            rule_key="semgrep:python.sqli",
            asset_key="org/repo",
            location_key="app/db.py",
        ),
        compute_fingerprint(
            finding_class="sast",
            rule_key="semgrep:python.xss",
            asset_key="org/repo",
            location_key="app/db.py",
        ),
        compute_fingerprint(
            finding_class="sast",
            rule_key="semgrep:python.sqli",
            asset_key="org/other",
            location_key="app/db.py",
        ),
        compute_fingerprint(
            finding_class="sast",
            rule_key="semgrep:python.sqli",
            asset_key="org/repo",
            location_key="app/other.py",
        ),
    ]
    assert len({base, *variants}) == 5


def test_fingerprint_is_hex_sha256() -> None:
    value = compute_fingerprint(
        finding_class="sast", rule_key="a", asset_key="b", location_key="c"
    )
    assert len(value) == 64
    int(value, 16)
