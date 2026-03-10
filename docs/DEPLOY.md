# Deploy to AWS — Step-by-step guide

Deploy the full stack on AWS: **S3** → **EMR** (MapReduce) → **Lambda + API Gateway** (backend) → **S3 + CloudFront** (frontend).

Use one region for everything (e.g. `us-east-1`). Replace placeholders:

- `YOUR_BUCKET` — a globally unique S3 bucket name (e.g. `twitter-stats-yourname-2025`)
- `us-east-1` — your chosen AWS region

---

## Prerequisites

- AWS CLI installed and configured (`aws configure`) with a user that can create S3, EMR, IAM, Lambda, API Gateway, CloudFront
- Node.js and Python 3 on your machine for building and packaging

---

## Phase 1 — S3 and data

### Step 1.1 — Create the S3 bucket

```bash
# Pick a unique bucket name (must be globally unique)
export AWS_REGION=us-east-1
export BUCKET=YOUR_BUCKET

aws s3 mb s3://$BUCKET --region $AWS_REGION
```

### Step 1.2 — Upload input data and scripts

From your project root (`Lab2/`):

```bash
# Input data for MapReduce (this can take a few minutes for a large file)
aws s3 cp data-analysis/twitter_combined.txt s3://$BUCKET/input/twitter_combined.txt

# Mapper and reducer for EMR
aws s3 cp data-analysis/mapper.py s3://$BUCKET/scripts/mapper.py
aws s3 cp data-analysis/reducer.py s3://$BUCKET/scripts/reducer.py
```

### Step 1.3 — Verify

```bash
aws s3 ls s3://$BUCKET/input/
aws s3 ls s3://$BUCKET/scripts/
```

You should see `twitter_combined.txt` under `input/` and `mapper.py`, `reducer.py` under `scripts/`.

---

## Phase 2 — EMR MapReduce job

### Step 2.1 — Create EMR streaming step file

From project root, set your bucket and generate the step file (replaces `YOUR_BUCKET` in `docs/emr-streaming-step.json`):

```bash
export BUCKET=YOUR_BUCKET
sed "s/YOUR_BUCKET/$BUCKET/g" docs/emr-streaming-step.json > docs/emr-step-generated.json
```

### Step 2.2 — Create EMR cluster and run the step

**Using the AWS Console (GUI)?** You do **not** need to run the CLI command below. Create the cluster, then add a step. Many consoles only show **Custom JAR**, **Hive**, and **Shell script** (no "Streaming program"). Use **Custom JAR** as follows:

1. **Step type:** **Custom JAR**.
2. **Name:** `Twitter stats streaming`.
3. **JAR location:** `command-runner.jar` (type exactly that; it is on the cluster).
4. **Arguments:** paste this single line (one line, no line break):
   ```
   hadoop-streaming,-files,s3://lab2-twitter-stats/scripts/mapper.py,s3://lab2-twitter-stats/scripts/reducer.py,-mapper,python3 mapper.py,-reducer,python3 reducer.py,-input,s3://lab2-twitter-stats/input/,-output,s3://lab2-twitter-stats/output/
   ```
5. **Action if step fails:** **Continue**.
6. Save the step and start the cluster. Wait for the step to **Complete** (Step 2.3).

**Using the CLI:** You need an EC2 key pair in that region for SSH (optional but useful). If you don’t have one, create one in the EC2 console (Key Pairs), then set `YOUR_KEY_NAME` below. You can run without a key; the job will still run and write output to S3.

**Without a key (no SSH):**

```bash
export AWS_REGION=us-east-1

aws emr create-cluster \
  --name "twitter-stats" \
  --release-label emr-6.15.0 \
  --applications Name=Hadoop \
  --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole \
  --instance-groups \
    InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m5.xlarge \
    InstanceGroupType=CORE,InstanceCount=2,InstanceType=m5.xlarge \
  --service-role EMR_DefaultRole \
  --steps file://docs/emr-step-generated.json \
  --region $AWS_REGION
```

**With a key (allows SSH):** use `--ec2-attributes KeyName=YOUR_KEY_NAME,InstanceProfile=EMR_EC2_DefaultRole`

Note the **ClusterId** from the output.

### Step 2.3 — Wait for the job to finish

- In the AWS Console: **EMR → Clusters → your cluster → Steps**. Wait until the “Twitter stats streaming” step is **Completed**.
- Or poll with CLI (replace `j-XXXXXXXXXXXXX` with your ClusterId):

```bash
aws emr describe-cluster --cluster-id j-XXXXXXXXXXXXX --query 'Cluster.Status.State'
aws emr list-steps --cluster-id j-XXXXXXXXXXXXX --query 'Steps[*].[Name,Status.State]' --output table
```

### Step 2.4 — Check EMR output in S3

```bash
aws s3 ls s3://$BUCKET/output/
```

You should see at least `part-00000` (and possibly more part files). The backend will use `output/part-00000` by default; if you use a different part file, set `S3_RESULTS_KEY` accordingly later.

---

## Phase 3 — Backend (Lambda + API Gateway)

The backend runs as a Lambda function and is exposed via HTTP API Gateway. It reads the MapReduce result from S3.

### Step 3.1 — Create a deployment package (zip) for Lambda

From project root:

```bash
cd backend
pip install -r requirements.txt -t package/
cp main.py package/
cd package && zip -r ../lambda-deploy.zip . && cd ..
```

You should have `backend/lambda-deploy.zip`.

### Step 3.2 — Create an IAM role for Lambda

The role must allow Lambda to read from your S3 bucket and write logs.

1. **IAM → Roles → Create role**
2. **Trusted entity:** AWS service → **Lambda**
3. **Permissions:** Create (or attach) a policy that allows:
   - `s3:GetObject` on `arn:aws:s3:::YOUR_BUCKET/*`
   - `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
4. Name the role e.g. `twitter-stats-lambda-role` and note its **ARN**.

Alternatively, attach **AmazonS3ReadOnlyAccess** (or a custom policy scoped to your bucket) and **AWSLambdaBasicExecutionRole**.

### Step 3.3 — Create the Lambda function

```bash
export AWS_REGION=us-east-1
export BUCKET=YOUR_BUCKET
export LAMBDA_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT_ID:role/twitter-stats-lambda-role

aws lambda create-function \
  --function-name twitter-stats-api \
  --runtime python3.11 \
  --role $LAMBDA_ROLE_ARN \
  --handler main.handler \
  --zip-file fileb://lambda-deploy.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment "Variables={S3_RESULTS_BUCKET=$BUCKET,S3_RESULTS_KEY=output/part-00000}" \
  --region $AWS_REGION
```

If the function already exists, update code and env:

```bash
aws lambda update-function-code --function-name twitter-stats-api --zip-file fileb://lambda-deploy.zip
aws lambda update-function-configuration --function-name twitter-stats-api \
  --environment "Variables={S3_RESULTS_BUCKET=$BUCKET,S3_RESULTS_KEY=output/part-00000}"
```

### Step 3.4 — Create HTTP API and connect Lambda

1. **API Gateway → Create API → HTTP API → Build**
2. **Integrations → Add integration → Lambda** → select region and `twitter-stats-api`
3. **Routes → Create** route: `GET /user-stats`, integration: `twitter-stats-api`
4. **Stages:** Create stage (e.g. `$default` or `prod`). Copy the **Invoke URL** (e.g. `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`).

This is your **backend URL**. The frontend will call `https://<invoke-url>/user-stats`.

(Optional) Enable CORS in API Gateway for your frontend origin.

---

## Phase 4 — Frontend (S3 + CloudFront)

### Step 4.1 — Build the frontend with the backend URL

Set the backend URL to the API Gateway Invoke URL from Phase 3:

```bash
cd frontend-app
echo "VITE_API_URL=https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com" > .env.production
npm ci
npm run build
```

Use the exact Invoke URL (no path), e.g. `https://abc123xyz.execute-api.us-east-1.amazonaws.com`. The app will request `{VITE_API_URL}/user-stats`.

### Step 4.2 — Deploy frontend to Vercel (alternative to S3 + CloudFront)

1. **Sign up / log in:** Go to [vercel.com](https://vercel.com) and sign in (e.g. with GitHub).
2. **Import project:** Click **Add New** → **Project**. Import your repo (e.g. from GitHub). If the repo is not on GitHub yet, push **Lab2** to a GitHub repo first, then import that repo.
3. **Configure project:**
   - **Root Directory:** Click **Edit** and set to **`frontend-app`** (so Vercel builds that folder only).
   - **Framework Preset:** Vite (should be auto-detected).
   - **Build Command:** `npm run build` (default).
   - **Output Directory:** `dist` (default).
   - **Environment variables:** Click **Add** and add:
     - **Name:** `VITE_API_URL`
     - **Value:** `https://ynj3yujpi0.execute-api.us-east-1.amazonaws.com/prod` (your API Gateway base URL, no trailing slash).
4. Click **Deploy**. Wait for the build to finish.
5. Your app will be at a URL like **`https://your-project.vercel.app`**. Open it; the frontend will call your Lambda API at `/user-stats`.

**To update the API URL later:** Project → **Settings** → **Environment Variables** → edit `VITE_API_URL` → **Redeploy**.

### Step 4.3 — Create S3 bucket for the frontend (AWS Console, optional)

1. Open **S3** in the AWS Console.
2. Click **Create bucket**.
3. **Bucket name:** e.g. `twitter-stats-frontend-YOURNAME` (globally unique).
4. **Region:** same as your API (e.g. `us-east-1`).
5. Leave **Block Public Access** as-is for now (CloudFront will access the bucket via an origin access identity or public read later; see Step 4.4).
6. Click **Create bucket**.

### Step 4.4 — Upload the build and enable static website hosting (AWS Console)

**Upload the build:**

1. In **S3**, open the bucket you created (e.g. `twitter-stats-frontend-YOURNAME`).
2. Click **Upload**.
3. Click **Add files** and select **all files and folders** inside your local **`frontend-app/dist/`** folder (after `npm run build`). You can drag the contents of `dist/` so that `index.html` and `assets/` (or similar) are at the **root** of the bucket, not inside a `dist` folder.
4. Click **Upload** and wait for it to finish.

**Enable static website hosting:**

1. In the same bucket, open the **Properties** tab.
2. Scroll to **Static website hosting** → **Edit**.
3. Choose **Enable**.
4. **Hosting type:** Host a static website.
5. **Index document:** `index.html`.
6. **Error document:** `index.html` (so SPA routes work on refresh).
7. **Save changes**.
8. Note the **Bucket website endpoint** (e.g. `http://twitter-stats-frontend-YOURNAME.s3-website-us-east-1.amazonaws.com`). You’ll use this as the CloudFront origin.

### Step 4.5 — Create a CloudFront distribution (AWS Console)

1. Open **CloudFront** in the AWS Console.
2. Click **Create distribution**.
3. **Origin settings:**
   - **Origin domain:** Click the field and choose the **S3 website endpoint** for your bucket (e.g. `twitter-stats-frontend-YOURNAME.s3-website-us-east-1.amazonaws.com`). Do **not** pick the bucket’s regular S3 endpoint (the one ending in `.s3.amazonaws.com` or `.s3.region.amazonaws.com`); use the **website** endpoint so the S3 website config is used.
   - **Name** is filled automatically.
   - **Enable Origin Shield:** No (optional).
4. **Default cache behavior:** Leave defaults; set **Viewer protocol policy** to **Redirect HTTP to HTTPS** if you want.
5. **Settings:**
   - **Default root object:** `index.html`.
   - **Alternate domain names (CNAMEs):** optional.
   - **Custom SSL certificate:** optional (default certificate is fine).
6. **Error pages (recommended for SPA):**
   - Click **Create custom error response**.
   - **HTTP error code:** `403` → **Response page path:** `/index.html` → **HTTP response code:** `200` → **Create**.
   - Create another: **HTTP error code:** `404` → **Response page path:** `/index.html` → **HTTP response code:** `200` → **Create**.
7. Click **Create distribution**.
8. Wait until **Status** is **Enabled** (a few minutes). Copy the **Distribution domain name** (e.g. `d1234abcd.cloudfront.net`). Your app URL is **`https://d1234abcd.cloudfront.net`**.

---

## Phase 5 — CORS (if the frontend can’t call the API)

If the browser blocks requests from your CloudFront URL to API Gateway:

1. **API Gateway → Your API → CORS**
2. Add your frontend origin (e.g. `https://d1234abcd.cloudfront.net`) and allow `GET`.
3. Redeploy the API stage.

Your backend FastAPI app already sends `Access-Control-Allow-Origin: *`; if you restrict CORS in API Gateway, ensure the frontend origin is allowed there.

---

## Checklist

| Phase | Step | Done |
|-------|------|------|
| 1 | Create S3 bucket, upload `twitter_combined.txt`, `mapper.py`, `reducer.py` | ☐ |
| 2 | Create EMR cluster with streaming step, wait for completion, confirm `output/part-00000` in S3 | ☐ |
| 3 | Package backend (zip), create Lambda role, create Lambda with S3 env, create HTTP API and GET /user-stats | ☐ |
| 4 | Build frontend with `VITE_API_URL`, upload to S3, create CloudFront distribution | ☐ |
| 5 | Fix CORS on API Gateway if needed | ☐ |

---

## Quick reference

| What | Where |
|------|--------|
| Input data | `s3://YOUR_BUCKET/input/twitter_combined.txt` |
| MapReduce scripts | `s3://YOUR_BUCKET/scripts/mapper.py`, `reducer.py` |
| EMR output | `s3://YOUR_BUCKET/output/part-00000` |
| Backend | Lambda `twitter-stats-api` + API Gateway GET `/user-stats` |
| Backend env | `S3_RESULTS_BUCKET=YOUR_BUCKET`, `S3_RESULTS_KEY=output/part-00000` |
| Frontend | S3 bucket + CloudFront URL |

---

## Troubleshooting

- **Lambda can’t read S3:** Check the Lambda execution role has `s3:GetObject` on `s3://YOUR_BUCKET/output/*`.
- **EMR step fails:** Check EMR cluster logs and that the bucket and paths in the step JSON match. Ensure `mapper.py` and `reducer.py` are executable or invoked as `python3 mapper.py`.
- **Frontend shows no data:** Confirm `VITE_API_URL` in `.env.production` has no trailing slash and is the API Gateway Invoke URL. Open DevTools → Network and check the `/user-stats` request and CORS errors.
- **403/404 on refresh (SPA):** Configure CloudFront error pages to return `index.html` with 200 for 403 and 404.
