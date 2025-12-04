# KServe Hugging Face Runtime for OpenShift AI

This setup deploys models using the [KServe Hugging Face Runtime](https://kserve.github.io/website/docs/model-serving/generative-inference/overview), which provides **OpenAI-compatible APIs** for serving Hugging Face models.

## Example Model

This setup uses [google/flan-t5-small](https://huggingface.co/google/flan-t5-small) - a fine-tuned T5 model for text-to-text generation (~300MB).

## When to Use This

Use the Hugging Face backend for:
- Models **not supported by vLLM** (like T5, BART, encoder-decoder models)
- Predictive tasks: `fill_mask`, `token_classification`, `sequence_classification`
- Text generation with standard HuggingFace transformers
- When you need OpenAI API compatibility without vLLM

## Supported Tasks

| Task | API Endpoint | Description |
|------|--------------|-------------|
| Text Generation | `/openai/v1/completions` | GPT-style text completion |
| Text2Text | `/openai/v1/completions` | T5/BART style generation |
| Chat | `/openai/v1/chat/completions` | Chat with message history |
| Embeddings | `/openai/v1/embeddings` | Vector embeddings |
| Re-rank | `/openai/v1/rerank` | Score/rank text inputs |
| Fill Mask | V2 Protocol | BERT-style masked language modeling |
| Token Classification | V2 Protocol | NER, POS tagging |
| Sequence Classification | V2 Protocol | Sentiment, text classification |

## Quick Start

### 1. Deploy ServingRuntime (one-time)

```bash
oc apply -f servingruntime.yaml
```

### 2. Deploy FLAN-T5-Small

```bash
oc apply -f inferenceservice.yaml
```

### 3. Create Route for External Access (optional)

```bash
oc apply -f service.yaml
oc apply -f route.yaml
```

## OpenAI API Usage

### Get Route URL

```bash
ROUTE=$(oc get route flan-t5-small -o jsonpath='{.spec.host}')
```

### Text Completions (Translation)

```bash
curl -k "https://${ROUTE}/openai/v1/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flan-t5-small",
    "prompt": "translate English to German: Hello, how are you?",
    "max_tokens": 50
  }'
```

### Text Completions (Question Answering)

```bash
curl -k "https://${ROUTE}/openai/v1/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flan-t5-small",
    "prompt": "What is the capital of France?",
    "max_tokens": 20
  }'
```

### Text Completions (Summarization)

```bash
curl -k "https://${ROUTE}/openai/v1/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flan-t5-small",
    "prompt": "summarize: Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
    "max_tokens": 50
  }'
```

## Using with Python OpenAI SDK

```python
from openai import OpenAI

# Point to your KServe endpoint
ROUTE = "<your-route-url>"  # e.g., flan-t5-small-myproject.apps.cluster.example.com
client = OpenAI(
    base_url=f"https://{ROUTE}/openai/v1",
    api_key="not-needed"  # No auth required by default
)

# Text completion - Translation
response = client.completions.create(
    model="flan-t5-small",
    prompt="translate English to Spanish: Good morning, how are you?",
    max_tokens=50
)
print(response.choices[0].text)
# Output: Buenos días, ¿cómo estás?

# Text completion - Question Answering
response = client.completions.create(
    model="flan-t5-small",
    prompt="What is the largest planet in our solar system?",
    max_tokens=20
)
print(response.choices[0].text)
# Output: Jupiter
```

## V2 Inference Protocol

You can also use the V2 protocol directly:

```bash
curl -k "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "text",
        "datatype": "BYTES",
        "shape": [1],
        "data": ["translate English to French: Hello world"]
      }
    ]
  }'
```

## Configuration Options

### Force HuggingFace Backend (disable vLLM)

If you want to ensure HuggingFace backend is used instead of vLLM:

```yaml
spec:
  predictor:
    model:
      args:
        - --backend=huggingface  # Force HuggingFace backend
```

### Common Arguments

| Argument | Description |
|----------|-------------|
| `--backend` | `auto`, `huggingface`, or `vllm` |
| `--task` | `text_generation`, `text2text_generation`, `fill_mask`, `token_classification`, `sequence_classification` |
| `--dtype` | `auto`, `float16`, `float32`, `bfloat16` |
| `--max_model_len` | Max tokens the model can process |
| `--trust_remote_code` | Allow custom model code |
| `--return_probabilities` | Return prediction probabilities |

### GPU Configuration

```yaml
resources:
  requests:
    nvidia.com/gpu: 1
  limits:
    nvidia.com/gpu: 1
```

### CPU-Only (no GPU)

```yaml
resources:
  requests:
    cpu: "2"
    memory: "8Gi"
  limits:
    cpu: "4"
    memory: "16Gi"
# No nvidia.com/gpu = CPU image auto-selected
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFETENSORS_FAST_GPU` | Enabled | Faster model loading |
| `HF_HUB_DISABLE_TELEMETRY` | Enabled | No telemetry |
| `KSERVE_OPENAI_ROUTE_PREFIX` | `openai` | Prefix for OpenAI endpoints |

To remove the `/openai` prefix:
```yaml
env:
  - name: KSERVE_OPENAI_ROUTE_PREFIX
    value: ""
```

## Troubleshooting

### Check Pod Logs
```bash
oc logs -l serving.kserve.io/inferenceservice=flan-t5-small -c kserve-container
```

### Check InferenceService Status
```bash
oc get inferenceservice flan-t5-small
oc describe inferenceservice flan-t5-small
```

### Common Issues

1. **Model not loading**: Check if model exists on HuggingFace Hub
2. **OOM errors**: Reduce model size, use quantization, or add more memory
3. **vLLM errors**: Force HuggingFace backend with `--backend huggingface`
4. **Slow first request**: Model loading takes time, subsequent requests are fast

## Using Other Models

To use a different model, update the `storageUri` in `inferenceservice.yaml`:

```yaml
# Text Generation (GPT-2)
storageUri: "hf://gpt2"

# Larger FLAN-T5
storageUri: "hf://google/flan-t5-base"
storageUri: "hf://google/flan-t5-large"

# BERT for Fill-Mask (change task to fill_mask)
storageUri: "hf://bert-base-uncased"

# Sentiment Analysis (change task to sequence_classification)
storageUri: "hf://distilbert-base-uncased-finetuned-sst-2-english"

# NER (change task to token_classification)
storageUri: "hf://dslim/bert-base-NER"
```

## References

- [KServe HuggingFace Runtime Overview](https://kserve.github.io/website/docs/model-serving/generative-inference/overview)
- [FLAN-T5-Small on HuggingFace](https://huggingface.co/google/flan-t5-small)
- [Supported vLLM Models](https://docs.vllm.ai/en/latest/models/supported_models.html)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

