def test_text_mode_uses_multimodal_processor_message_format(monkeypatch):
    """Regression: a string system content crashes Qwen's real chat processor."""
    import torch
    from tokenizers import Tokenizer, models
    from transformers import (
        Qwen2TokenizerFast,
        Qwen2VLImageProcessorFast,
        Qwen3VLProcessor,
        Qwen3VLVideoProcessor,
    )

    from evidencedoc.inference import LocalQwen

    tokenizer = Qwen2TokenizerFast(
        tokenizer_object=Tokenizer(
            models.WordLevel(
                {"[UNK]": 0, "ok": 1, "<|image_pad|>": 2, "<|video_pad|>": 3}, unk_token="[UNK]"
            )
        ),
        unk_token="[UNK]",
    )
    processor = Qwen3VLProcessor(
        image_processor=Qwen2VLImageProcessorFast(),
        tokenizer=tokenizer,
        video_processor=Qwen3VLVideoProcessor(),
        chat_template="{% for m in messages %}{% for c in m['content'] %}{{ c['text'] }}{% endfor %}{% endfor %}",
    )

    class MinimalGeneration:
        def generate(self, **kwargs):
            return torch.cat([kwargs["input_ids"], torch.tensor([[1]])], dim=-1)

    engine = LocalQwen()
    engine.processor, engine.model, engine.device = processor, MinimalGeneration(), "cpu"
    monkeypatch.setattr(engine, "_load", lambda: None)
    assert engine.generate("Ağırlık?", [{"page": 1, "text": "Atlas 8 kg."}], "text") == "ok"
