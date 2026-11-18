# Route/form discovery review and first scope dispositions

All 69 scheduled blobs were collected and Git/SHA256 verified. The cumulative total is 127 source slots and 1,376,235 decoded bytes across twelve projects; per-project counts remain below their fixed caps. This is acquisition coverage, not a claim that every collected line was human-reviewed. No application jobs, producer inputs, controlled branches or scientific observations ran.

## Closed scope exclusions

ChartDB's pinned packaged deployment uses Nginx to serve the frontend and configuration JavaScript (wave1 Dockerfile; wave2 default.conf.template and entrypoint.sh). The inspected storage provider initializes a browser Dexie database and performs diagram/table create, get and update operations there (wave2 file48, lines1–145, 260–350, 625–700, 780–846). The native create-diagram code calls that storage abstraction (file49, lines145–190). This is outside the registered local server JSON mutation/readback scope. Optional AI endpoints and the separate cloud product do not turn browser-local record writes into the required server workflow. This disposition concerns the pinned self-hosted package, not a claim about every possible integration.

socks5-proxy-server's full README/Compose and complete 38-entry tree identify SOCKS, Redis, CLI scripts and a Telegram bot. Full review of wave2 files57–60 shows the proxy entrypoint starting simple-socks, and the second entrypoint starting a Telegram Bot with corresponding package dependencies. The documented application does not provide the required original browser record editor. No Telegram connection, proxy lifecycle or substitute UI was attempted. Both excluded projects remain in the twelve-project denominator; there will be no replacements or further runtime qualification for them in this cohort.

## Partial mappings retained

Meme-search: full review of wave2 files1–7 shows the route table, image-core description/tag controls, empty embedding/tag scaffold forms, token creation/revocation, one-name-plus-frequency path forms, and tag-name/color controls. These are not yet an admitted paired JSON workflow. The tag color is a color input despite a string-valued model; earlier candidates and original Rails form transport/serialization need explicit resolution. Image-to-text settings routes also remain unresolved. Do not infer native/API complete-payload equivalence from generic Rails helpers or the README's read-only integration API.

Viseron: full review of files16–18 shows AddUserDialog collecting name, username, password and role, guarded by useUserForm validity, while UserDialog initializes name/username/role from the record and submits id, name, username, role, assigned_cameras and preferences. The inspected edit Save button is disabled only while the update is pending. This source distinction is not an executed outcome or reason to omit the project if no native-only signal is expected. API wrappers, response/persistence, empty-camera behavior and original local initialization still require mapping; frontend name/username editing alone is not control qualification.

Mathesar: full review of NewUserPage and users RPC module (files67 and69) identifies UserDetailsForm and users.add/get/patch_other with username, email, full_name and related user fields. The shared form, frontend RPC serializer, decorators, users utility and persistence are not yet mapped. Admin creation is an early native route candidate, not a frozen scientific workflow yet.

Other acquired route/form files have not yet received a complete mapping review. Their presence is not evidence of a supported comparison. The broad filename-discovery manifest contains false positives and cannot establish absence of earlier workflows. Source dependency and candidate-order review continues for ten remaining projects under unchanged caps, with all unresolved prefixes retained.

The prior CloudBeaver embedded-fix exposure remains in force. No issues, tests, fix commits or release-note files were newly acquired by this wave. The study still has zero independent scientific cases in this cohort.
