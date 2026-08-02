import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'partner-prospects.json').read_text())
LIVE = json.loads((ROOT / 'live-source-audit.json').read_text())
errors = []
checks = []

def require(condition, message):
    checks.append(message)
    if not condition:
        errors.append(message)

prospects = DATA.get('prospects', [])
ids = [item.get('id') for item in prospects]
selected = [item for item in prospects if item.get('priority_tier') in (1, 2)]
require(len(prospects) == 136, 'exactly 136 prospect records')
require(DATA.get('organization_count') == 136, 'organization_count remains 136')
require(len(ids) == len(set(ids)) == 136, 'all 136 IDs are unique')
require(all(re.fullmatch(r'P\d{3}', value or '') for value in ids), 'all IDs retain PNNN format')
require(Counter(item['priority_tier'] for item in selected) == Counter({1: 34, 2: 59}), 'tier coverage is 34 tier-1 and 59 tier-2')
require(set(LIVE.get('records', {})) == {item['id'] for item in selected}, 'live audit covers all 93 tier-1/2 IDs')

probed_urls = set()
for audit_record in LIVE.get('records', {}).values():
    for field_result in audit_record.values():
        if isinstance(field_result, dict) and 'requested_url' in field_result:
            probed_urls.add(field_result['requested_url'])
validated = [item for item in prospects if item.get('claim_validation', {}).get('status') == 'official-source-validated']
unprobed = []
for item in validated:
    top_url = item.get('official_source')
    if top_url and top_url not in probed_urls:
        unprobed.append(f"{item['id']}:official_source")
    for field_name in ('program_or_facility', 'decision_maker_or_team', 'recent_trigger', 'lupine_pipeline_mapping'):
        field = item.get(field_name)
        if isinstance(field, dict):
            field_url = field.get('official_source') or field.get('url')
            if field_url and field_url not in probed_urls:
                unprobed.append(f"{item['id']}:{field_name}")
require(not unprobed, f"every validated claim URL is probed in live-source-audit.json (missing: {unprobed[:5]})")

allowed_status = {'official-source-validated', 'needs-verification'}
verified_dates = 0
needs_dates = 0
mapping_values = []
for item in selected:
    rid = item['id']
    for field in ('program_or_facility', 'decision_maker_or_team', 'recent_trigger'):
        require(field in item and isinstance(item[field], dict), f'{rid} has {field} object')
        require(item[field].get('official_source', '').startswith('http'), f'{rid} {field} has official URL')
        audit = item.get('evidence_audit', {}).get(field, {})
        require(audit.get('status') in allowed_status, f'{rid} {field} has fail-closed status')
        require(audit.get('checked_on') == '2026-08-01', f'{rid} {field} records check date')
    target_text = json.dumps(item['decision_maker_or_team']).lower()
    require('routing hypothesis' not in target_text, f'{rid} decision-maker/team is not a routing hypothesis')
    target_status = item['evidence_audit']['decision_maker_or_team']['status']
    if target_status == 'official-source-validated':
        require('needs verification' not in target_text, f'{rid} validated target is concretely named')
    else:
        require('needs verification' in target_text, f'{rid} unresolved target is explicitly labeled')

    trigger = item['recent_trigger']
    trigger_status = item['evidence_audit']['recent_trigger']['status']
    if trigger_status == 'official-source-validated':
        verified_dates += 1
        require(bool(re.fullmatch(r'202[4-6]-\d{2}-\d{2}', trigger.get('date') or '')), f'{rid} validated trigger has full 2024-2026 date')
        require(not re.search(r'earnings|conference call|financial results|outlook|calendar|future target|on track', trigger.get('event', ''), re.I), f'{rid} validated trigger is substantive')
    else:
        needs_dates += 1
        require(trigger.get('date') is None, f'{rid} unverified trigger does not publish an unverified date')
        require('NEEDS VERIFICATION' in trigger.get('event', ''), f'{rid} unverified trigger is explicit')

    mapping = item.get('lupine_pipeline_mapping', {})
    mapping_values.append(mapping.get('prospect_need'))
    require(item['name'] in mapping.get('pipeline_stage', ''), f'{rid} mapping names the prospect')
    require(item['program_or_facility']['name'] in mapping.get('pipeline_stage', ''), f'{rid} mapping names the asset')
    require(item['program_or_facility']['name'] in mapping.get('prospect_need', ''), f'{rid} need is tied to the asset')
    require(mapping.get('lupine_proof_point') == '72.4% fewer DFT evaluations; measured execution guardrail: $14.65 per 129 anchors', f'{rid} economics match guardrail')
    require(mapping.get('lupine_sources') == ['https://lupine.science/articles/the-savings-stack/', 'https://library.lupine.science/#/read/z1-union-cost-ledger'], f'{rid} has direct Lupine proof URLs')

require(len(mapping_values) == len(set(mapping_values)) == 93, 'all 93 prospect-need mappings are unique')
require(verified_dates + needs_dates == 93, 'all 93 triggers are validated or fail-closed')

for tier, expected in ((1, 34), (2, 59)):
    path = ROOT / f'tier-{tier}-outreach-one-pager.md'
    text = path.read_text()
    headings = re.findall(r'^### (P\d{3}) —', text, re.M)
    require(len(headings) == len(set(headings)) == expected, f'tier-{tier} one-pager has exact record coverage')
    require(text.count('https://lupine.science/articles/the-savings-stack/') == expected, f'tier-{tier} one-pager links savings proof per record')
    require(text.count('https://library.lupine.science/#/read/z1-union-cost-ledger') == expected, f'tier-{tier} one-pager links cost ledger per record')
    require('routing hypothesis' not in text.lower(), f'tier-{tier} one-pager has no routing hypotheses')
    economics_text = '\n'.join(
        line for line in text.splitlines()
        if line.startswith('Cost guardrail:') or line.startswith('- **Lupine proof:**')
    )
    dollar_values = set(re.findall(r'\$\s*([0-9]+(?:\.[0-9]+)?)', economics_text))
    percent_values = set(re.findall(r'([0-9]+(?:\.[0-9]+)?)%', economics_text))
    require(dollar_values <= {'14.65'}, f'tier-{tier} one-pager has no unauthorized dollar economics')
    require(percent_values <= {'72.4'}, f'tier-{tier} one-pager has no unauthorized percentage economics')

summary = {
    'status': 'PASS' if not errors else 'FAIL',
    'checks': len(checks),
    'errors': errors,
    'records': len(prospects),
    'tier_1': 34,
    'tier_2': 59,
    'validated_triggers': verified_dates,
    'needs_verification_triggers': needs_dates,
    'official_source_validated_records': sum(item['claim_validation']['status'] == 'official-source-validated' for item in selected),
    'needs_verification_records': sum(item['claim_validation']['status'] == 'needs-verification' for item in selected),
}
(ROOT / 'validation-report.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
sys.exit(1 if errors else 0)
