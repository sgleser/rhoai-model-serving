import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import triton_python_backend_utils as pb_utils


class TritonPythonModel:
    """Triton Python model for madlad400-3b-mt translation."""

    def initialize(self, args):
        """Initialize the model and tokenizer."""
        import os
        
        # Parse model config
        self.model_config = json.loads(args['model_config'])
        
        # Get model path from model.json
        model_version = args.get('model_version', '1')
        model_name = args.get('model_name', 'madlad400-3b-mt')
        model_repository = args.get('model_repository', '/mnt/models')
        
        # Try to find model.json - handle both /mnt/models and /mnt/models/madlad400-3b-mt as repository
        model_json_path = os.path.join(model_repository, model_version, 'model.json')
        if not os.path.exists(model_json_path):
            # Try alternative path structure
            model_json_path = os.path.join(model_repository, model_name, model_version, 'model.json')
        
        print(f"Reading model configuration from: {model_json_path}")
        with open(model_json_path, 'r') as f:
            model_json = json.load(f)
            model_path = model_json['model']
        
        print(f"Loading model from: {model_path}")
        
        # Load tokenizer and model from local path
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Determine device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        
        self.model.eval()
        print("Model loaded successfully!")

    def execute(self, requests):
        """Execute inference on the requests."""
        responses = []
        
        for request in requests:
            try:
                # Get input text
                input_text_tensor = pb_utils.get_input_tensor_by_name(request, "INPUT_TEXT")
                input_texts = input_text_tensor.as_numpy()
                
                # Decode bytes to strings if necessary
                if input_texts.dtype == np.object_:
                    input_texts = [text.decode('utf-8') if isinstance(text, bytes) else text 
                                   for text in input_texts.flatten()]
                else:
                    input_texts = input_texts.flatten().tolist()
                
                # Optional parameters with defaults
                max_length = 256
                target_lang = None
                
                # Try to get optional parameters
                try:
                    max_length_tensor = pb_utils.get_input_tensor_by_name(request, "MAX_LENGTH")
                    if max_length_tensor is not None:
                        max_length = int(max_length_tensor.as_numpy()[0])
                except Exception:
                    pass
                
                try:
                    target_lang_tensor = pb_utils.get_input_tensor_by_name(request, "TARGET_LANG")
                    if target_lang_tensor is not None:
                        target_lang_bytes = target_lang_tensor.as_numpy()[0]
                        target_lang = target_lang_bytes.decode('utf-8') if isinstance(target_lang_bytes, bytes) else target_lang_bytes
                except Exception:
                    pass
                
                # Prepare inputs (add target language prefix if provided)
                if target_lang:
                    # madlad400 uses format: "<2es> text" for Spanish, "<2fr> text" for French, etc.
                    prepared_texts = [f"<2{target_lang}> {text}" for text in input_texts]
                else:
                    prepared_texts = input_texts
                
                # Tokenize
                inputs = self.tokenizer(
                    prepared_texts,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512
                ).to(self.device)
                
                # Generate translation
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_length=max_length,
                        num_beams=4,
                        early_stopping=True
                    )
                
                # Decode outputs
                translated_texts = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
                
                # Prepare output tensor
                output_texts = np.array(translated_texts, dtype=np.object_)
                output_tensor = pb_utils.Tensor("OUTPUT_TEXT", output_texts)
                
                # Create response
                inference_response = pb_utils.InferenceResponse(
                    output_tensors=[output_tensor]
                )
                responses.append(inference_response)
                
            except Exception as e:
                # Create error response
                error_message = f"Error during inference: {str(e)}"
                print(error_message)
                inference_response = pb_utils.InferenceResponse(
                    output_tensors=[],
                    error=pb_utils.TritonError(error_message)
                )
                responses.append(inference_response)
        
        return responses

    def finalize(self):
        """Clean up resources."""
        print('Cleaning up model...')
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'tokenizer'):
            del self.tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
