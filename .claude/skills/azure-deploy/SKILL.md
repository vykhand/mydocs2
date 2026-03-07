---
name: azure-deploy
description: Deploy to Azure by resetting azure-deployment branch to a source branch and force-pushing. Usage /azure-deploy [branch] (defaults to current branch).
argument-hint: [source-branch]
allowed-tools: Bash, AskUserQuestion
---

# Azure Deploy

Deploy to Azure by resetting the `azure-deployment` branch to match a source branch exactly, then force-pushing, and monitoring the GitHub Actions deployment workflow.

## Steps

1. Determine the source branch:
   - If `$ARGUMENTS` is provided, use it as the source branch name.
   - If no arguments, use the current branch (`git rev-parse --abbrev-ref HEAD`).

2. Verify the source branch exists (check local and remote). If it doesn't exist, report the error and stop.

3. Save the current branch name so we can return to it afterward.

4. Fetch latest from origin.

5. Ask the user for confirmation before proceeding: "Will reset `azure-deployment` to `<source-branch>` and force-push. Continue?"

6. Execute the deployment:
   ```bash
   git checkout azure-deployment
   git reset --hard <source-branch>
   git push --force origin azure-deployment
   ```

7. Return to the original branch:
   ```bash
   git checkout <original-branch>
   ```

8. Report the commit hash that `azure-deployment` now points to.

9. The force-push triggers the "Deploy to Azure AKS" workflow automatically (deploy-aks.yml, on push to azure-deployment). Wait ~10 seconds, then find the triggered run:
   ```bash
   gh api repos/:owner/:repo/actions/runs --jq '[.workflow_runs[] | select(.name=="Deploy to Azure AKS" and .head_branch=="azure-deployment")] | first | "\(.id) \(.status) \(.conclusion)"'
   ```

10. Monitor the run in the background:
    ```bash
    gh run watch <run-id> --exit-status
    ```
    Run this in background so you get notified when it completes.

11. When the run finishes, report the result (success/failure). If it failed, show the failed step logs:
    ```bash
    gh run view <run-id> --log-failed
    ```