"""Minimal gateway stub for the sample fixture repository."""

import json


def main() -> None:
    print(json.dumps({"status": "success", "output": {}}))


if __name__ == "__main__":
    main()
