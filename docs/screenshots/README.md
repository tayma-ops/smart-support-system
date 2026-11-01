# Screenshot capture plan

This directory reserves filenames for real captures of existing application pages. No image files or UI mockups have been generated. Capture the six images below in order; use all six in the README, or use **1, 3, 4 and 5** for a compact four-image selection.

## Recommended README selection, in order

| Order / filename | Existing page and role | Viewport | Capture instructions |
| --- | --- | --- | --- |
| 1. `01-dashboard.png` | Employee, `/dashboard/` | 1440 × 1000 | English overview with scoped metrics, activity and the priority queue. This is the first portfolio image. |
| 2. `02-ticket-list.png` | Employee, `/tickets/` | 1440 × 1000 | Show several labeled demo tickets and the search/filter controls. Use a broad result set so the page communicates the workflow. |
| 3. `03-ticket-details.png` | Employee, a visible ticket at `/tickets/<id>/` | 1440 × 1000 | Show public conversation, a staff-only internal note, status and assignment. Use an actual ID from the list. |
| 4. `04-ai-human-review.png` | Employee, the same ticket with completed real AI analysis | 1440 × 1000 | Show the generated suggestion and human-review controls. Click **Use draft in reply**, edit the composer if needed and capture before clicking **Send reply**. The suggestion and review are parts of the ticket page, not separate pages. |
| 5. `05-arabic-rtl.png` | Employee, `/dashboard/` after switching to Arabic | 1440 × 1000 | Show translated labels, RTL navigation and real scoped metrics. |
| 6. `06-mobile-ticket.png` | Ticket owner, `/tickets/<id>/` | 390 × 844 | Show readable ticket content and mobile controls. Check the menu open/close behavior first; use the clearest final view. |

The existing demo ticket with subject `[Demo] Production dashboard is unavailable` has genuinely generated local-model analysis in this checkout. Use a visible, genuinely analyzed demo ticket; do not type invented AI output into the database. An internal note must be real synthetic content added through the staff workflow. Avoid changing existing demo data solely for a screenshot if a suitable ticket is already present.

## Optional alternatives that also exist

| Filename | Existing page | When to use it |
| --- | --- | --- |
| `07-home.png` | `/` as a signed-out visitor | Use instead of image 2 if the landing page makes a clearer introduction. |
| `08-login.png` | `/accounts/login/` as a signed-out visitor | Supporting documentation; usually less useful than workflow images in the main six. |
| `09-customer-ticket.png` | Owner viewing the same ticket | Demonstrate that private notes and AI drafts are absent. |
| `10-analytics.png` | Employee, `/analytics/` | Alternative evidence of scoped reporting. |
| `11-api-docs.png` | `/api/docs/` | Show an expanded operation without any live token visible. |
| `12-tablet-rtl.png` | Employee, Arabic `/tickets/` | 768 × 1024 tablet layout and horizontal table scrolling. |

## Capture checklist

1. Start the real development application and sign in with private generated demo credentials. Never display those credentials in an image.
2. Use synthetic `[Demo]` records and 100% zoom. Hide password-manager overlays, developer tools, tokens, reset URLs, personal emails and filesystem paths.
3. Check the same ticket as staff, its owner and an unrelated customer. The owner must not see staff-only material; the unrelated customer must not gain access.
4. Check focus visibility, Tab/Shift+Tab, Escape, focus restoration, validation messages, long Arabic text, 200% zoom and the 760px breakpoint. A screenshot alone does not prove accessibility or responsiveness.
5. Save the selected PNGs under the exact filenames above. Replace the root README's reserved slots with image embeds only after the actual files exist.

Browser visual QA is still pending. The application has HTML/HTTP and localization tests; those tests are not a claim that screenshots or mobile browser testing have been completed.
