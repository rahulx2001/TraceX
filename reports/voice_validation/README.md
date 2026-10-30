# Voice validation status

[results.json](results.json) records zero consented microphone turns and zero
human grades. It is a pending-status artifact, not a speech-quality score.

The generator is `scripts/voice_validation.py`; collection instructions and exact
evidence requirements are in [docs/voice-validation.md](../../docs/voice-validation.md).
The regression suites use synthetic samples/transports and are kept separate.
No recorded demo narration or simulated historical latency was imported as real
voice evidence.
