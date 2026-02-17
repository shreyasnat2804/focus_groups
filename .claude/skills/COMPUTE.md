# COMPUTE.md — Lambda Instances & GPU Jobs

## Instance Types

| Task | Instance | GPU | Est. Cost |
|------|----------|-----|-----------|
| Scraping | Lambda CPU | None | ~$0.01/hr |
| Embeddings | Lambda GPU (1x A10) | 24GB VRAM | ~$0.75/hr |
| LoRA training | Lambda GPU (1x A100 40GB) | 40GB VRAM | ~$1.10/hr |
| Inference | Lambda GPU (1x A10) | 24GB VRAM | ~$0.75/hr |

## SSH Setup

```bash
# Add to ~/.ssh/config
Host lambda-cpu
    HostName <IP>
    User ubuntu
    IdentityFile ~/.ssh/lambda_key

Host lambda-gpu
    HostName <IP>
    User ubuntu
    IdentityFile ~/.ssh/lambda_key
```

## Environment Setup (on instance)

```bash
# First time setup
sudo apt update && sudo apt install -y tmux htop
pip install --upgrade pip
git clone <repo_url> ~/focus_groups
cd ~/focus_groups
pip install -r requirements.txt

# For GPU instances
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes peft sentence-transformers
```

## Running Jobs

Always use tmux for long-running jobs:

```bash
ssh lambda-gpu
tmux new -s embeddings
cd ~/focus_groups
python3 src/embed.py --batch-size 256
# Ctrl+B, D to detach
# tmux attach -t embeddings to re-attach
```

## Monitoring

```bash
# GPU usage
nvidia-smi -l 1

# Watch GPU memory
watch -n 1 nvidia-smi

# Process monitoring
htop
```

## Data Transfer

```bash
# Upload data to instance
scp data/export.csv lambda-gpu:~/focus_groups/data/

# Download results
scp lambda-gpu:~/focus_groups/output/embeddings.npy ./output/

# For large files, use gsutil through GCS as intermediary
gsutil cp gs://focusgroups-data/corpus.csv ~/focus_groups/data/
```

## Pitfalls

- **Lambda instances are ephemeral**: Save checkpoints to GCS frequently. Instance can be reclaimed.
- **Don't install CUDA manually**: Lambda instances come with CUDA pre-installed. Just install PyTorch with the right CUDA index URL.
- **tmux is mandatory**: SSH disconnects kill jobs. Always use tmux.
- **Check VRAM before starting**: `nvidia-smi` to confirm GPU memory. Mistral-7B in 4-bit needs ~6GB, full precision needs ~28GB.
