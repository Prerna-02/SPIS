# Push This Project to GitHub

The project is already committed locally. To push to GitHub:

## 1. Create a new repository on GitHub

1. Go to [https://github.com/new](https://github.com/new).
2. Choose a name (e.g. `DL_Final_Project` or `SPIS`).
3. **Do not** initialize with README, .gitignore, or license (we already have them).
4. Click **Create repository**.

## 2. Add the remote and push

In PowerShell, from the project root (`e:\DL_Final_Project`):

```powershell
# Replace YOUR_USERNAME and YOUR_REPO with your GitHub username and repo name
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push the main branch
git push -u origin main
```

If your branch is named `master` instead of `main`:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## 3. If you use SSH

```powershell
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

After this, your full project will be on GitHub. For future updates: `git add -A`, `git commit -m "message"`, then `git push`.
