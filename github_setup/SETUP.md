# ACLED Fetcher — Setup Guide

Follow these steps in order. Should take about 15 minutes.

---

## STEP 1 — Create a GitHub Account

1. Go to https://github.com and click **Sign up**
2. Choose a username, enter your email and a password
3. Verify your email address

---

## STEP 2 — Create a New Repository

1. Once logged in, click the **+** icon (top right) → **New repository**
2. Fill in:
   - **Repository name:** `acled-fetcher` (or any name you like)
   - **Visibility:** Public ✅ (required for free GitHub Pages)
   - Leave everything else as default
3. Click **Create repository**

---

## STEP 3 — Upload the Project Files

In your new repo, click **uploading an existing file** and upload everything
in this folder, keeping the folder structure intact:

```
.github/
  workflows/
    fetch_acled.yml
_scripts/
  acled_fetch.py
  fetch_data.py
docs/
  index.html
requirements.txt
```

To upload with folders intact, it's easiest to drag the entire folder into
the GitHub upload area. Then click **Commit changes**.

---

## STEP 4 — Add Your ACLED Credentials as Secrets

This keeps your password out of the code and out of public view.

1. In your repo, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** and add:
   - Name: `ACLED_EMAIL`     Value: `ellisdjones0607@hotmail.com`
   - Name: `ACLED_PASSWORD`  Value: `NaSaeu099!`

---

## STEP 5 — Create a Personal Access Token (PAT)

The web page needs a token to trigger GitHub Actions on your behalf.

1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Give it a name like `acled-fetcher`
4. Set expiration to **No expiration** (or 1 year)
5. Tick these scopes:
   - ✅ `repo` (full repo access)
   - ✅ `workflow`
6. Click **Generate token**
7. **Copy the token now** — you won't see it again

---

## STEP 6 — Configure the Web Page

Open `docs/index.html` and edit the four lines at the top of the `<script>` block:

```javascript
const GITHUB_OWNER  = "YOUR_GITHUB_USERNAME";        // your GitHub username
const GITHUB_REPO   = "acled-fetcher";               // your repo name
const GITHUB_TOKEN  = "ghp_xxxxxxxxxxxxxxxxxxxx";    // token from Step 5
const PAGE_PASSWORD = "your-team-password";          // any password you choose
```

Save the file and re-upload it to your repo (or edit it directly on GitHub
by clicking the file → pencil icon → commit changes).

---

## STEP 7 — Enable GitHub Pages

1. In your repo go to **Settings** → **Pages**
2. Under **Source**, select **Deploy from a branch**
3. Branch: **main** · Folder: **/docs**
4. Click **Save**

After about 60 seconds your page will be live at:
```
https://YOUR_GITHUB_USERNAME.github.io/acled-fetcher/
```

---

## STEP 8 — Test It

1. Open your GitHub Pages URL
2. Enter the team password you set in Step 6
3. Type a country (e.g. `Nigeria`) and click **Run Fetch**
4. Wait ~60–90 seconds for results to appear automatically

---

## Sharing with Your Team

Just send them the GitHub Pages URL and the password. They need nothing else —
no GitHub account, no Python, no installs.

---

## Troubleshooting

**"Failed to trigger workflow"**
→ Check your PAT token is correct in `index.html` and has `workflow` scope

**Results show 0 events**
→ The ACLED account may have data access restrictions — check the date range
  in `acled_fetch.py` is within your account's allowed history window

**Page not loading**
→ GitHub Pages can take 1–2 minutes to go live after first enabling it
