# Building Model Containers

## Container Images

### 1. Triton Server with Dependencies
The base Triton server with PyTorch, Transformers, and dependencies pre-installed.

```bash
# Build Triton server with torch/transformers (CUDA 11.8)
# Tag format: {triton-version}-py3-torch{pytorch-version}-cu{cuda-version}-v{revision}
# Current: v2 = PyTorch 2.1.0 + Transformers 4.34.1 + CUDA 11.8
podman build -f Containerfile.triton \
  -t quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-torch2.1-cu118-v2 .

podman push quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-torch2.1-cu118-v2

# Version History:
# v1: PyTorch 2.1.0 + Transformers 4.35.0 (incompatible - failed)
# v2: PyTorch 2.1.0 + Transformers 4.34.1 (compatible)
```

### 2. Model Data Containers
Build separate containers for each model using the `MODEL_NAME` argument.

**For madlad400-3b-mt:**
```bash
# v0.0.4: Batching enabled in config.pbtxt
podman build -f Containerfile.modelcar \
  --build-arg MODEL_NAME=madlad \
  -t quay.io/rh_ee_sgleszer/madlad400-3b-mt-triton-modelcar:0.0.4 .

podman push quay.io/rh_ee_sgleszer/madlad400-3b-mt-triton-modelcar:0.0.4
```

**For flan-t5-small:**
```bash
podman build -f Containerfile.modelcar \
  --build-arg MODEL_NAME=t5-small \
  -t quay.io/rh_ee_sgleszer/flan-t5-small-triton-modelcar:0.0.1 .

podman push quay.io/rh_ee_sgleszer/flan-t5-small-triton-modelcar:0.0.1
```

## Directory Structure

```
./
├── Containerfile.modelcar        # Generic model container
├── Containerfile.triton          # Triton server with dependencies
│
└── models/                       # All models organized here
    ├── madlad/                   # madlad400-3b-mt
    │   └── madlad400-3b-mt/
    │       ├── config.pbtxt
    │       ├── 1/
    │       │   ├── model.py
    │       │   └── model.json
    │       └── madlad400-3b-mt/  # Model weights
    │
    └── t5-small/                 # flan-t5-small
        └── flan-t5-small/
            ├── config.pbtxt
            ├── 1/
            │   ├── model.py
            │   └── model.json
            └── flan-t5-small/    # Model weights
```

## Testing Locally

### Option 1: Test on CPU (no GPU needed)
```bash
# Temporarily change KIND_GPU to KIND_CPU in config.pbtxt
cd models/madlad/madlad400-3b-mt  # or models/t5-small/flan-t5-small
sed -i 's/KIND_GPU/KIND_CPU/g' config.pbtxt
cd ../../..  # back to root

# Start Triton with your model
podman run --rm -it \
  -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/models:/mnt/models:Z \
  quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-cu118 \
  tritonserver --model-repository=/mnt/models

# Restore GPU config when done
cd models/madlad/madlad400-3b-mt
sed -i 's/KIND_CPU/KIND_GPU/g' config.pbtxt
```

### Option 2: Test with GPU (NVIDIA GPU required)
```bash
# Podman with NVIDIA GPU access
podman run --rm -it \
  --device nvidia.com/gpu=all \
  --security-opt=label=disable \
  -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/models:/mnt/models:Z \
  quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-cu118 \
  tritonserver --model-repository=/mnt/models

# Alternative: Use Docker if available
docker run --rm -it --gpus all \
  -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/models:/mnt/models \
  quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-cu118 \
  tritonserver --model-repository=/mnt/models
```

### Test Inference
```bash
# For madlad400-3b-mt (with batching)
curl -X POST http://localhost:8000/v2/models/madlad400-3b-mt/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "INPUT_TEXT",
        "datatype": "BYTES",
        "shape": [1, 1],
        "data": ["Hello, how are you?"]
      },
      {
        "name": "TARGET_LANG",
        "datatype": "BYTES",
        "shape": [1, 1],
        "data": ["es"]
      }
    ]
  }'

# For flan-t5-small (with batching)
curl -X POST http://localhost:8000/v2/models/flan-t5-small/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "INPUT_TEXT",
        "datatype": "BYTES",
        "shape": [1, 1],
        "data": ["translate English to Spanish: Hello, how are you?"]
      }
    ]
  }'
```

## Deployment

Each model has its own container, deploy them separately:

**For flan-t5-small:**
```yaml
spec:
  predictor:
    model:
      runtime: triton-transformers
      storageUri: "oci://quay.io/rh_ee_sgleszer/flan-t5-small-triton-modelcar:0.0.1"
```

**For madlad400-3b-mt:**
```yaml
spec:
  predictor:
    model:
      runtime: triton-transformers
      storageUri: "oci://quay.io/rh_ee_sgleszer/madlad400-3b-mt-triton-modelcar:0.0.9"
```

Then apply:
```bash
oc apply -f servingruntime.yaml
oc apply -f inferenceservice.yaml
```

