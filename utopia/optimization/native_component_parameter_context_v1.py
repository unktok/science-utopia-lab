"""Explicit counterfactual component parameters, not a native-world fixture.

Only parameters are rebound; original inputs/state/period/phase/randomness stay
literal. Candidate source is never interpreted or executed here.
"""
from utopia.system.design_patch import clone, digest

SCOPE = 'current-component-parameters-on-recorded-inputs-v1'
OPTION = 'post_edit_parameter_context_scope'
NOTE = ('Component probes use the CURRENT authored node parameters with RECORDED '
    'developer inputs, state, period, phase and random seed. This is a declared '
    'counterfactual component context, not the exact historical context or a new '
    'candidate world. Inputs/state/wiring may be inapplicable after other changes. '
    'Failures do not veto finish and passing does not establish native benefit. ')


def parameters(document, node_id):
    nodes = [n for n in document['mechanisms'] if n['mechanism_id'] == node_id]
    if len(nodes) != 1 or nodes[0]['implementation'] != 'code.python.v1':
        raise ValueError('one explicit current code component required')
    # Same literal projection used by register_code_mechanisms' native handler.
    return {k: clone(v) for k, v in nodes[0]['parameters'].items()
        if k not in {'code_artifact', 'runtime_image_id'}}


def binding(document, node_id):
    return {'scope': SCOPE, 'node_id': node_id, 'document_sha256': digest(document),
        'parameters': parameters(document, node_id)}


def project(recorded_context, parameter_context):
    if (not isinstance(parameter_context, dict) or set(parameter_context) != {
            'scope', 'node_id', 'document_sha256', 'parameters'}
            or parameter_context['scope'] != SCOPE
            or not isinstance(parameter_context['node_id'], str) or not parameter_context['node_id']
            or not isinstance(parameter_context['document_sha256'], str)
            or len(parameter_context['document_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in parameter_context['document_sha256'])
            or not isinstance(parameter_context['parameters'], dict)
            or {'code_artifact', 'runtime_image_id'} & parameter_context['parameters'].keys()):
        raise ValueError('explicit literal counterfactual parameter context required')
    return {**clone(recorded_context), 'parameters': clone(parameter_context['parameters'])}
