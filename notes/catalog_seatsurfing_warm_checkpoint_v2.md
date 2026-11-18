# SeatSurfing warm-state capture correction

Review found that stopping the application and browser before taking the initial checkpoint would erase the warm process/editor state required for the registered warm native reference. The prepared v1 coordinator therefore cannot alone support that comparison. No application job or scientific outcome used it.

Added v2 components requiring running-but-paused application/browser containers for capture, preserving their memory for a later warm resume. Restore still requires stopped containers and no other database sessions. Capture permits only idle, transaction-free loopback connections for the original database user and checks stopped/paused states live through Docker metadata. All source/build/image, fixture label, isolation and full fingerprint conditions remain enforced. The actual pause/settle/resume worker is still to be implemented and qualified.

Added an explicit expected capture-manifest hash and exact member-inventory validation before restoration. Eleven mocked database-guard checks and nine mocked bundle checks passed locally. No Docker, browser, database or network operation ran in those tests. The corrected CI state from the preceding commit remains a separate verification item; no synthetic test is counted as a scientific case. Cohort application jobs remain six and scientific cases zero.
