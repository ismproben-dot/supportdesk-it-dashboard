# SupportDesk

A responsive IT helpdesk portfolio app for **Ismail Bentayeb**, connecting practical IT support workflows with application development and Business Intelligence.

## Features

- Create tickets with requester, priority and status.
- Update status, search across tickets and combine search with status filters.
- See live counts of unresolved, resolved and critical tickets.
- Add equipment with unique asset tags and view its assigned department/state.
- Export all tickets to CSV, with spreadsheet formula protection.
- Follow four expandable troubleshooting checklists.
- Persist tickets and equipment in browser localStorage.
- Keyboard-accessible native dialogs and responsive layouts.

## Run

Open `index.html` directly in a modern browser, or serve the folder:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000`. No packages, API keys or build step are required. Data is local to this browser and origin; moving from a file URL to a server starts a separate dataset.

## Technology and structure

| File | Responsibility |
| --- | --- |
| `index.html` | Semantic views, forms and troubleshooting content |
| `styles.css` | Responsive layout, components and focus states |
| `app.js` | State, validation, rendering, filters, CSV and persistence |

Built with HTML, CSS and vanilla JavaScript. No third-party runtime dependencies.

## Scope

This is a **single-user frontend portfolio prototype**, not a production helpdesk. All initial records and infrastructure health indicators are fictional demo data. Infrastructure values are static examples, not live monitoring. There is no backend, authentication, multi-user synchronization or real municipal data. Do not enter confidential information. Browser storage can be cleared; CSV export covers tickets only. Assets can be added and viewed; editing/deleting assets is a future improvement.

## GitHub Pages

After uploading these files to a repository, open **Settings → Pages → Deploy from a branch**, choose the default branch and **/(root)**, then save.

## Suggested next milestones

- Add a PHP or Python backend and a relational database.
- Add authenticated roles, audit history and server-side validation.
- Add ticket assignment, resolution notes and SLA reporting.
- Add full asset editing and backups.

## Portfolio description

“IT helpdesk frontend prototype with ticket workflows, equipment inventory, KPI reporting, search/filtering and CSV export, built with HTML, CSS and JavaScript.”

Created with AI assistance as a portfolio learning project. Review and understand the code before presenting or extending it.

## Verification

Run `node tests/smoke.cjs` (Node.js 18+). Dependency-free checks cover ticket creation, text escaping, combined filtering, status persistence, asset creation, duplicate tags, CSV formula protection and malformed stored data. These use a minimal DOM harness and do not replace browser or accessibility testing. Automated visual browser verification was unavailable in the build environment.
