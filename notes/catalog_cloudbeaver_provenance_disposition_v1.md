# CloudBeaver executable provenance unavailable

Wave 47 acquired the five scheduled build-reference files at freeze
b6ca67de7b1d176d33a5ee378a12416f6e5d5fb0. The aggregate explicitly includes
sibling dbeaver-common, datadam-api/apis and dbeaver projects. The previously
retained build script clones those repositories without revision pins. The
product inherits a snapshot parent and properties from that build; the Docker
script obtains its base-Java version from the sibling dbeaver-common Maven root.
The inspected files do not supply immutable sibling revisions. Pinning only the
CloudBeaver checkout would not resolve those source identities.

A separate metadata-only protocol was frozen at
df6ef7fa998494f5b56a7c787d9356b3beb23da0 for the original image workflow's
ghcr.io/dbeaver/cloudbeaver:devel reference. The first anonymous token request
returned HTTP 403. No manifest, config, revision label or layer was observed.
There was no retry, alternate tag, registry substitution or dependency-HEAD
acquisition. The response does not prove the image is absent, private or built
from a different revision; it establishes that this metadata route supplied
no executable-provenance evidence.

CloudBeaver is recorded as pre-execution qualification unavailable under the
fixed study rules. This is not an application defect, a scientific null, proof
of irreproducibility or a claim that every possible deployment is unsupported.
The earlier team GraphQL binding still rejects missing/null names in source;
that fact is not an executed outcome and did not determine this disposition.

No application job or scientific case was spent. The project remains in the
original twelve-project denominator without replacement. Three mappings remain:
Meme Search, changedetection.io and Jitsi. The study still has eight qualification
jobs and zero scientific cases; these pre-execution limitations are reported
separately from runtime failures and scope exclusions.
