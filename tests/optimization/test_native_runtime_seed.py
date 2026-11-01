import os
from utopia.utils.seeding import set_seed


def test_runtime_rng_seed_does_not_overwrite_actual_python_startup_seed(monkeypatch):
    monkeypatch.setenv('PYTHONHASHSEED', '42')
    actual = hash('scienceutopia.native-world.v1')
    set_seed(1301, use_torch=False)
    assert os.environ['PYTHONHASHSEED'] == '42'
    assert hash('scienceutopia.native-world.v1') == actual


def test_runtime_rng_seed_does_not_claim_to_pin_missing_startup_hash_seed(monkeypatch):
    monkeypatch.delenv('PYTHONHASHSEED', raising=False)
    set_seed(1301, use_torch=False)
    assert 'PYTHONHASHSEED' not in os.environ
