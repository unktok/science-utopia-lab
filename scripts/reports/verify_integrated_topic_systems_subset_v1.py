"""Verify an actual exact-subset rebuild of the reviewed topic-systems paper.

Reuse the full staged-input/text/bbox/every-page checks, not historical output
data. This is local cache-backed reconstruction, not inference reproduction.
"""
from scripts.reports import verify_integrated_staged_actual_subset_v1 as verifier


def main():
    verifier.POLICY = 'research/publication/paper-rebuild-allowlist-integrated-topic-systems-v1.json'
    verifier.RECEIPT = 'paper/integrated-topic-systems-build-v1.json'
    verifier.OUTPUT = 'research/results/integrated-topic-systems-rebuild-subset-verification-v1.json'
    verifier.SCHEMA = 'scienceutopia.integrated-topic-systems-subset-verification.v1'
    verifier.main()


if __name__ == '__main__':
    main()
