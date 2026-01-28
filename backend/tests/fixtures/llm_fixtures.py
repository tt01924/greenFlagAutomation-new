"""Test fixtures for LLM classification responses."""

from typing import Dict, Any


def get_mock_classification_response_high_confidence() -> str:
    """Get mock LLM classification response with high confidence.

    Returns:
        Mock JSON response string
    """
    return """
    {
      "classifications": [
        {
          "response_id": "iam-request",
          "confidence": 0.92,
          "reasoning": "Clear mention of IAM permissions needed for AWS resources (S3, DynamoDB)"
        },
        {
          "response_id": "access-request",
          "confidence": 0.45,
          "reasoning": "General access request but specific to AWS IAM"
        },
        {
          "response_id": "empty-s3-bucket",
          "confidence": 0.15,
          "reasoning": "Mentions S3 but not about emptying buckets"
        }
      ],
      "overall_assessment": "This is a clear IAM permission request for AWS resources",
      "flags": {
        "sensitive_data_detected": false,
        "multiple_questions": false,
        "urgent_tone": false
      }
    }
    """


def get_mock_classification_response_low_confidence() -> str:
    """Get mock LLM classification response with low confidence.

    Returns:
        Mock JSON response string
    """
    return """
    {
      "classifications": [
        {
          "response_id": "cortex-bug",
          "confidence": 0.55,
          "reasoning": "Mentions something broken but unclear what system"
        },
        {
          "response_id": "documentation-request",
          "confidence": 0.48,
          "reasoning": "Asking for help which could be documentation"
        },
        {
          "response_id": "iam-request",
          "confidence": 0.35,
          "reasoning": "No clear indication of IAM needs"
        }
      ],
      "overall_assessment": "Unclear ticket, multiple interpretations possible",
      "flags": {
        "sensitive_data_detected": false,
        "multiple_questions": true,
        "urgent_tone": false
      }
    }
    """


def get_mock_classification_response_ambiguous() -> str:
    """Get mock LLM classification response with ambiguous match.

    Returns:
        Mock JSON response string
    """
    return """
    {
      "classifications": [
        {
          "response_id": "cortex-bug",
          "confidence": 0.78,
          "reasoning": "Mentions Cortex and something not working"
        },
        {
          "response_id": "cortex-feature-request",
          "confidence": 0.76,
          "reasoning": "Could also be requesting a new feature in Cortex"
        },
        {
          "response_id": "documentation-request",
          "confidence": 0.32,
          "reasoning": "Unlikely to be a documentation request"
        }
      ],
      "overall_assessment": "Ambiguous - could be bug or feature request for Cortex",
      "flags": {
        "sensitive_data_detected": false,
        "multiple_questions": false,
        "urgent_tone": false
      }
    }
    """


def get_mock_classification_response_sensitive_data() -> str:
    """Get mock LLM classification response with sensitive data flag.

    Returns:
        Mock JSON response string
    """
    return """
    {
      "classifications": [
        {
          "response_id": "access-request",
          "confidence": 0.85,
          "reasoning": "Clear access request"
        }
      ],
      "overall_assessment": "Access request but contains sensitive credentials",
      "flags": {
        "sensitive_data_detected": true,
        "multiple_questions": false,
        "urgent_tone": false
      }
    }
    """
