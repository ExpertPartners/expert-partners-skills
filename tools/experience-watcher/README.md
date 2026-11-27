# Experience watcher

Carries approved experience decisions from the HQ Decision Log to the AI Experience Director and to every affected Factory Workstream, Handoff List route HO-HQ-012. Authority is the HQ Decision Log, November 27, 2026, AI Experience Director established in HQ Claude with immediate transmission.

## What runs

watcher.py watch runs every 10 minutes from launchd on Allison's M4 (invisible background work). It exports the Decision Log, finds new entries whose title contains Experience, calls the Factory connection find_owner to pick the affected Workstream orchestrators, sends each one a five-field handoff with post_message, appends the instance to the Director Inbox doc, and copies any receiver pickup replied in a Factory session into the inbox below the matching instance.

watcher.py reconcile runs daily at 2:15 AM America/Chicago. It sends any experience entry from the last 14 days the watcher missed, folds new non-TEST decisions into the Human Experience Standard under Logged since the last Director pass, and writes the unconfirmed handoff list at the top of the Director Inbox for the 7:35 AM health check.

watcher.py baseline marks every current experience entry as handled. Run it once at install.

## Where things live

Deployed copy and launchd working directory, /Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/experience-director. State, ~/Library/Application Support/hq-experience-watcher/state.json. Logs, ~/Library/Logs/experience-watcher.log and experience-reconcile.log (.err beside them). Plists in launchd/ use __HOME__ for the home folder. HX_STANDARD_DOC holds the Standard's Doc ID.

Secrets come from 1Password at run time and are never printed. Google uses the Ember workspace service account key (op://Ember/6d2p2sastgo5yktlde4gfr5z5i/credential) acting as the ember worker mailbox. Factory uses the Factory Connection Hub API token (op://Automation/Factory Connection - Hub API token/credential). The op service account token is read from ~/.ember/op-sa-token-main.

## Docs it touches

Decision Log 1ausL1HV3ns3VMZH86jD8zjWnAKSQ3DaUfFzkiwR1qWc (read only). Director Inbox 1gSUYfy3dEp0Ke1iIfeCtCW4riXIiZsyR0GcJlJaaicc. Human Experience Standard 16pH3N3ECnzALMKUNlxGJ2F4XVW42NoFcF19VZvyn1Tk. Company Test Bench checks both jobs in its weekly maintenance pass.
