"""Security corpus package for M5 (Security & Trust Oracle)."""

from .loader import load_all_instances, load_corpus_manifest, load_instance, list_instances
from .types import CWE_LABELS, CWEBucket, CorpusManifest, ExpectedCriticSignal, SecurityInstance

__all__ = [
    "CWEBucket",
    "CWE_LABELS",
    "CorpusManifest",
    "ExpectedCriticSignal",
    "SecurityInstance",
    "load_all_instances",
    "load_corpus_manifest",
    "load_instance",
    "list_instances",
]