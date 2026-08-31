import os
import importlib
import json

import pytest


def reload_rules_module():
    # reload the rules module to pick up env var changes
    import backend.app.analysis.rules as rules
    importlib.reload(rules)
    return rules


def test_defaults_preserved():
    rules = reload_rules_module()
    # ensure DEFAULT_CONFIG values equal historical defaults
    assert rules.DEFAULT_CONFIG['saturation']['global']['warning'] == 0.90
    assert rules.DEFAULT_CONFIG['saturation']['global']['alert'] == 0.95
    assert rules.DEFAULT_CONFIG['saturation']['global']['critical'] == 0.98
    # CONFIG when no env var should equal DEFAULT_CONFIG
    assert rules.CONFIG == rules.DEFAULT_CONFIG


def test_env_override_changes_thresholds(tmp_path, monkeypatch):
    # prepare a JSON file overriding a nested threshold
    cfg = {'saturation': {'global': {'warning': 0.5, 'alert': 0.6}}}
    p = tmp_path / 'th.json'
    p.write_text(json.dumps(cfg))
    monkeypatch.setenv('ANALYSIS_THRESHOLDS', str(p))
    rules = reload_rules_module()
    assert rules.CONFIG['saturation']['global']['warning'] == 0.5
    assert rules.CONFIG['saturation']['global']['alert'] == 0.6
    # ensure unspecified values stay from default
    assert rules.CONFIG['saturation']['global']['critical'] == rules.DEFAULT_CONFIG['saturation']['global']['critical']


def test_defaults_not_mutated_on_override(tmp_path, monkeypatch):
    # ensure DEFAULT_CONFIG remains unchanged after an override is applied
    cfg = {'saturation': {'global': {'warning': 0.33, 'alert': 0.44}}}
    p = tmp_path / 'th2.json'
    p.write_text(json.dumps(cfg))
    monkeypatch.setenv('ANALYSIS_THRESHOLDS', str(p))
    rules = reload_rules_module()
    # CONFIG should reflect override
    assert rules.CONFIG['saturation']['global']['warning'] == 0.33
    assert rules.CONFIG['saturation']['global']['alert'] == 0.44
    # DEFAULT_CONFIG must remain equal to the historical defaults
    assert rules.DEFAULT_CONFIG['saturation']['global']['warning'] == 0.90
    assert rules.DEFAULT_CONFIG['saturation']['global']['alert'] == 0.95


def test_env_override_with_json_string(monkeypatch):
    js = json.dumps({'budget': {'warning_pct': 0.4, 'alert_pct': 0.5}})
    monkeypatch.setenv('ANALYSIS_THRESHOLDS', js)
    rules = reload_rules_module()
    assert rules.CONFIG['budget']['warning_pct'] == 0.4
    assert rules.CONFIG['budget']['alert_pct'] == 0.5
    # critical pct remains default
    assert rules.CONFIG['budget']['critical_pct'] == rules.DEFAULT_CONFIG['budget']['critical_pct']


def test_invalid_env_ignored(monkeypatch):
    # invalid JSON should be ignored and defaults kept
    monkeypatch.setenv('ANALYSIS_THRESHOLDS', 'not-a-json-or-file')
    rules = reload_rules_module()
    assert rules.CONFIG == rules.DEFAULT_CONFIG
