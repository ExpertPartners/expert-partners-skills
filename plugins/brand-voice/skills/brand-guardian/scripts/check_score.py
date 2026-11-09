"""Check an editorial score record, not the quality of the writing."""

import json
import math
import sys
from pathlib import Path


def check_score(record):
    if not isinstance(record, dict):
        raise ValueError("score record must be an object")
    score = record.get("score")
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not 0 <= score <= 100
        or not math.isfinite(score)
    ):
        raise ValueError("score must be a finite number from 0 to 100")
    problems = record.get("problems")
    if not isinstance(problems, list) or any(
        not isinstance(problem, str) or not problem.strip() for problem in problems
    ):
        raise ValueError("problems must be an array of nonempty strings")
    return {**record, "result": "PASS" if score >= 90 else "FAIL"}


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError("usage: check_score.py /absolute/path/score-record.json")
        record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = check_score(record)
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}))
        return 1
    print(json.dumps({"valid": True, "record": result}, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
