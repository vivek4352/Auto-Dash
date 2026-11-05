# AutoDash
Sign in with Google, upload a CSV/Excel file, and get a dashboard that only contains charts the data can support, with a full explanation of how each one was decided. Dashboards are saved to your account.

## Run
```bash
cd backend && cp .env.example .env      # then edit .env (see Google login)
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000/docs
pytest                                   # 11 tests: login/privacy, dashboard quality rules, exports

cd ../frontend && cp .env.example .env && npm install && npm run dev      # http://localhost:5173
```

## Google login (about 5 minutes)
1. Open https://console.cloud.google.com > create or pick a project > **APIs & Services > OAuth consent screen** (External, add your email as a test user).
2. **APIs & Services > Credentials > Create credentials > OAuth client ID** > type **Web application**.
3. Under **Authorized JavaScript origins** add the exact address of your frontend, e.g. `http://localhost:5173` (add every port you use, and your real domain in production). No redirect URI is needed.
4. Copy the **Client ID** into `backend/.env` as `GOOGLE_CLIENT_ID=...`, set a long random `JWT_SECRET`, and restart the backend.
5. Open the site: the Google button appears where the upload box was. After signing in, the upload box and **Your saved dashboards** appear.

*Trying it without Google:* set `AUTH_DEV_MODE=1` in `backend/.env`. A "Continue as demo user" button appears. Never enable this in production.

## How accounts and data work
- The browser gets a Google ID token; the backend verifies it with Google, then issues its own 30-day session token. Your Google password is never seen.
- Every API route except `/health` and `/api/auth/*` needs that token. A dashboard can only be opened, queried, downloaded or deleted by the account that uploaded it (anyone else gets 404).
- Users and the list of dashboards are in SQLite (`DATA_DIR/app.db`); each dataset is stored as `DATA_DIR/<id>.pkl` + `.json`. Signing in again from any browser shows your previous dashboards. Deleting a dashboard removes its data.
- Limit: `MAX_DATASETS_PER_USER` saved dashboards per account (default 25).

## Downloads
- **Interactive web page (.html)**: one offline file with live filters, tooltips and the same panels as the app.
- **Power BI kit (.zip)**: cleaned data (CSV), Power Query (M) scripts, DAX measures (including outcome rates such as Churn Rate), a theme and a guide that maps every panel to a Power BI visual. A native `.pbix` cannot be generated outside Power BI Desktop.

## How the dashboard is decided (and why it avoids misleading charts)
- Column names keep word boundaries (`MonthlyCharges` -> Monthly Charges).
- Yes/No and 0/1 columns are **flags**, never averaged like numbers. A flag whose name says it is an outcome (churn, attrition, fraud ...) becomes the **target**: the dashboard shows its rate, the groups where it is highest and lowest, and the columns that separate it most.
- Averages, rates and durations are averaged; additive amounts are summed; IDs are counted. **Share-of-total donuts only use sums or row counts.**
- No date column means **no** trend, growth, best-period, yearly or forecast widgets. A Top-N table only appears when a column has 8+ distinct values.
- Every panel's title is generated from its own query, so a title can never describe something other than what is drawn.

## Deploy
Backend: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` with `GOOGLE_CLIENT_ID`, `JWT_SECRET`, `FRONTEND_ORIGIN`, `DATA_DIR` (persistent disk); health check `/health`. Serve over HTTPS.
Frontend: set `VITE_API_URL`, `npm run build`.

## Not built yet
Column-role overrides, per-user quotas by size, password/email login, server-side PDF export, rate limiting.
