# README repetition 1: failed starting control

Run 44033922143, frozen head af384bda7491cfc02f40ffa9d2e56825081d2ed3, repetition 1 completed with workflow-job conclusion success. Its archived batch.json instead records control_failed. Only entry 00 (control_start, native_native) ran; scientific_cases_executed is zero. Repetition 2 was still live when this note was written, so this is not the final run reconstruction.

The ordinary control created the intended private project and submitted the native Web IDE commit. The recorded commit response was HTTP 201. Project and file/tree reads showed a nonempty repository and the expected README. The immediate branches read returned HTTP 200 with an empty list, failing the assertion requiring main. The read-only failure snapshot subsequently returned main as the default branch, the exact README, and one root commit bound to that file. These sequential observations are consistent with a transient readback issue; the archived evidence does not prove its internal cause. No API-created scientific state was involved, so this is not evidence of the proposed API/native defect.

The batch runner returns normally after recording a failed control, which explains why the job can be green while the scientific batch is disqualified. Retain the frozen control failure, absent ending control and unreached schedule. Do not substitute the later snapshot for a passed control, alter the assertions, add waits, or rerun to replace the result. Repetition 2 remains the already registered second batch, not a repair or response to this finding.

Raw artifact: results/benchmark-gitlab-readme-inputs-v1-ci-44033922143/gitlab-readme-inputs-r1-44033922143. Final scoring waits for terminal metadata for both jobs.

Separately, the archive-scoped compute snapshot reconstructs 16 earlier terminal benchmark runs, 29 distinct jobs and 14,775 job-seconds (246.25 minutes), including 4,906 seconds in failed jobs. It excludes this live scientific run, other research stages, unit workflows and any unlisted runs. It is not a whole-project total or an invoice. Source metadata hashes and unique job IDs are retained in manifests/benchmark-archived-compute-v1.json.
