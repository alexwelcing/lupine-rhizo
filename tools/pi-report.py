#!/usr/bin/env python3
"""Render a private PI cycle with explicit completed, stopped, and pending stages."""
import argparse
import html
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit


def esc(value):
    return html.escape(str(value), quote=True)


def paragraphs(value):
    if isinstance(value, list):
        return '<ul>' + ''.join('<li>' + paragraphs(item) + '</li>' for item in value) + '</ul>'
    if isinstance(value, dict):
        return '<dl>' + ''.join('<dt>' + esc(key.replace('_', ' ')) + '</dt><dd>' + paragraphs(item) + '</dd>' for key, item in value.items()) + '</dl>'
    return '<p>' + esc(value) + '</p>'


def render(ledger, cycle_id, notes=None):
    db = sqlite3.connect('file:' + str(Path(ledger).resolve()) + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    row = db.execute('SELECT * FROM scientific_pi_cycles WHERE cycle_id=?', (cycle_id,)).fetchone()
    if not row:
        raise ValueError('The cycle is not recorded in this ledger')
    stages = {r['stage']: r for r in db.execute('SELECT * FROM scientific_pi_stages WHERE cycle_id=?', (cycle_id,))}
    if row['status'] != 'completed':
        result = render_incomplete(row, stages, Path(ledger).resolve().parent, notes)
        db.close()
        return result
    if set(stages) != {'discovery', 'independent_critique', 'pi_decision'}:
        raise ValueError('Missing a completed research stage')
    decision = json.loads(row['decision_json'])
    proposal = json.loads(stages['discovery']['result_json'])
    critique = json.loads(stages['independent_critique']['result_json'])
    source_items = []
    for source in proposal['sources']:
        url = urlsplit(source['url'])
        if source['url'] == 'urn:lupine:' + stages['discovery']['job_id'] + ':context' and source['publication_kind'] == 'primary_research_report':
            source_items.append(f'<li><strong>{esc(source["title"])}</strong><p>{esc(source["supports"])}</p><small>Provided research brief; not an independently retrieved publication</small></li>')
            continue
        if url.scheme != 'https' or not url.netloc or url.username or url.password:
            raise ValueError('Unsafe source URL')
        source_items.append(f'<li><a href="{esc(source["url"])}" rel="noreferrer">{esc(source["title"])}</a><p>{esc(source["supports"])}</p><small>{esc(source["publication_kind"].replace("_", " "))} · {esc(source["year"])}</small></li>')
    receipt_cards = []
    for key, title in [('discovery', 'Codex · Mac · discovery'), ('independent_critique', 'Claude · aledev · independent critique'), ('pi_decision', 'Codex · Mac · PI decision')]:
        receipt = json.loads(stages[key]['receipt_json'])
        model = receipt.get('model') or receipt.get('model_requested') or 'CLI did not return the model identifier'
        if isinstance(model, list):
            model = ', '.join(model)
        receipt_cards.append(f'<article><h3>{title}</h3><p>Completed {esc(receipt["finished_at"])}</p><small>{esc(model)}</small><dl><dt>Job</dt><dd><code>{esc(receipt["job_id"])}</code></dd><dt>Session</dt><dd><code>{esc(receipt["session_id"])}</code></dd><dt>Result fingerprint</dt><dd><code>{esc(receipt["result_sha256"])}</code></dd></dl></article>')
    content = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Lupine · PI discovery cycle</title>
<style>body{{margin:0;background:#f6f3eb;color:#17291f;font:17px/1.55 system-ui,sans-serif}}main{{max-width:1040px;margin:auto;padding:48px 24px 80px}}header small{{letter-spacing:.12em;text-transform:uppercase;color:#566952}}h1{{font-size:clamp(32px,4.3vw,52px);line-height:1.14;max-width:940px;margin:16px 0 24px}}h2{{font-size:26px;line-height:1.3}}h3{{font-size:18px}}p{{margin:.4em 0 1em}}.status{{display:inline-block;background:#dfe8c6;border-radius:30px;padding:7px 14px;font-weight:650}}.notice{{padding:15px 20px;border-left:4px solid #9c7b37;background:#efe6cf;margin:24px 0}}section{{margin-top:34px;padding:26px;background:#fffdf6;border:1px solid #d7ddce;border-radius:16px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}article{{background:#f0f2e8;padding:18px;border-radius:12px;min-width:0}}dt{{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:#5a6954;margin-top:12px}}dd{{margin:4px 0 14px}}code{{font:12px/1.4 ui-monospace,monospace;overflow-wrap:anywhere}}a{{color:#21664a;text-underline-offset:3px}}details{{margin-top:18px}}summary{{cursor:pointer;font-weight:650}}li{{margin:14px 0}}small{{color:#56634e}}footer{{margin-top:35px;font-size:13px;color:#56634e}}.decision{{border:2px solid #608252}}</style>
<main><header><small>Lupine Rhizo / private research notebook</small><h1>{esc(decision['revised_hypothesis'])}</h1><span class="status">PI decision: {esc(decision['recommendation'].replace('_',' '))}</span><p style="margin-top:20px">{esc(decision['reason'])}</p></header>
<div class="notice">A completed research discussion, with real Codex and Claude runs. The proposed experiment has not run. Novelty is unverified. Library publication is held.</div>
<section class="decision"><h2>The next discriminating test</h2>{paragraphs(decision['cheap_discriminating_experiment'])}<h3>What would refute it</h3><p>{esc(decision['falsifier'])}</p></section>
<section><h2>What the independent critic changed</h2><p><strong>Claude's verdict:</strong> {esc(critique['verdict'].replace('_',' '))}</p><p>{esc(critique['strongest_alternative'])}</p>{paragraphs(decision['response_to_critique'])}<details><summary>Read Claude's full independent critique</summary>{paragraphs(critique)}</details></section>
<section><h2>Where this meets published research</h2><p>{esc(decision['closest_prior_art_boundary'])}</p><ul>{''.join(source_items)}</ul><details><summary>Read the initial Codex proposal</summary>{paragraphs(proposal)}</details></section>
<section><h2>Verified handoffs</h2><div class="grid">{''.join(receipt_cards)}</div></section><footer>Cycle {esc(cycle_id)} · {esc(row['finished_at'])} · Local private ledger · No automatic experiment execution or publication</footer></main></html>'''
    db.close()
    return content


def render_incomplete(row, stages, state, notes=None):
    """A proposal is useful evidence, but never promote it to an adjudicated result."""
    proposal = json.loads(stages['discovery']['result_json']) if 'discovery' in stages else None
    hypotheses = proposal.get('proposals', []) if proposal else []
    headline = 'A research direction, awaiting independent review'
    if hypotheses:
        headline = hypotheses[0]['hypothesis']
    stage_cards = []
    for key, suffix, title in [('discovery', 'discovery', '1 · Codex reads and proposes'),
                               ('independent_critique', 'critique', '2 · Claude challenges'),
                               ('pi_decision', 'decision', '3 · Codex decides')]:
        if key in stages:
            receipt = json.loads(stages[key]['receipt_json'])
        else:
            path = state / (row['cycle_id'] + '-' + suffix) / 'receipt.json'
            receipt = json.loads(path.read_text()) if path.is_file() else None
        if not receipt:
            stage_cards.append(f'<article><h3>{title}</h3><strong>Not started</strong><p>No result is implied.</p></article>')
            continue
        status = receipt['status']
        description = 'A validated research packet was received.' if status == 'completed' else 'No validated answer was received. This request will not be repeated.'
        proof = {key: receipt.get(key) for key in ['job_id', 'provider', 'model', 'session_id', 'started_at', 'finished_at', 'duration_seconds', 'result_sha256', 'completion_unknown']}
        if proof['model'] is None:
            proof['model'] = 'Not returned by the CLI'
        stage_cards.append(f'<article><h3>{title}</h3><strong>{esc(status.replace("_", " "))}</strong><p>{description}</p><details><summary>Execution record</summary>{paragraphs(proof)}</details></article>')
    source_items = []
    for source in proposal.get('sources', []) if proposal else []:
        url = urlsplit(source['url'])
        if url.scheme == 'https' and url.netloc and not url.username and not url.password:
            title = f'<a href="{esc(source["url"])}" rel="noreferrer">{esc(source["title"])}</a>'
        else:
            title = esc(source['title']) + ' · supplied internal brief'
        source_items.append(f'<li>{title}<p>{esc(source["supports"])}</p><small>{esc(source["limitations"])}</small></li>')
    proposed = ''.join(f'<h3>{esc(p["id"])} · Proposed test</h3>{paragraphs(p["cheap_discriminating_experiment"])}<h3>What would refute it</h3><p>{esc(p["falsifier"])}</p><details><summary>Prior art, competing explanations and novelty boundary</summary>{paragraphs({k:p[k] for k in ["closest_prior_art", "competing_explanations", "possible_novelty", "novelty_status"]})}</details>' for p in hypotheses)
    question = esc(row['question'])
    display_title = esc(notes.get('title', 'An idea to put to the test')) if isinstance(notes, dict) else 'An idea to put to the test'
    stage_status = 'Proposal received · independent review incomplete' if hypotheses else 'Discovery incomplete'
    annotation = '<section><h2>Local audit and next action</h2>' + paragraphs(notes) + '</section>' if notes else ''
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Lupine · Private PI notebook</title>
<style>body{{margin:0;background:#f4f1e8;color:#203629;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:48px 24px 70px}}h1{{font-size:clamp(26px,3.5vw,40px);line-height:1.25;margin:16px 0 24px}}h2{{font-size:25px}}h3{{font-size:18px}}header small{{letter-spacing:.12em;text-transform:uppercase}}.status{{display:inline-block;padding:6px 14px;border-radius:30px;background:#ece0bd;font-weight:650}}.notice{{padding:18px 22px;background:#efe4c8;border-left:4px solid #987e43;margin:26px 0}}section{{background:#fffdf7;border:1px solid #d7dece;border-radius:16px;padding:24px;margin-top:26px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}article{{padding:18px;background:#eef1e5;border-radius:12px;min-width:0}}dt{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:16px;color:#647059}}dd{{margin:4px 0 12px;overflow-wrap:anywhere}}p{{margin:.5em 0 1em}}a{{color:#216148;text-underline-offset:3px}}small{{color:#637159}}li{{margin:18px 0}}details{{margin-top:18px}}summary{{cursor:pointer;font-weight:600}}footer{{margin-top:30px;color:#647059;font-size:13px}}</style>
<main><header><small>Lupine Rhizo / private PI notebook</small><h1>{display_title}</h1><p><strong>Hypothesis:</strong> {esc(headline)}</p><span class="status">{stage_status}</span><p>{question}</p></header>
<div class="notice">Codex's proposal is available to inspect. Claude did not return a validated critique, so no PI decision has been made. No experiment has run and novelty is unverified. Library publication remains held.</div>
<section><h2>The purpose of this loop</h2><p>Read published work, find the boundary of what is known, propose a test that can disprove a new idea, and have another agent challenge it before committing resources.</p><div class="grid">{''.join(stage_cards)}</div><p><small>{esc(row['error'] or '')}</small></p></section>
<section><h2>The proposed discriminating test</h2>{proposed or '<p>No validated proposal is available.</p>'}</section>
{annotation}<section><h2>Published research and its limits</h2><ul>{''.join(source_items)}</ul></section>
<footer>Cycle {esc(row['cycle_id'])} · {esc(row['finished_at'] or 'in progress')} · Private local evidence · No automatic retry or publication</footer></main></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--cycle-id', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--notes', help='Optional private JSON notes with explicit reviewer attribution')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    notes = json.loads(Path(args.notes).read_text()) if args.notes else None
    output.write_text(render(args.ledger, args.cycle_id, notes))
    output.chmod(0o600)
    print(json.dumps({'report': str(output), 'published': False}))
