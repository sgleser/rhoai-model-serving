# Build Instructions for FLAN-T5-Small MLServer Deployment

## Prerequisites

- Podman or Docker installed
- Access to Quay.io (or your container registry)
- OpenShift cluster with OpenDataHub/RHOAI installed

## Step 1: Build the Model Container

The model container packages the FLAN-T5-Small model with its configuration.

```bash
cd bmj/model-serving/triton-model-car-and-servingruntime-container/mlserver/huggingface

# Build the model container (downloads ~300MB model)
podman build -t quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.1 -f Containerfile.modelcar .

# Push to registry
podman push quay.io/rh_ee_sgleszer/flan-t5-small-modelcar:0.0.1
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

# Wait for deployment to be ready
oc get inferenceservice flan-t5-small-mlserver -w
```

## Step 3: Expose the Service (Optional)

```bash
# Create the Service and Route for external access
oc apply -f service.yaml
oc apply -f route.yaml

# Get the route URL
oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}'
```

## Step 4: Test the Deployment

```bash
ROUTE=$(oc get route flan-t5-small-mlserver -o jsonpath='{.spec.host}')

# Test translation (English to German)
curl -k "https://${ROUTE}/v2/models/flan-t5-small/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "args",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["translate English to German: Hello, how are you?"]
      }
    ]
  }'

# Test question answering
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

## Customization

### Using a Different Model

1. Update `models/flan-t5-small/model-settings.json` with the new model:

```json
{
  "name": "your-model-name",
  "implementation": "mlserver_huggingface.HuggingFaceRuntime",
  "parameters": {
    "extra": {
      "task": "text2text-generation",
      "pretrained_model": "your/model-name",
      "device": "cuda"
    }
  }
}
```

2. Update `Containerfile.modelcar` to download the new model

3. Update YAML files with the new model name

4. Rebuild and redeploy

### Using Your Own Registry

Replace `quay.io/rh_ee_sgleszer` with your registry path in:
- `Containerfile.modelcar`
- `inferenceservice.yaml`
