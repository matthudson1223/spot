# Fix Applied: Vertex AI Fine-Tuned Model "Invalid Argument" Error

## Problem
When calling `generate_content()` on fine-tuned Gemini models, receiving:
```
400 Request contains an invalid argument
```

## Root Cause
The issue had multiple layers:
1. **Wrong model resource names**: Using display names (e.g., `crossword-grid-generator@1`) instead of actual model IDs
2. **Wrong endpoint format**: Tuned Gemini models must be accessed through their **endpoint** resources, not model resources
3. **API method confusion**: Gemini tuned models use `GenerativeModel.generate_content()`, not the Predict API

## Solution Applied

### Updated: [src/orchestrator.py](src/orchestrator.py) - Lines 22-67

**Changes Made:**

1. **Retrieve Actual Model Endpoints** (NEW)
   - Query tuning jobs to get actual endpoint resource names
   - Use endpoint resources instead of model display names
   - Store both model ID and endpoint ID

2. **Updated ModelClient Class** (Lines 22-67)
   - Constructor now takes both `model_name` and `endpoint_name`
   - Load model using the **endpoint resource name** with `GenerativeModel()`
   - Call `generate_content()` directly without generation config
   - Tuned models use the parameters they were trained with

3. **Updated initialize_models()** (Lines 121-161)
   - Use actual model IDs (e.g., `1942114667140743168@1`)
   - Use endpoint resources (e.g., `endpoints/7494226174944477184`)
   - Use project number (`922813767018`) not project ID

### Code Changes

**Before (Incorrect):**
```python
# Wrong: Using display name instead of actual model resource
self.grid_model = ModelClient(
    f"projects/{self.project_id}/locations/{self.location}/models/crossword-grid-generator@1",
    self.project_id,
    self.location
)

# Wrong: Loading model by model resource name
self.model = GenerativeModel(self.model_name)
```

**After (Correct):**
```python
# Correct: Using actual model ID and endpoint resource
self.grid_model = ModelClient(
    model_name=f"projects/922813767018/locations/us-central1/models/1942114667140743168@1",
    endpoint_name=f"projects/922813767018/locations/us-central1/endpoints/7494226174944477184",
    project_id=self.project_id,
    location=self.location
)

# Correct: Loading model by ENDPOINT resource name
self.model = GenerativeModel(self.endpoint_name)
```

**Key Insight:**
```python
# ❌ WRONG - Model resource doesn't work for inference
model = GenerativeModel("projects/.../models/12345@1")

# ✅ CORRECT - Use endpoint resource for inference
model = GenerativeModel("projects/.../endpoints/67890")
```

## Testing

### Quick Test
```bash
python test_models.py
```

This will:
1. Initialize all three tuned models using endpoint resources
2. Test generation with each model
3. Report success/failure for each

### Actual Output (SUCCESS!)
```
[1/3] Testing Grid Generator...
✓ Grid generator responded (length: 1626 chars)

[2/3] Testing Fill Generator...
✓ Fill generator responded (length: 2423 chars)

[3/3] Testing Clue Generator...
✓ Clue generator responded: 'Apollo mission vehicle (6 letters)'

✅ ALL TESTS PASSED - Models are ready to use!
```

### How to Get Endpoint Resources

If you need to find the endpoint resources for your tuned models:

```python
import google.cloud.aiplatform as aiplatform
import vertexai

vertexai.init(project='your-project-id', location='us-central1')

# Get tuning job
job_id = 'your-tuning-job-id'
job_resource_name = f'projects/your-project-id/locations/us-central1/tuningJobs/{job_id}'

client = aiplatform.gapic.GenAiTuningServiceClient(
    client_options={'api_endpoint': 'us-central1-aiplatform.googleapis.com'}
)

request = aiplatform.gapic.GetTuningJobRequest(name=job_resource_name)
tuning_job = client.get_tuning_job(request=request)

print(f"Model: {tuning_job.tuned_model.model}")
print(f"Endpoint: {tuning_job.tuned_model.endpoint}")
```

## Key Points

### ✅ What Works Now
- Tuned Gemini models accessed through endpoint resources
- Models respond successfully to generation requests
- All three models (grid, fill, clue) working correctly
- No generation config needed - models use tuned parameters

### ⚠️ Critical Requirements

1. **Use Endpoint Resources, Not Model Resources**
   - ❌ Wrong: `projects/.../models/12345@1`
   - ✅ Correct: `projects/.../endpoints/67890`
   - The endpoint resource is what GenerativeModel needs

2. **Use Project Number, Not Project ID**
   - ❌ Wrong: `crossword-constructor-478912` (project ID)
   - ✅ Correct: `922813767018` (project number)
   - Get project number from tuning job resource names

3. **Query Tuning Jobs for Endpoints**
   - Model display names (like `crossword-grid-generator@1`) are not usable
   - Use the GenAiTuningServiceClient to get actual endpoint resources
   - Each tuning job has a `tuned_model.endpoint` field

4. **No Generation Config Needed**
   - Tuned models use the parameters from training
   - Don't pass `generation_config` parameter
   - Simply call: `model.generate_content(prompt)`

## Technical Details

### Why This Fix Works

1. **Gemini Tuned Models Use Different API**
   - Base models: Use model resource name directly
   - Tuned models: Use endpoint resource name
   - The GenerativeModel class routes to the correct API based on resource type

2. **Endpoint vs Model Resources**
   - Model resource: Metadata about the tuned model
   - Endpoint resource: Actual inference endpoint
   - GenerativeModel needs the endpoint to make predictions

3. **Gemini Cannot Use Predict API**
   - Error: "Gemini cannot be accessed through Vertex Predict/RawPredict API"
   - Must use GenerativeModel.generate_content()
   - But with the endpoint resource, not model resource

## References

- [Vertex AI Gemini Tuning Docs](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-tuning)
- [GenerativeModel API](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Fine-Tuned Model Usage](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-use-supervised-tuning)

## Next Steps

1. **Test Your Models**
   ```bash
   python test_models.py
   ```

2. **Generate Test Puzzle**
   ```bash
   python src/orchestrator.py --prompt "Create a space-themed crossword"
   ```

3. **Monitor Performance**
   - Check generation quality
   - Verify JSON output format
   - Adjust temperature if needed

---

**Status:** ✅ FIXED
**Date:** 2025-11-27
**Files Modified:** `src/orchestrator.py`, `test_models.py`
