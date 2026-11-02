"""Independent scalar analytical scores for the one v13 conditional LR step."""
from __future__ import annotations

import math


def _close(actual, expected):
    if type(actual) not in (int, float) or not math.isfinite(actual) or not math.isclose(
            actual, expected, rel_tol=1e-10, abs_tol=1e-11):
        raise ValueError('independently derived conditional likelihood/gradient/update differs')


def analytic_draw(definition, weights, draw):
    """No autograd, sampler, native world or generated source execution."""
    scores, logq, prefix = {}, 0., {}
    for factor in definition['factors']:
        key = factor['id']
        choices = [c['id'] for c in factor['choices']]
        allowed = choices
        if 'support' in factor:
            rules = [r for r in factor['support'] if all(prefix.get(k) == v for k, v in r['when'].items())]
            if len(rules) != 1:
                raise ValueError('conditional support lacks exactly one explicit reachable rule')
            allowed = [choice for choice in choices if choice in rules[0]['allow']]
        selected = draw['assignment'][key]
        logits = weights['logits'][key]
        if selected not in allowed:
            raise ValueError('actual draw outside declared conditional support')
        score = [0.] * len(logits)
        if len(allowed) > 1:
            if factor['kind'] == 'bernoulli':
                x = logits[0]
                p = 1/(1+math.exp(-x)) if x >= 0 else math.exp(x)/(1+math.exp(x))
                action = int(selected == choices[1])
                score[0] = action-p
                logq += (-max(0., -x)-math.log1p(math.exp(-abs(x)))) if action else (
                    -max(0., x)-math.log1p(math.exp(-abs(x))))
            else:
                indices = [i for i, choice in enumerate(choices) if choice in allowed]
                maximum = max(logits[i] for i in indices)
                normalizer = math.fsum(math.exp(logits[i]-maximum) for i in indices)
                for i in indices:
                    score[i] = int(choices[i] == selected)-math.exp(logits[i]-maximum)/normalizer
                logq += logits[choices.index(selected)]-maximum-math.log(normalizer)
        scores[key], prefix[key] = score, selected
    continuous = []
    for coordinate, mean, z in zip(definition['continuous'], weights['continuous_mean'], draw['latent']):
        sigma = coordinate['sigma']
        continuous.append((z-mean)/sigma**2)
        logq += -.5*((z-mean)/sigma)**2-math.log(sigma)-.5*math.log(2*math.pi)
    _close(draw['conditional_latent_log_probability'], logq)
    return {'logits': scores, 'continuous_mean': continuous, 'log_probability': logq}


def conditional_update_proof(records):
    if not records:
        return {'status': 'initial-batch-not-complete', 'updates': 0}
    initial = records[0]
    if initial['generation_error']:
        return {'status': 'initial-vocabulary-invalid-no-estimator', 'updates': 0,
            'error': initial['generation_error']}
    report = initial['report']
    before, after = report['weights_before'], report['weights_after']
    scores = [analytic_draw(initial['definition'], before, draw) for draw in initial['draws']]
    valid = all(o and o['status'] == 'complete' and not o['metadata'].get('technical_failures')
                for o in initial['observations'])
    result = {'status': report['status'], 'updates': int(report['status'] == 'score-updated'),
        'scores': scores, 'weights_before': before, 'weights_after': after,
        'conditional_only': True, 'pathwise_source_or_world_derivative': False}
    if report['status'] == 'score-updated':
        if not valid or len(scores) != 2:
            raise ValueError('sole LOO update requires two valid IID native costs')
        costs = [o['loss'] for o in initial['observations']]
        advantage = [costs[0]-costs[1], costs[1]-costs[0]]
        gradient = {'logits': {key: [math.fsum(advantage[j]*scores[j]['logits'][key][i]
            for j in range(2))/2 for i in range(len(values))]
            for key, values in before['logits'].items()}}
        if before['continuous_mean']:
            gradient['continuous_mean'] = [math.fsum(advantage[j]*scores[j]['continuous_mean'][i]
                for j in range(2))/2 for i in range(len(before['continuous_mean']))]
        if set(report['gradient']) != set(gradient):
            raise ValueError('conditional gradient fields differ')
        for key, values in gradient['logits'].items():
            for i, value in enumerate(values):
                _close(report['gradient']['logits'][key][i], value)
                _close(after['logits'][key][i], before['logits'][key][i]-.1*value)
        for i, value in enumerate(gradient.get('continuous_mean', [])):
            _close(report['gradient']['continuous_mean'][i], value)
            _close(after['continuous_mean'][i], before['continuous_mean'][i]-.1*value)
        result.update(losses=costs, leave_one_out_advantages=advantage, independently_derived_gradient=gradient)
    elif before != after or report['gradient'] is not None:
        raise ValueError('invalid/no-coordinate batch must leave distribution explicitly unchanged')
    if len(records) > 1 and not records[1]['generation_error']:
        updated = records[1]
        if (updated['definition'] != initial['definition']
                or updated['version_sha256'] != initial['version_sha256']
                or updated['report']['weights_before'] != after
                or updated['report']['weights_after'] != after
                or updated['report']['gradient'] is not None):
            raise ValueError('fresh updated proposal changed G0 vocabulary/update or performed another update')
        result['fresh_updated_draw_scores'] = [analytic_draw(initial['definition'], after, draw)
            for draw in updated['draws']]
    if len(records) > 2 and not records[2]['generation_error']:
        final = records[2]
        if final['report']['gradient'] is not None or final['report']['weights_before'] != final['report']['weights_after']:
            raise ValueError('free G1 singleton must remain forward only')
        result['redesign_draw_scores'] = [analytic_draw(final['definition'], final['report']['weights_before'], draw)
            for draw in final['draws']]
    return result
