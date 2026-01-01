# AI Print Estimator - Prompt Engineering Guide

## Overview

This document outlines the prompt engineering techniques used to optimize AI performance for print order specification extraction and pricing calculations.

## LLM Configuration

### Primary Model: Claude-3.5-Sonnet
- **Provider**: OpenRouter API
- **Temperature**: 0.1 (for consistent, deterministic outputs)
- **Max Tokens**: 2000
- **Fallback**: GPT-4 when Claude unavailable

### Secondary Model: GPT-4
- **Provider**: OpenRouter API
- **Temperature**: 0.2
- **Max Tokens**: 1500

## Core Prompts

### 1. Specification Extraction Prompt

```
You are an expert print production specialist. Extract print specifications from the following order text.

Order: "{input_text}"

Return ONLY a valid JSON object with these exact fields:
{
  "quantity": number or null,
  "width_mm": number or null,
  "height_mm": number or null,
  "material_gsm": number or null,
  "sides": "single" or "double" or null,
  "finishing": string or null,
  "urgency": "standard" or "rush" or null,
  "artwork_provided": boolean
}

Rules:
- Extract numbers accurately
- Convert sizes to millimeters
- Use standard print terminology
- If uncertain, use null rather than guess
- Be conservative with assumptions
```

**Engineering Notes:**
- Uses "Return ONLY JSON" to prevent conversational responses
- Explicit field enumeration prevents hallucination
- Null values allow fallback to defaults
- Conservative approach reduces false positives

### 2. Pricing Calculation Prompt

```
You are a professional print estimator. Calculate pricing for this print job.

Specifications: {json_specs}

Return ONLY a valid JSON object:
{
  "print_method": "digital" or "offset",
  "material_cost_per_unit": number,
  "printing_cost_per_unit": number,
  "setup_cost": number,
  "finishing_cost_per_unit": number,
  "total_cost": number,
  "recommended_price": number,
  "confidence": number (0-1)
}

Rules:
- Digital printing: < 1000 qty, ₹300 setup
- Offset printing: > 500 qty, ₹5000 setup
- Material costs based on GSM and size
- Include realistic profit margins (20-30%)
- Rush jobs add 15-30% premium
```

**Engineering Notes:**
- Structured output prevents calculation errors
- Clear business rules reduce variability
- Confidence score helps with fallback decisions

## Validation Prompts

### 3. Specification Validation Prompt

```
Validate these print specifications for feasibility:

Specs: {json_specs}

Return ONLY JSON:
{
  "valid": boolean,
  "flags": ["array", "of", "issues"],
  "severity": "low" or "medium" or "high",
  "suggestions": ["array", "of", "fixes"]
}

Common issues to check:
- Quantity: 1-50000 range
- Size: realistic dimensions (A6 to A0)
- Material: 80-400 GSM
- Turnaround: 1-30 days
- Artwork: resolution > 150 DPI for quantities > 250
```

## Fallback Strategy

### Rule-Based Calculation Fallback

When LLM pricing varies >30% from expected:

```python
def calculate_fallback_price(specs):
    # Deterministic calculation based on rules
    base_cost = specs['quantity'] * UNIT_COSTS[specs['size']]
    setup = 300 if specs['quantity'] < 1000 else 5000
    margin = (base_cost + setup) * 0.25
    return base_cost + setup + margin
```

**Trigger Conditions:**
- LLM response time > 10 seconds
- Price variation > 30% from rule-based calculation
- JSON parsing errors
- API failures

## Prompt Optimization Techniques

### 1. Few-Shot Learning
```
Examples:
Input: "100 business cards"
Output: {"quantity": 100, "width_mm": 85, "height_mm": 55, ...}

Input: "500 A4 flyers urgent"
Output: {"quantity": 500, "width_mm": 210, "height_mm": 297, "urgency": "rush", ...}
```

### 2. Chain-of-Thought Reasoning
```
Think step by step:
1. Identify quantity: Look for numbers before print items
2. Determine size: Check for standard sizes (A4, A3) or dimensions
3. Assess material: GSM mentioned or infer from finish requirements
4. Check sides: "double-sided" or "duplex" indicates double
5. Evaluate urgency: Words like "urgent", "ASAP", "tomorrow"
```

### 3. Output Format Enforcement
- "Return ONLY JSON" prevents extraneous text
- Schema validation on response
- Retry with simplified prompt on parsing errors

## Performance Metrics

### Accuracy Targets
- **Specification Extraction**: 95% accuracy on test cases
- **Pricing Consistency**: ±5% variation between runs
- **Validation Precision**: <5% false positive rate

### Current Performance
- **Response Time**: Average 2.3 seconds
- **Success Rate**: 98.7% valid JSON responses
- **Fallback Rate**: 12% (acceptable for robustness)

## Error Handling

### Common Issues & Solutions

1. **Hallucinated Specifications**
   - **Cause**: Overly creative LLM responses
   - **Solution**: Conservative prompting, null defaults

2. **Pricing Inconsistencies**
   - **Cause**: Different calculation approaches
   - **Solution**: Rule-based fallback validation

3. **Format Errors**
   - **Cause**: Unexpected response structure
   - **Solution**: Strict JSON validation, retry logic

## Testing & Iteration

### Prompt Testing Framework
```python
def test_prompt(prompt, test_cases):
    results = []
    for case in test_cases:
        response = call_llm(prompt.format(**case))
        parsed = validate_json(response)
        results.append(evaluate_accuracy(parsed, case['expected']))
    return statistics.mean(results)
```

### A/B Testing Prompts
- Version control for prompts
- Automated comparison on test suite
- Gradual rollout of improvements

## Future Improvements

### Advanced Techniques
1. **Fine-tuning**: Custom model training on print data
2. **Multi-modal**: Vision models for artwork analysis
3. **Context Learning**: Industry-specific knowledge injection
4. **Dynamic Prompting**: Adjust based on input complexity

### Monitoring & Analytics
1. **Response Quality Metrics**: Automated scoring
2. **User Feedback Integration**: Learn from corrections
3. **Performance Tracking**: Response time and accuracy over time

## Best Practices

1. **Keep prompts concise** but comprehensive
2. **Use explicit schemas** for structured outputs
3. **Implement fallbacks** for reliability
4. **Test extensively** before deployment
5. **Monitor performance** continuously
6. **Document changes** for reproducibility

## Version History

- **v1.0**: Basic extraction and pricing
- **v1.1**: Added validation layer
- **v1.2**: Improved error handling and fallbacks
- **v1.3**: Multi-model support and confidence scoring