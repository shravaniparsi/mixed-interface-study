# Jitsi settings and external transport mapping

Wave 41 acquired all six scheduled blobs once at freeze
7f92d38b86e18855c3c610a52fa8206cf23ab389. No application, conference or scientific
input ran. The fixed revision remains 2413432d732c184184f986da1f7487fa7689b104.

modules/transport/index.js constructs Transport with PostMessageTransportBackend
from the declared @jitsi/js-utils dependency. It also exposes backend replacement
through the global namespace. This establishes the default source configuration;
it does not establish that every possible embedding uses the same backend.
The previously retained modules/API/API.js command surface is consequently not
by itself evidence of a server JSON CRUD API.

The base settings reducer registers its state with PersistenceRegistry. That
registry serializes filtered subtrees with JSON.stringify and calls
jitsiLocalStorage.setItem; reads call getItem and safeJsonParse. Display name
changes dispatch updateSettings, which creates a local Redux action. The profile
submit path separately invokes APP.conference.changeLocalEmail for email changes.
The relevant conference implementation and settings middleware have not yet
been acquired, so this review does not claim that all profile effects are local.

The original reducer includes an incidental comment explaining a historical
null-to-empty-string handling workaround during migration from legacy settings.
This is retained source exposure, not a newly discovered incompatibility or a
reason to alter inputs. No profile workflow or scientific input is selected.

The previously mapped poll path remains conference-message based. Together,
these findings leave persistent server record creation/update and full native
continuation unestablished. Jitsi remains pending; the review does not convert
failure to map a candidate into an exhaustive project exclusion. Next resolve
the explicit conference email and web/shared settings middleware dependencies.
