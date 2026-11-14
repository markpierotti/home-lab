#!/usr/bin/env python3
"""Run the exact provisioned expression in promtool, without production metrics."""
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    deploy = Path(__file__).resolve().parents[1]
    cfg = json.loads((deploy / 'etc/grafana/provisioning/alerting/slim-rules.yaml').read_text())
    rule = next(r for g in cfg['groups'] for r in g['rules'] if r['uid'] == 'router-rebooted')
    expr = rule['data'][0]['model']['expr']
    labels = '{job="router",instance="fixture"}'
    base = {'rtax_router_uptime_seconds': '10000+30x30', 'up': '1+0x30',
            'rtax_exporter_up': '1+0x30', 'rtax_last_attempt_success': '1+0x30',
            'rtax_last_sample_timestamp_seconds': '0+30x30'}
    reset = '10000+30x14 30+30x15'
    cases = [('steady uptime', {}, 0),
             ('positive and negative boot jitter', {'rtax_router_boot_time_seconds': '10000+0x10 10001+0x9 10000+0x9'}, 0),
             ('real reset', {'rtax_router_uptime_seconds': reset}, 1),
             ('short prior uptime reset', {'rtax_router_uptime_seconds': '10+1x14 1+30x15'}, 1),
             ('scrape outage', {'up': '0+0x30', 'rtax_router_uptime_seconds': reset}, None),
             ('exporter unhealthy', {'rtax_exporter_up': '0+0x30'}, None),
             ('collection failing', {'rtax_last_attempt_success': '0+0x30'}, None),
             ('stale collection', {'rtax_last_sample_timestamp_seconds': '0+0x30'}, None),
             ('future clock timestamp', {'rtax_last_sample_timestamp_seconds': '10000+0x30'}, None),
             ('non-finite uptime', {'rtax_router_uptime_seconds': 'NaN+0x30'}, None),
             ('negative uptime', {'rtax_router_uptime_seconds': '-1+0x30'}, None),
             ('only one uptime observation', {'rtax_router_uptime_seconds': '_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 5'}, None),
             ('scrape gap then increasing uptime', {'rtax_router_uptime_seconds': '10000+30x9 _ _ _ _ _ _ _ _ _ _ 10600+30x10'}, 0)]
    for metric in base:
        cases.append(('missing ' + metric, {metric: None}, None))
    cases.append(('all metrics missing', {k: None for k in base}, None))
    tests = []
    for name, overrides, expected in cases:
        series = {**base, **overrides}
        samples = [] if expected is None else [{'labels': '{instance="fixture",job="router"}', 'value': expected}]
        tests.append({'name': name, 'interval': '30s',
                      'input_series': [{'series': k + labels, 'values': v} for k, v in series.items() if v is not None],
                      'promql_expr_test': [{'expr': expr, 'eval_time': '15m', 'exp_samples': samples}]})
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'tests.json'
        path.write_text(json.dumps({'rule_files': [], 'evaluation_interval': '30s', 'tests': tests}))
        subprocess.run(['promtool', 'test', 'rules', str(path)], check=True)
    print(f'{len(tests)} exact-expression fixtures passed')


if __name__ == '__main__':
    main()
