# MLServer HuggingFace Runtime for FLAN-T5-Small

This setup deploys the [FLAN-T5-Small](https://huggingface.co/google/flan-t5-small) text-to-text generation model using [MLServer HuggingFace Runtime](https://mlserver.readthedocs.io/en/latest/runtimes/huggingface.html).

## Model Overview

**FLAN-T5-Small** is a fine-tuned version of T5 (Text-to-Text Transfer Transformer) from Google that excels at various NLP tasks including translation, summarization, and question answering.

- **Model**: `google/flan-t5-small`
- **Size**: ~300MB
- **Task**: Text-to-Text Generation (seq2seq)
- **Parameters**: ~80M

## When to Use This

Use MLServer HuggingFace runtime for:
- HuggingFace Transformer models (translation, summarization, text generation)
- V2 Inference Protocol compatibility
- Lightweight Python-based model serving
- When you need custom model implementations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    InferenceService                         │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Init Container    │    │      MLServer Container     │ │
│  │   (Model Car OCI)   │───►│   (seldonio/mlserver:       │ │
│  │                     │    │    1.6.0-huggingface)       │ │
│  │  /mnt/models:       │    │                             │ │
│  │  - model files      │    │  HuggingFaceRuntime loads:  │ │
│  │  - model-settings   │    │  - model-settings.json      │ │
│  └─────────────────────┘    │  - transformer model        │ │
│                             └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Build and Push Model Container (one-time)

```bash
# Build the model container
podman build -t quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.1 -f Containerfile.modelcar .

# Push to registry
podman push quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.1
```

### 2. Deploy ServingRuntime

```bash
oc apply -f servingruntime.yaml
```

### 3. Deploy InferenceService

```bash
oc apply -f inferenceservice.yaml
```

### 4. Create Route for External Access (optional)

```bash
oc apply -f service.yaml
oc apply -f route.yaml
```

## API Usage

### Get Route URL

```bash
ROUTE=$(oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}')
```

### V2 Inference Protocol

MLServer uses the V2 Inference Protocol.

#### Translation Request

```bash
curl -k "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "args",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["translate English to German: Hello, how are you today?"]
      }
    ]
  }'
```

#### Question Answering

```bash
curl -k "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "args",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["What is the capital of France?"]
      }
    ]
  }'
```

#### Summarization

```bash
curl -k "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "args",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["summarize: Machine learning is a subset of artificial intelligence that enables systems to learn from data."]
      }
    ]
  }'
```

## Using with Python

```python
import requests

# Get route URL
route = "<your-route-url>"  # e.g., flan-t5-small-mlserver-myproject.apps.cluster.example.com

# Translation request
payload = {
    "inputs": [
        {
            "name": "args",
            "shape": [1],
            "datatype": "BYTES",
            "data": ["translate English to German: The weather is nice today."]
        }
    ]
}

response = requests.post(
    f"https://{route}/v2/models/flan-t5-small/infer",
    json=payload,
    verify=False  # For self-signed certs
)

result = response.json()
print(result)
# Output: Das Wetter ist heute schön.
```

## Model Settings

The `model-settings.json` configures MLServer HuggingFace runtime:

```json
{
  "name": "flan-t5-small",
  "implementation": "mlserver_huggingface.HuggingFaceRuntime",
  "parameters": {
    "extra": {
      "task": "text2text-generation",
      "pretrained_model": "google/flan-t5-small",
      "device": "cuda"
    }
  }
}
```

### Configuration Options

| Parameter | Description |
|-----------|-------------|
| `name` | Model name (used in API paths) |
| `implementation` | MLServer runtime class |
| `task` | HuggingFace task type |
| `pretrained_model` | HuggingFace model identifier |
| `device` | `cuda` for GPU, `cpu` for CPU |

## GPU Configuration

For GPU acceleration, ensure:

```yaml
resources:
  requests:
    nvidia.com/gpu: 1
  limits:
    nvidia.com/gpu: 1
```

And in `model-settings.json`:
```json
"device": "cuda"
```

## CPU-Only Configuration

For CPU-only deployment, update `inferenceservice.yaml`:

```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
  limits:
    cpu: "4"
    memory: "8Gi"
```

And update `model-settings.json`:
```json
"device": "cpu"
```

## Troubleshooting

### Check Pod Logs

```bash
oc logs -l serving.kserve.io/inferenceservice=flan-t5-small-mlserver -c kserve-container
```

### Check InferenceService Status

```bash
oc get inferenceservice flan-t5-small-mlserver
oc describe inferenceservice flan-t5-small-mlserver
```

### Check Model Loading

```bash
# Check if model is ready
curl -k "https://${ROUTE}/v2/models/flan-t5-small"
```

### Common Issues

1. **Model not loading**: Check if the model container was built correctly and the `model-settings.json` is valid.

2. **Slow first request**: First request loads the model; subsequent requests are faster.

3. **Wrong output format**: Ensure you're using the correct V2 protocol input format.

## Alternative Models

You can use other models by updating `model-settings.json` and rebuilding the model container:

```json
// Larger FLAN-T5 models
"pretrained_model": "google/flan-t5-base"
"pretrained_model": "google/flan-t5-large"

// Other T5 variants
"pretrained_model": "t5-small"
"pretrained_model": "t5-base"
```

## Comparison: MLServer vs KServe HuggingFace Runtime

| Feature | MLServer HuggingFace | KServe HuggingFace |
|---------|---------------------|-------------------|
| API | V2 Protocol | OpenAI + V2 |
| Image | seldonio/mlserver | kserve/huggingfaceserver |
| Config | model-settings.json | CLI args |
| Use case | Custom runtimes | Production serving |

## References

- [FLAN-T5-Small on HuggingFace](https://huggingface.co/google/flan-t5-small)
- [MLServer HuggingFace Runtime](https://mlserver.readthedocs.io/en/latest/runtimes/huggingface.html)
- [V2 Inference Protocol](https://kserve.github.io/website/modelserving/inference_api/)
