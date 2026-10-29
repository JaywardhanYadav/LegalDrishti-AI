import os
import sys
import json
import time
import shutil
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from peft import LoraConfig, get_peft_model

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_MODEL_DIR = BASE_DIR / "models" / "octen-0.6b"
OUTPUT_MODEL_DIR = BASE_DIR / "models" / "octen-0.6b-finetuned"
TRAIN_DATA_PATH = BASE_DIR / "data" / "train_triplets.json"
VAL_DATA_PATH = BASE_DIR / "data" / "val_triplets.json"


class LegalTripletDataset(Dataset):
    def __init__(self, json_path: Path):
        with open(json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        return {
            "query": item["query"],
            "positive": item["positive"],
            "negative": item.get("negative", ""),
        }


def compute_normalized_embedding(model, inputs):
    outputs = model(**inputs)
    # Mean pooling / First token pooled embedding
    emb = outputs.last_hidden_state[:, 0]
    return F.normalize(emb, p=2, dim=1)


class ContrastiveLoss(nn.Module):
    """
    Multiple Negatives Ranking Loss (MNRL / InfoNCE) with hard negative support.
    """
    def __init__(self, temperature: float = 0.05):
        super().__init__()
        self.temperature = temperature
        self.cross_entropy = nn.CrossEntropyLoss()

    def forward(self, q_emb, p_emb, n_emb=None):
        batch_size = q_emb.size(0)

        # In-batch similarities: (batch_size, batch_size)
        sim_pos = torch.matmul(q_emb, p_emb.T) / self.temperature

        if n_emb is not None:
            # Query to Hard Negative similarities: (batch_size, batch_size)
            sim_neg = torch.matmul(q_emb, n_emb.T) / self.temperature
            # Concatenate along candidate dimension: (batch_size, batch_size * 2)
            logits = torch.cat([sim_pos, sim_neg], dim=1)
        else:
            logits = sim_pos

        # Ground truth: diagonal entries are the true positive matches
        labels = torch.arange(batch_size, device=q_emb.device)
        return self.cross_entropy(logits, labels)


def evaluate(model, tokenizer, val_loader, device):
    model.eval()
    total_val = 0
    top1_correct = 0

    with torch.no_grad():
        for batch in val_loader:
            queries = batch["query"]
            positives = batch["positive"]
            negatives = batch["negative"]

            q_in = tokenizer(queries, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
            p_in = tokenizer(positives, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
            n_in = tokenizer(negatives, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)

            q_emb = compute_normalized_embedding(model, q_in)
            p_emb = compute_normalized_embedding(model, p_in)
            n_emb = compute_normalized_embedding(model, n_in)

            # Check if sim(q, pos) > sim(q, neg)
            pos_sim = torch.sum(q_emb * p_emb, dim=1)
            neg_sim = torch.sum(q_emb * n_emb, dim=1)

            correct = (pos_sim > neg_sim).sum().item()
            top1_correct += correct
            total_val += len(queries)

    acc = (top1_correct / total_val) * 100 if total_val > 0 else 0.0
    return acc


def train_model():
    print("=" * 60)
    print("  LegalDrishti AI - Octen-0.6B Fine-Tuning Pipeline")
    print("=" * 60)

    if not BASE_MODEL_DIR.exists():
        print(f"[Error] Base model directory not found at: {BASE_MODEL_DIR}")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[Setup] Training Device: CUDA GPU -> {gpu_name} ({vram:.1f} GB VRAM)", flush=True)
    else:
        print(f"[Setup] Training Device: CPU", flush=True)

    print(f"[Setup] Loading base tokenizer and model from {BASE_MODEL_DIR}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(str(BASE_MODEL_DIR))
    base_model = AutoModel.from_pretrained(str(BASE_MODEL_DIR))

    # Apply LoRA Adapter
    print("[Setup] Injecting LoRA adapter for efficient parameter adaptation...", flush=True)
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(base_model, lora_config)
    model.to(device)

    trainable_params, all_params = model.get_nb_trainable_parameters()
    print(f"[Setup] Trainable Parameters: {trainable_params:,} / {all_params:,} ({trainable_params/all_params*100:.2f}%)", flush=True)

    train_dataset = LegalTripletDataset(TRAIN_DATA_PATH)
    val_dataset = LegalTripletDataset(VAL_DATA_PATH)

    batch_size = 4
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    print(f"[Setup] Training Samples: {len(train_dataset)} | Validation Samples: {len(val_dataset)}", flush=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=0.01)
    criterion = ContrastiveLoss(temperature=0.05)

    # Initial Zero-Shot Evaluation
    print("\n[Evaluation] Evaluating zero-shot accuracy before fine-tuning...", flush=True)
    init_acc = evaluate(model, tokenizer, val_loader, device)
    print(f"[Evaluation] Initial Baseline Top-1 Accuracy: {init_acc:.1f}%\n", flush=True)

    num_epochs = 3
    print(f"[Training] Starting fine-tuning for {num_epochs} epochs...", flush=True)

    start_time = time.time()
    for epoch in range(1, num_epochs + 1):
        model.train()
        total_loss = 0.0
        step_count = 0

        for step, batch in enumerate(train_loader, start=1):
            queries = batch["query"]
            positives = batch["positive"]
            negatives = batch["negative"]

            optimizer.zero_grad()

            q_in = tokenizer(queries, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
            p_in = tokenizer(positives, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
            n_in = tokenizer(negatives, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)

            q_emb = compute_normalized_embedding(model, q_in)
            p_emb = compute_normalized_embedding(model, p_in)
            n_emb = compute_normalized_embedding(model, n_in)

            loss = criterion(q_emb, p_emb, n_emb)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            step_count += 1

            if step % 5 == 0 or step == len(train_loader):
                print(f"  Epoch [{epoch}/{num_epochs}] Step [{step}/{len(train_loader)}] Loss: {loss.item():.4f}", flush=True)

        avg_loss = total_loss / step_count
        val_acc = evaluate(model, tokenizer, val_loader, device)
        print(f"--> [Epoch {epoch} Complete] Average Loss: {avg_loss:.4f} | Validation Top-1 Acc: {val_acc:.1f}%\n", flush=True)

        # Save checkpoint after each epoch
        ckpt_dir = OUTPUT_MODEL_DIR / "adapter_checkpoint"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(ckpt_dir))

    elapsed = time.time() - start_time
    print(f"[Training Complete] Total time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)", flush=True)

    # Merge LoRA weights into base model
    print(f"\n[Export] Merging LoRA weights back into base model...", flush=True)
    with torch.no_grad():
        merged_model = model.merge_and_unload()
    merged_model.eval()

    # Save to fine-tuned model directory
    OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Export] Saving standalone fine-tuned model to {OUTPUT_MODEL_DIR}...", flush=True)
    merged_model.save_pretrained(str(OUTPUT_MODEL_DIR))
    tokenizer.save_pretrained(str(OUTPUT_MODEL_DIR))

    print("\n" + "=" * 60, flush=True)
    print(f"  [SUCCESS] Octen-0.6B Fine-Tuned Model Ready!", flush=True)
    print(f"  Weights saved to: {OUTPUT_MODEL_DIR}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    train_model()
