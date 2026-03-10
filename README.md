# Twitter User Statistics

A small full-stack app: MapReduce (Python) computes follower/followee counts from a Twitter edge list; a FastAPI backend serves the results; a React frontend displays them.

---

## Run locally (check current outlook)

From the project root (`Lab2/`).

### 1. Backend (API)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Leave this running. The API reads `part-00000` from `backend/` or `data-analysis/`.

### 2. Frontend

In a new terminal:

```bash
cd frontend-app
npm install
npm run dev
```

Open the URL shown (e.g. **http://localhost:5173**). The app calls `http://localhost:8000/user-stats` by default.

---

## If you don’t have `part-00000` yet

Generate it with MapReduce (from project root):

```bash
cd data-analysis
cat twitter_combined.txt | python3 mapper.py | sort | python3 reducer.py > part-00000
```

Then copy (or symlink) `part-00000` into `backend/`, or leave it in `data-analysis/` — the backend looks in both places.

---

## Project layout

| Folder / file      | Purpose                          |
|--------------------|----------------------------------|
| `data-analysis/`   | Mapper, reducer, input data      |
| `backend/`         | FastAPI app, serves `/user-stats`|
| `frontend-app/`    | React (Vite) UI                  |
| `docs/DEPLOY.md`   | Step-by-step AWS deployment      |
