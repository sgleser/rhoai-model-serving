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
│  │  /models/* copied   │    │                             │ │
│  │  to /mnt/models/*   │    │  HuggingFaceRuntime loads:  │ │
│  │                     │    │  - model-settings.json      │ │
│  └─────────────────────┘    │  - transformer model        │ │
│                             └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Build and Push Model Container (one-time)

```bash
cd flan-t5-small

# Build the model container (~300MB download)
podman build -t quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.9 -f Containerfile.modelcar .

# Push to registry
podman push quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.9
```

### 2. Deploy to OpenShift

```bash
# Deploy ServingRuntime
oc apply -f servingruntime.yaml

# Deploy InferenceService
oc apply -f inferenceservice.yaml

# Create Service and Route for external access
oc apply -f service.yaml
oc apply -f route.yaml
```

### 3. Load the Model (Required!)

**Important**: MLServer discovers the model but doesn't auto-load it at startup. You must call the load endpoint:

```bash
ROUTE=$(oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}')

# Load the model
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"
```

You can verify the model is loaded:

```bash
# Check model status (should return model info, not "not found")
curl -sk "https://${ROUTE}/v2/models/flan-t5-small"

# Or check repository index
curl -sk -X POST "https://${ROUTE}/v2/repository/index" -H "Content-Type: application/json" -d '{}'
# State should be "READY" not "UNAVAILABLE"
```

### 4. Test Inference

```bash
# Translation
curl -sk "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -X POST -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "args",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["translate English to German: Hello, how are you?"]
    }]
  }'
```

## API Usage

### V2 Inference Protocol

MLServer uses the V2 Inference Protocol.

#### Translation Request

```bash
curl -sk "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -X POST -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "args",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["translate English to German: Hello, how are you today?"]
    }]
  }'
```

#### Question Answering

```bash
curl -sk "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -X POST -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "args",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["What is the capital of France?"]
    }]
  }'
```

#### Summarization

```bash
curl -sk "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -X POST -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "args",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["summarize: Machine learning is a subset of artificial intelligence that enables systems to learn from data."]
    }]
  }'
```

### Model Repository API

```bash
# List all models
curl -sk -X POST "https://${ROUTE}/v2/repository/index" -H "Content-Type: application/json" -d '{}'

# Load a model
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"

# Unload a model
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/unload"
```

## Using with Python

```python
import requests

# Get route URL
route = "<your-route-url>"  # e.g., flan-t5-small-mlserver-myproject.apps.cluster.example.com

# First, load the model (if not already loaded)
requests.post(f"https://{route}/v2/repository/models/flan-t5-small/load", verify=False)

# Translation request
payload = {
    "inputs": [{
        "name": "args",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["translate English to German: The weather is nice today."]
    }]
}

response = requests.post(
    f"https://{route}/v2/models/flan-t5-small/infer",
    json=payload,
    verify=False
)

result = response.json()
print(result["outputs"][0]["data"])
```

## File Structure

```
flan-t5-small/
├── Containerfile.modelcar      # Builds model container
├── inferenceservice.yaml       # KServe InferenceService
├── servingruntime.yaml         # MLServer ServingRuntime
├── service.yaml                # ClusterIP Service
├── route.yaml                  # OpenShift Route
├── settings.json               # MLServer global settings
├── models/
│   └── flan-t5-small/
│       └── model-settings.json # Model configuration
├── README.md                   # This file
└── BUILD.md                    # Build instructions
```

## Model Settings

The `model-settings.json` configures MLServer HuggingFace runtime:

```json
{
  "name": "flan-t5-small",
  "implementation": "mlserver_huggingface.HuggingFaceRuntime",
  "parameters": {
    "uri": "/mnt/models/flan-t5-small",
    "extra": {
      "task": "text2text-generation"
    }
  }
}
```

### Configuration Options

| Parameter | Description |
|-----------|-------------|
| `name` | Model name (used in API paths) |
| `implementation` | MLServer runtime class |
| `uri` | Path to model files (after KServe copies them) |
| `task` | HuggingFace task type |

## Key Concepts

### Model Car Directory Structure

KServe copies files from `/models/` in the model car to `/mnt/models/` in the main container:

```
Model Car (/models/)          →  Main Container (/mnt/models/)
├── flan-t5-small/                ├── flan-t5-small/
│   ├── model-settings.json       │   ├── model-settings.json
│   ├── config.json               │   ├── config.json
│   ├── model.safetensors         │   ├── model.safetensors
│   └── tokenizer.json            │   └── tokenizer.json
└── settings.json                 └── settings.json
```

### Model Loading

MLServer discovers models with `model-settings.json` files but doesn't auto-load them. The model must be explicitly loaded via the repository API:

```bash
curl -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"
```

## Troubleshooting

### Model not found (404)

The model needs to be loaded first:

```bash
# Load the model
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"
```

### Check if model is discovered

```bash
curl -sk -X POST "https://${ROUTE}/v2/repository/index" -H "Content-Type: application/json" -d '{}'
```

- `READY`: Model is loaded and ready
- `UNAVAILABLE`: Model is discovered but not loaded (call load endpoint)
- Not listed: Model files or model-settings.json are missing

### Check Pod Logs

```bash
oc logs -l serving.kserve.io/inferenceservice=flan-t5-small-mlserver -c kserve-container
```

### Check Model Files

```bash
oc exec $(oc get pods -l serving.kserve.io/inferenceservice=flan-t5-small-mlserver -o jsonpath='{.items[0].metadata.name}') \
  -c kserve-container -- ls -la /mnt/models/flan-t5-small/
```

### Common Issues

1. **"Model not found"**: Load the model first with the load endpoint
2. **"UNAVAILABLE" state**: Model failed to load, check logs for errors
3. **CUDA errors in logs**: Normal if running on CPU, model will still work
4. **Slow first request**: Model loading takes time, subsequent requests are fast

## Comparison: MLServer vs KServe HuggingFace Runtime

| Feature | MLServer HuggingFace | KServe HuggingFace |
|---------|---------------------|-------------------|
| API | V2 Protocol | OpenAI + V2 |
| Image | seldonio/mlserver | kserve/huggingfaceserver |
| Config | model-settings.json | CLI args |
| Model Loading | Manual via API | Automatic |
| Use case | Custom runtimes | Production serving |

## References

- [FLAN-T5-Small on HuggingFace](https://huggingface.co/google/flan-t5-small)
- [MLServer HuggingFace Runtime](https://mlserver.readthedocs.io/en/latest/runtimes/huggingface.html)
- [V2 Inference Protocol](https://kserve.github.io/website/modelserving/inference_api/)
- [MLServer Repository API](https://mlserver.readthedocs.io/en/latest/user-guide/content-type.html)
