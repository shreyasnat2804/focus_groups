# LORA.md — Sector Model Fine-Tuning

## Architecture

Three sector-specific LoRA adapters on a shared Mistral-7B base:

```
mistral-7b-instruct-v0.3 (base, frozen)
  ├── lora-tech/       (tech sector adapter)
  ├── lora-financial/  (financial sector adapter)
  └── lora-political/  (political sector adapter)
```

Each adapter adds ~10-50MB on top of the 14GB base. Load/swap at inference time.

## Training Data Format

Each training example is a demographic-conditioned prompt → response:

```json
{
  "instruction": "You are a 28-year-old male software engineer with middle income. How would you react to Apple releasing a $3,500 VR headset?",
  "response": "Honestly, I think it's cool tech but way overpriced for what you get. I'd wait for the second gen when they've worked out the kinks and dropped the price. Most of my friends feel the same — we're interested but not $3,500 interested."
}
```

Training set: ~5k-10k examples per sector, curated from the tagged corpus.

## LoRA Config

```python
from peft import LoraConfig, get_peft_model, TaskType

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                          # rank — 16 is a good balance
    lora_alpha=32,                 # scaling factor, typically 2*r
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # attention layers
    bias="none",
)
```

## Training Script

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import get_peft_model
import torch

base_model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.3",
    torch_dtype=torch.bfloat16,
    load_in_4bit=True,             # QLoRA — fits in 24GB VRAM
    device_map="auto",
)

model = get_peft_model(base_model, lora_config)
model.print_trainable_parameters()  # Should be ~0.1-0.5% of total

training_args = TrainingArguments(
    output_dir=f"./sector_models/lora-{sector}",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,  # effective batch size = 32
    learning_rate=2e-4,
    bf16=True,
    logging_steps=10,
    save_strategy="epoch",
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
)
```

## Inference — Prediction Generation

```python
from peft import PeftModel

base = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3", ...)
model = PeftModel.from_pretrained(base, f"./sector_models/lora-{sector}")

def predict_sentiment(model, tokenizer, prompt, n_samples=10, temperature=0.7):
    """Generate n_samples responses and extract sentiment distribution."""
    responses = []
    for _ in range(n_samples):
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        output = model.generate(**inputs, max_new_tokens=256, temperature=temperature, do_sample=True)
        responses.append(tokenizer.decode(output[0], skip_special_tokens=True))
    return responses
```

**Key**: Generate 10 samples per prompt with temperature=0.7 to get a distribution, not a single point estimate.

## Training Commands

```bash
# On Lambda GPU (A100 40GB):
ssh lambda-gpu
tmux new -s training
cd ~/focus_groups

python3 src/train_lora.py \
    --sector tech \
    --base-model mistralai/Mistral-7B-Instruct-v0.3 \
    --data data/training/tech_examples.jsonl \
    --epochs 3 \
    --output sector_models/lora-tech/

# Upload checkpoint to GCS
gsutil cp -r sector_models/lora-tech/ gs://focusgroups-models/lora-tech/
```

## Pitfalls

- **QLoRA (4-bit) is required for A10 (24GB)**. Full bf16 Mistral-7B needs ~28GB. Use `load_in_4bit=True`.
- **A100 40GB can do bf16 without quantization** if you prefer higher quality.
- **Save adapters, not full model**: `model.save_pretrained()` on a PeftModel saves only the adapter (~50MB), not the full base.
- **Predictions must be saved before comparing to actuals**: Generate all predictions in a batch, save to `predictions.json`, then load actuals for comparison. This prevents data leakage.
- **Temperature matters**: Too low (0.1) gives degenerate repetitive outputs. Too high (1.5) gives nonsense. 0.7 is the starting point.
- **Don't fine-tune on test cases**: Training data must not overlap with the product launches you're predicting.
