# Pinned GitLab image inspection v1

This extends the candidate selection with one infrastructure inspection, not scientific execution. The purpose is to identify the bundled GitLab version and obtain matching source API documentation before independent input construction.

Use only am1n3e/webarena-verified-gitlab@sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0 on the existing standard public Ubuntu runner. First require 70,000,000,000 bytes free on the runner root filesystem. No cleanup or replacement image is allowed. If capacity is insufficient, preserve the measurement and stop before pulling.

One job, maximum 20 minutes; image pull capped at 15 minutes. No automatic retry. Record actual job duration regardless of success. No paid infrastructure or model calls. This does not consume the closed converter study's budget or authorize a new scientific study; it adds at most 20 infrastructure-job minutes within the existing $100 cash ceiling.

Pull the digest-pinned image and create a stopped container with network disabled and /bin/true as entrypoint. Never start the container or GitLab services. Copy only version identifiers and the named API documentation files: projects, issues, merge_requests, members, repository_files, commits and the API index. Preserve missing-file failures. Version identifiers are VERSION, REVISION and GITLAB_REVISION under the bundled Rails root, plus the package version manifest. Do not inspect frontend validators, task evaluators, application databases or business records. Remove only this disposable stopped container on exit.

Save host capacity, pull logs, image identity, extraction outcomes, extracted files and file hashes. If documentation is not bundled, a resolved version/revision may support later retrieval from the corresponding upstream source; do not silently use current documentation. If version identity is unavailable, qualification remains unresolved. No workflow input or output is observed here, and no claim of scientific validity follows from a successful extraction.
