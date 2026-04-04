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

Your ACLED email and password need to be stored securely in GitHub so the
script can use them when it runs in the cloud — without ever being visible
in your code.

1. In your repo, click the **Settings** tab along the top navigation bar
   (you need to be the repo owner to see this tab)

2. In the left sidebar, scroll down to **Security** and click
   **Secrets and variables** → then click **Actions** in the submenu

3. You will see a page titled "Actions secrets and variables".
   Click the green **New repository secret** button in the top right.

4. Add the first secret:
   - **Name:** `ACLED_EMAIL`
   - **Secret:** `your-acled-email@example.com`
   - Click **Add secret**

5. Click **New repository secret** again to add the second:
   - **Name:** `ACLED_PASSWORD`
   - **Secret:** `your-acled-password`
   - Click **Add secret**

6. You should now see both `ACLED_EMAIL` and `ACLED_PASSWORD` listed
   on the secrets page. The values are hidden and cannot be read back
   by anyone — not even you. They are only injected into the script
   when the workflow runs.

---

## STEP 5 — Create a Personal Access Token (PAT)

The web page needs a special token to tell GitHub "please trigger the
workflow on my behalf." This is separate from your GitHub password.

1. Click your **profile photo** in the top right corner of GitHub
   and select **Settings** from the dropdown menu

2. Scroll all the way down the left sidebar and click
   **Developer settings** (it's at the very bottom)

3. In the left sidebar click **Personal access tokens** →
   then click **Tokens (classic)**

4. Click **Generate new token** → select **Generate new token (classic)**

5. Fill in the form:
   - **Note:** `acled-fetcher` (just a label so you remember what it's for)
   - **Expiration:** Click the dropdown and select **No expiration**
     (or choose 1 year if you prefer it to expire automatically)

6. Scroll down to **Select scopes** and tick the following two boxes:
   - ✅ **repo** — tick the top-level `repo` checkbox, which will
     automatically tick all the sub-options beneath it
   - ✅ **workflow** — scroll down a little to find this and tick it

7. Scroll to the bottom and click the green **Generate token** button

8. GitHub will now show you the token — it starts with `ghp_`.
   **Copy it immediately and paste it somewhere safe** (a notes app,
   password manager, etc). GitHub will never show it to you again.
   If you lose it you will need to generate a new one.

---

## STEP 6 — Configure the Web Page

Now you need to put your GitHub username, repo name, token, and a team
password into the web page so it knows where to send requests.

1. In your repo, navigate to the `docs/` folder and click `index.html`

2. Click the **pencil icon** (Edit this file) in the top right of the
   file viewer

3. Near the bottom of the file, find this block — it's clearly labelled
   with a `CONFIGURATION` comment:

```javascript
const GITHUB_OWNER  = "YOUR_GITHUB_USERNAME";
const GITHUB_REPO   = "YOUR_REPO_NAME";
const GITHUB_TOKEN  = "YOUR_PERSONAL_ACCESS_TOKEN";
const PAGE_PASSWORD = "YOUR_TEAM_PASSWORD";
```

4. Replace each value inside the quotes:
   - `GITHUB_OWNER` → your GitHub username exactly as it appears on
     your profile (e.g. `"ellisdjones"`)
   - `GITHUB_REPO` → the repo name you created in Step 2
     (e.g. `"acled-fetcher"`)
   - `GITHUB_TOKEN` → paste the token you copied in Step 5
     (e.g. `"ghp_abc123..."`)
   - `PAGE_PASSWORD` → choose any password for your team to use when
     they open the page (e.g. `"acled2025"`)

5. Scroll to the bottom of the page. Under **Commit changes**, leave
   the default option ("Commit directly to the main branch") selected
   and click **Commit changes**

---

## STEP 7 — Enable GitHub Pages

This is what turns your `docs/index.html` file into a live website.

1. In your repo click the **Settings** tab

2. In the left sidebar click **Pages**
   (under the "Code and automation" section)

3. Under **Build and deployment**, find the **Source** dropdown
   and make sure it is set to **Deploy from a branch**

4. Under **Branch**, click the first dropdown and select **main**.
   Then click the second dropdown (which shows `/ (root)`) and
   change it to **/docs**

5. Click **Save**

6. Wait about 60 seconds, then refresh the Settings → Pages page.
   You will see a green banner that says:
   > "Your site is live at https://YOUR_USERNAME.github.io/acled-fetcher/"

7. Click that link to confirm the page loads. You should see the
   ACLED Fetcher password screen.

---

## STEP 8 — Test It End to End

Before sharing with your team, run a full test yourself:

1. Open your GitHub Pages URL in a browser

2. Enter the team password you set in Step 6 and click **Continue**

3. Type a country name in the box — use `Mali` for the first test
   as you know there is data available for it

4. Click **Run Fetch** and watch the loading screen. You will see
   the steps tick off one by one as the workflow progresses:
   - ✅ Triggering GitHub Action
   - ✅ Connecting to ACLED API
   - ✅ Fetching conflict events
   - ✅ Processing & saving data

5. After ~60–90 seconds the results will appear automatically showing
   total events, total fatalities, and a breakdown by event type

6. To verify the data was saved, go back to your GitHub repo and
   check the `data/` folder — you should see a file called
   `risk_data_mali.json`

---

## Sharing with Your Team

Send your team two things:
- The GitHub Pages URL: `https://YOUR_USERNAME.github.io/acled-fetcher/`
- The team password you set in Step 6

That is all they need. No GitHub account, no Python, no installs.

---

## Troubleshooting

**"Failed to trigger workflow"**
→ Your PAT token in `index.html` is likely wrong or missing the `workflow`
  scope. Go back to Step 5, generate a new token, and update `index.html`

**Page shows password screen but nothing happens after clicking Continue**
→ The password in `index.html` doesn't match what you typed. Re-check the
  `PAGE_PASSWORD` value you set in Step 6 — it is case-sensitive

**Results show 0 events**
→ The ACLED account has a data access restriction that limits how recent
  the data can be. The date range in `acled_fetch.py` needs to fall within
  your account's allowed window. Check with ACLED about your access tier.

**GitHub Pages URL returns a 404**
→ Pages can take up to 2 minutes to go live after first enabling it.
  Also double-check that the Branch is set to `main` and folder to `/docs`
  in Settings → Pages

**The workflow runs but fails (red X in GitHub Actions)**
→ Go to your repo → click the **Actions** tab → click the failed run →
  click the **fetch** job → read the error output to see what went wrong.
  Most commonly this is a missing secret (Step 4) or a Python error.
