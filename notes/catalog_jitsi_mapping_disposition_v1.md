# Jitsi bounded candidate disposition

Wave 49 acquired all eight scheduled blobs once at published freeze
168767da0ee9ac1e15acd7002f7b913f94f131d5. Jitsi exposure totals 30 source slots
and 344,335 decoded bytes. No application or scientific case ran.

The original AddBreakoutRoomButton dispatches createBreakoutRoom without a
custom name. The action chooses a default subject when none is supplied and
calls the current conference breakout-room service. RenameButton opens
BreakoutRoomNamePrompt, which contains one text Input for roomName. Submission
trims the name and calls renameBreakoutRoom; the action rejects empty trimmed
names and delegates to the current conference service. This mapped editor lacks
the required second independently editable scalar text property. No downstream
server storage claim is necessary for that candidate-level exclusion.

The middleware listens for conference breakout-room updates and moves, dispatches
room state, enriches participant context and updates chat display names. The
reducer holds room state and supports reset. Those client paths do not establish
server persistence or its absence. Its compatibility comment about older server
join restrictions is incidental source exposure, not a new defect finding.

ProfileTab confirms displayName and conditionally visible email text inputs,
with readOnlyName optionally disabling the name. The previously retained save,
settings persistence and conference methods establish local preference and
conference effects, but no eligible server JSON record creation/update pair.
SubjectText displays a conference name; it is not an editor. This does not prove
that other subject-edit controls do not exist. The previously mapped poll
candidate remains conference-message based and unqualified for this study.

Close the bounded candidate mapping as unavailable, retaining the candidates
in UTF-8 control-path order. This is not an exhaustive project exclusion:
whiteboard, integrations and external transport replacements are not fully
reviewed. Unused source capacity is not represented as exhausted. No guessed
REST CRUD implementation, external account or inter-user-message experiment
is substituted to create an eligible workflow. Keep the project in the twelve
selected projects, with zero runtime attempts and scientific cases.
