# Build Instructions for FLAN-T5-Small MLServer Deployment

## Prerequisites

- Podman or Docker installed
- Access to Quay.io (or your container registry)
- OpenShift cluster with OpenDataHub/RHOAI installed

## Step 1: Build the Model Container

The model container downloads the FLAN-T5-Small model from HuggingFace and packages it with the model configuration.

```bash
cd bmj/model-serving/triton-model-car-and-servingruntime-container/mlserver/huggingface/flan-t5-small

# Build the model container (~300MB model download, takes a few minutes)
podman build --no-cache -t quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.9 -f Containerfile.modelcar .

# Push to registry
podman push quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.9
```

### What the Containerfile Does

1. Uses `huggingface_hub.snapshot_download()` to download model files
2. Copies `model-settings.json` to configure MLServer
3. Copies `settings.json` for debug logging
4. Creates minimal final image with just the model files

### Model Car Directory Structure

```
/models/                          # KServe copies this to /mnt/models/
├── flan-t5-small/
│   ├── model-settings.json       # MLServer configuration
│   ├── config.json               # HuggingFace model config
│   ├── model.safetensors         # Model weights
│   ├── tokenizer.json            # Tokenizer
│   └── ...                       # Other model files
└── settings.json                 # MLServer global settings
```

## Step 2: Deploy to OpenShift

```bash
# Login to OpenShift
oc login --server=<your-cluster-api>

# Switch to your project
oc project <your-project>

# Deploy the ServingRuntime
oc apply -f servingruntime.yaml

# Deploy the InferenceService
oc apply -f inferenceservice.yaml

# Wait for deployment to be ready (2/2 Running)
oc get pods -l serving.kserve.io/inferenceservice=flan-t5-small-mlserver -w
```

## Step 3: Expose the Service

```bash
# Create the Service and Route for external access
oc apply -f service.yaml
oc apply -f route.yaml

# Get the route URL
ROUTE=$(oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}')
echo "Route: https://${ROUTE}"
```

## Step 4: Load the Model (Required!)

**Important**: MLServer discovers the model but doesn't auto-load it at startup. You must explicitly load the model:

```bash
# Load the model
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"

# Wait a few seconds for loading, then verify
curl -sk -X POST "https://${ROUTE}/v2/repository/index" -H "Content-Type: application/json" -d '{}'
# Should show: [{"name":"flan-t5-small","state":"READY","reason":""}]
```

### Why Manual Loading?

MLServer marks the model as `UNAVAILABLE` at startup due to TensorFlow/CUDA initialization. After explicitly loading, the model works correctly using CPU.

## Step 5: Test the Deployment

```bash
ROUTE=$(oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}')

# Test translation (English to German)
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

# Test question answering
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

## Customization

### Using a Different Model

1. Update `models/flan-t5-small/model-settings.json`:

```json
{
  "name": "your-model-name",
  "implementation": "mlserver_huggingface.HuggingFaceRuntime",
  "parameters": {
    "uri": "/mnt/models/your-model-name",
    "extra": {
      "task": "text2text-generation"
    }
  }
}
```

2. Update `Containerfile.modelcar` to download the new model:

```dockerfile
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('your/model-name', local_dir='/models/your-model-name')"
```

3. Update YAML files with the new model name

4. Rebuild and redeploy

### Using Your Own Registry

Replace `quay.io/rh_ee_sgleszer` with your registry path in:
- `Containerfile.modelcar` (build command comments)
- `inferenceservice.yaml` (storageUri)

### Supported Tasks

| Task | Description |
|------|-------------|
| `text2text-generation` | T5, FLAN-T5, BART models |
| `text-generation` | GPT-2, GPT-Neo models |
| `fill-mask` | BERT, RoBERTa models |
| `token-classification` | NER models |
| `sequence-classification` | Sentiment analysis |
| `translation` | Translation models |
| `summarization` | Summarization models |

## Troubleshooting

### Model shows "UNAVAILABLE"

This is normal at startup. Load the model manually:

```bash
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"
```

### "Model not found" error

1. Check if model is discovered:
```bash
curl -sk -X POST "https://${ROUTE}/v2/repository/index" -H "Content-Type: application/json" -d '{}'
```

2. Load the model if state is UNAVAILABLE

### Check logs for errors

```bash
oc logs -l serving.kserve.io/inferenceservice=flan-t5-small-mlserver -c kserve-container
```

### Verify model files are present

```bash
oc exec $(oc get pods -l serving.kserve.io/inferenceservice=flan-t5-small-mlserver -o jsonpath='{.items[0].metadata.name}') \
  -c kserve-container -- ls -la /mnt/models/flan-t5-small/
```

### Route not found

Routes get deleted when InferenceService is recreated. Re-apply:

```bash
oc apply -f route.yaml
oc apply -f service.yaml
```

## Quick Reference

```bash
# Build
podman build --no-cache -t quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.9 -f Containerfile.modelcar .
podman push quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.9

# Deploy
oc apply -f servingruntime.yaml
oc apply -f inferenceservice.yaml
oc apply -f service.yaml
oc apply -f route.yaml

# Load model (required!)
ROUTE=$(oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}')
curl -sk -X POST "https://${ROUTE}/v2/repository/models/flan-t5-small/load"

# Test
curl -sk "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -X POST -H "Content-Type: application/json" \
  -d '{"inputs": [{"name": "args", "shape": [1], "datatype": "BYTES", "data": ["translate English to German: Hello!"]}]}'
```
