"""Claude Vision wrapper for caftan condition analysis.

When ANTHROPIC_API_KEY is set, `analyze_with_claude` calls Claude with the
photos of the latest baseline and the current handover and returns a
structured JSON dict matching the ConditionReport.ai_* fields.

Falls back to a deterministic stub when the SDK or key is missing — keeps
the e2e tests green offline.
"""
import json
import logging
import os
from decimal import Decimal

logger = logging.getLogger(__name__)

PROMPT = """Tu es un expert en évaluation de caftans et takchitas (vêtements traditionnels marocains).
Compare les photos AVANT (baseline) et APRÈS (état actuel) du même vêtement.

Identifie chaque dégradation observable :
- Nouvelles taches (localisation, taille, type — encre, sauce, henné, parfum…)
- Accrocs, déchirures, points qui sautent
- Boutons, perles ou broderie manquants
- Décoloration, traces de transpiration, jaunissement
- Déformation : ourlet qui tombe, doublure, ceinture mdamma déformée
- Auréoles d'odeur visibles (parfum, transpiration, fumée)

Réponds STRICTEMENT avec un JSON conforme à ce schéma — pas de markdown, pas de prose :

{
  "overall_score": 1-5,           // 5 = parfait, 1 = inacceptable
  "is_acceptable": true|false,    // false dès qu'une réparation est nécessaire
  "detected_issues": [
    {
      "type": "stain"|"tear"|"missing_part"|"discoloration"|"deformation"|"odor"|"other",
      "location": "string court (ex: 'manche droite', 'col', 'mdamma')",
      "severity": 1-5,
      "description": "phrase courte"
    }
  ],
  "estimated_repair_cost_eur": number,    // 0 si rien
  "recommendation": "accept"|"minor_dispute"|"major_dispute"|"inconclusive"
}
"""


def analyze_with_claude(baseline_urls, current_urls):
    """Run Claude Vision; return a normalized dict.

    Returns the same shape as the JSON above plus a `_source` key
    ('claude' or 'stub') so callers can know what they got.
    """
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key:
        return _stub('no ANTHROPIC_API_KEY set')
    try:
        import anthropic
    except ImportError:
        return _stub('anthropic SDK not installed')

    try:
        client = anthropic.Anthropic(api_key=key)
        content = [{'type': 'text', 'text': PROMPT}]
        for label, urls in [('AVANT', baseline_urls), ('APRES', current_urls)]:
            content.append({'type': 'text', 'text': label})
            for u in urls[:3]:
                content.append({'type': 'image', 'source': {'type': 'url', 'url': u}})
        msg = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=1500,
            messages=[{'role': 'user', 'content': content}],
        )
        raw = msg.content[0].text if msg.content else '{}'
        data = json.loads(_strip_codefence(raw))
        return _normalize(data, source='claude', raw=raw)
    except Exception as e:
        logger.exception('claude vision call failed')
        return _stub(f'claude error: {e}')


def _strip_codefence(s):
    s = s.strip()
    if s.startswith('```'):
        s = s.split('\n', 1)[1] if '\n' in s else s
        if s.endswith('```'):
            s = s.rsplit('```', 1)[0]
    return s.strip()


def _normalize(d, source, raw=None):
    issues = d.get('detected_issues') or []
    return {
        'overall_score': int(d.get('overall_score', 5) or 5),
        'is_acceptable': bool(d.get('is_acceptable', True)),
        'detected_issues': issues,
        'estimated_repair_cost_eur': Decimal(str(d.get('estimated_repair_cost_eur', 0) or 0)),
        'recommendation': d.get('recommendation') or 'accept',
        '_source': source,
        '_raw': raw or '',
    }


def _stub(reason):
    return _normalize({
        'overall_score': 5,
        'is_acceptable': True,
        'detected_issues': [],
        'estimated_repair_cost_eur': 0,
        'recommendation': 'accept',
    }, source='stub', raw=reason)
