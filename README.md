
Docs used:

[Quick Deploy: HuggingFace Transformers on Triton Inference Server (NVIDIA Docs)](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/tutorials/Quick_Deploy/HuggingFaceTransformers/README.html)

[Python Backend Usage (NVIDIA Triton Inference Server docs)](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/python_backend/README.html#usage)

[Example of Triton Python backend](https://github.com/triton-inference-server/tutorials/blob/main/HuggingFace/python_model_repository/python_vit/1/model.py)

[Better way could be to use Triton Model Format](https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/triton/huggingface)

Triton Python backend example: https://github.com/triton-inference-server/python_backend/blob/main/examples/add_sub/model.py#L29-L33

Can we have OpenAI API with Triton?
It looks like there is something in Triton documentation:
https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/client_guide/openai_readme.html



[Alternatively Seldon MLServer could be used with HF Transformers too](https://github.com/SeldonIO/MLServer/tree/master/runtimes/huggingface)


----

1. Download Model from hugging face into the right folder:
    /models
        /madlad
            /madlad400-3b-mt
                /madlad400-3b-mt
        /t5-small
            /flan-t5-small
                /flan-t5-small

2. Build the two container. AI Generated commands and tests in BUILD.md
    Containerfile.modelcar - Here we bake the model.
    Containerfile.triton   - Here we create the serving runtime. We rebuilt the Triton server because we need some Python packages in the model.py to start

3. oc apply -f .   - for the Kubernetes Objects to create them on the openshift cluster.

4. Test cURL-s down in this file


```sh
cd /path/to/triton-model-car-and-servingruntime-container

# Rebuild Triton server with PyTorch 2.1 (this will take a while)
podman build --no-cache -f Containerfile.triton -t quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-cu118 .
podman push quay.io/rh_ee_sgleszer/tritonserver-torch:23.05-py3-cu118

# Rebuild model container with fixed model.py
podman build --no-cache -f Containerfile -t quay.io/rh_ee_sgleszer/madlad400-3b-mt-triton-modelcar:0.0.9 .
podman push quay.io/rh_ee_sgleszer/madlad400-3b-mt-triton-modelcar:0.0.9

# Deploy
oc apply -f servingruntime.yaml
oc apply -f inferenceservice.yaml
```

This worked first in the container without batching:
```sh
curl -X POST http://localhost:8000/v2/models/flan-t5-small/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "INPUT_TEXT",
        "datatype": "BYTES",
        "shape": [1],
        "data": ["translate English to Spanish: Hello, how are you?"]
      }
    ]
  }'
```

with batching
```sh
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
{"model_name":"flan-t5-small","model_version":"1","outputs":[{"name":"OUTPUT_TEXT","datatype":"BYTES","shape":[1],"data":["Cómo está aqu?"]}]}
```

batching with multiple instances
```sh
curl -X POST http://localhost:8000/v2/models/flan-t5-small/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "INPUT_TEXT",
        "datatype": "BYTES",
        "shape": [3, 1],
        "data": [
          "translate English to Spanish: Hello, how are you?",
          "translate English to French: Good morning",
          "translate English to German: Thank you"
        ]
      }
    ]
  }'
{"model_name":"flan-t5-small","model_version":"1","outputs":[{"name":"OUTPUT_TEXT","datatype":"BYTES","shape":[3],"data":["Cómo está aqu?","Good morning","Vielen Dank!"]}]}
```

```sh
curl -k -X POST https://flan-t5-small-triton-<namespace>.apps.<cluster-domain>/v2/models/flan-t5-small/infer \
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

```sh
curl -k -X POST https://flan-t5-small-triton-<namespace>.apps.<cluster-domain>/v2/models/flan-t5-small/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "INPUT_TEXT",
        "datatype": "BYTES",
        "shape": [3, 1],
        "data": [
          "translate English to Spanish: Hello",
          "translate English to French: Good morning",
          "translate English to German: Thank you"
        ]
      }
    ]
  }'
```

```sh
curl -k -X POST https://${ROUTE}/v2/models/flan-t5-small/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "INPUT_TEXT",
        "datatype": "BYTES",
        "shape": [3, 1],
        "data": [
          "translate English to Spanish: Hello",
          "translate English to French: Good morning",
          "translate English to German: Thank you"
        ]
      }
    ]
  }'
```