# Wake-word models (empty by default)

This fork ships **no** hotword model. Two engines are available:

- **sherpa (default)** — sherpa-onnx open-vocabulary keyword spotting. The
  ``wake_word.phrase`` (default ``hey tino``) is BPE-tokenized at runtime against
  a small KWS model that is downloaded once (~13 MB). Any phrase works, no
  training needed.
- **openwakeword (optional)** — point ``wake_word.openwakeword.model`` at your
  own trained model file, or use a built-in openWakeWord name
  (``hey_jarvis``, ``alexa``, ``hey_mycroft``, …). Drop a custom model here as
  ``<name>.onnx`` / ``<name>.tflite`` and reference it by ``<name>``.

See ``website/docs/user-guide/features/wake-word.md`` for setup and the training
guide.
