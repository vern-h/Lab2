import os
from io import StringIO

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI()

# S3 config for cloud: set S3_RESULTS_BUCKET and optional S3_RESULTS_KEY (default: results/part-00000)
S3_BUCKET = os.environ.get("S3_RESULTS_BUCKET")
S3_KEY = os.environ.get("S3_RESULTS_KEY", "results/part-00000")

# Local fallback when not using S3
PART_FILE = Path(__file__).parent / "part-00000"
if not PART_FILE.exists():
    PART_FILE = Path(__file__).parent.parent / "data-analysis" / "part-00000"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_part_content(content: str) -> list[dict]:
    results = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            user_id = parts[0]
            follower_count = parts[1].split(":")[1]
            followee_count = parts[2].split(":")[1]
        except IndexError:
            continue
        results.append({
            "id": user_id,
            "followers": follower_count,
            "followees": followee_count
        })
    return results


def _get_stats_impl():
    if S3_BUCKET:
        import boto3
        s3 = boto3.client("s3")
        if S3_KEY.endswith("/"):
            prefix = S3_KEY
            resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
            keys = [obj["Key"] for obj in resp.get("Contents", []) if "part-" in obj["Key"]]
        else:
            keys = [S3_KEY]
        results = []
        for key in sorted(keys):
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            content = obj["Body"].read().decode("utf-8")
            results.extend(_parse_part_content(content))
        return results
    if not PART_FILE.exists():
        return []
    with open(PART_FILE, "r") as f:
        return _parse_part_content(f.read())


@app.get("/user-stats")
@app.get("/prod/user-stats")
def get_stats():
    try:
        return _get_stats_impl()
    except Exception as e:
        import traceback
        return {"error": str(e), "detail": traceback.format_exc()}


@app.get("/ping")
@app.get("/prod/ping")
def ping():
    return {"ok": True, "bucket": S3_BUCKET, "key": S3_KEY}


# Lambda entrypoint (for AWS deployment)
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = None