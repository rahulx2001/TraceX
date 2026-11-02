"""Prepare the complete synthetic safety walkthrough in the configured warehouse.

Run with the same environment as the server, while it is stopped:
    python -m scripts.safety_campaign_seed

Idempotent: reuses the prepared scenario and preserves later operator changes.
Does not make model calls, contact owners, book workshops or reset databases.
"""
import json


def main():
    from src.ai_layer.safety_campaigns import prepared_demo_campaign

    result = prepared_demo_campaign("demo_setup", "service")
    print(json.dumps({"campaign_id": result["campaign_id"], "synthetic_demo": result["synthetic_demo"],
                      "metrics": result["metrics"], "demo_version": result["demo_version"]}, indent=2))


if __name__ == "__main__":
    main()
