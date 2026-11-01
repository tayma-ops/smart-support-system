# Real application screenshots

Captured and visually reviewed on **1 November 2026** from the actual localhost Django application using Chromium 153.0.8010.12. PostgreSQL, Redis, Celery and the local model were started using the existing native development setup. All six PNGs are embedded in the root README.

Only existing fictional demo accounts and `[Demo]` tickets were used. No credentials, personal emails, tokens, filesystem paths or real customer data appear in the images. External browser requests were blocked; application responses were not mocked and no UI content was injected. No generated images were used.

## Published captures

| Order / filename | Existing page and role | Viewport | Captured content |
| --- | --- | --- | --- |
| 1. `01-dashboard.png` | Employee, `/dashboard/` | 1440 × 1000 | English overview with scoped metrics, activity and the priority queue. |
| 2. `02-ticket-list.png` | Employee, `/tickets/` | 1440 × 1000 | Existing demo tickets with search, filters, status and ownership. |
| 3. `03-ticket-details.png` | Employee, `/tickets/3/` | 1440 × 1060 | Public conversation, reply composer, internal-note option and assignment details. |
| 4. `04-ai-human-review.png` | Employee, the same ticket | 1440 × 1060 | A genuine 1126 × 745 browser capture region showing the AI suggestion and populated composer. No reply was sent. |
| 5. `05-arabic-rtl.png` | Employee, `/dashboard/` after switching to Arabic | 1440 × 1000 | Translated labels, RTL navigation and the same scoped metrics. |
| 6. `06-mobile-ticket.png` | Ticket owner, `/tickets/3/` | 390 × 844 | Full-page capture, 390 × 1832, with readable conversation and customer controls. |

The existing ticket `[Demo] Production dashboard is unavailable` has genuine saved Qwen3-0.6B-Q4_K_M analysis from the earlier local inference verification. The real **Use draft in reply** button copied that suggestion into the composer. The screenshot demonstrates the review step; it does not claim a new model run or a sent reply. Existing tickets, replies, AI output, assignments and password hashes were preserved. No internal note was invented for capture.

## Browser review completed

- All six final images were opened and inspected for readable content, clipping, layout and sensitive information.
- English and Arabic dashboards had no document-level horizontal overflow at 1440, 1024, 768, 760, 390 and 320 pixels. RTL mobile ticket-list overflow was also checked. Wide tables retain their own horizontal scrolling.
- A tablet overflow issue caused by an absolutely positioned screen-reader label escaping its table scroller was fixed with `position: relative` on `.table-scroll`. This is the only application source change and affects layout containment only.
- Mobile navigation opened, closed with Escape and restored focus to its toggle. The customer view contained no staff AI panel or internal-note control; an unrelated customer received 404 for the same ticket.
- Loading the AI draft left the API record unchanged. No reply was submitted. Browser checks reported no JavaScript exceptions or server errors.

This is a focused visual and interaction review of the displayed workflows, not an exhaustive accessibility, cross-browser or production certification. The full backend suite was not repeated for screenshots and this CSS-only adjustment. Private capture scripts, session state and detailed evidence remain under ignored `.local/`.

## Optional future captures

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
5. Save the selected PNGs under the exact filenames above. Keep the README embeds and capture notes consistent with any new captures.

The six published captures and the focused checks above supersede the earlier pending-screenshot notes. The checklist also includes broader checks, such as 200% zoom and exhaustive keyboard traversal, which were not all performed in this capture session.
