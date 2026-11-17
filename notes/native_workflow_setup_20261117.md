# Native browser setup evidence

The two fixed public Cypress files were retrieved and read. The login test defaults to user/user if its environment does not override them, navigates through the root page and login menu, and asserts a 200 response from POST /api/authenticate. The selector names are preserved in the manifest. These are public fixture defaults for an isolated development instance, not credentials for any hosted service.

The API-backed Cypress login helper inserts a token into sessionStorage using environment-configured keys. That shortcut is not a native UI login and should not silently replace the UI control. The native login test supplies the direct UI sequence we can reproduce. Neither file establishes admin credentials or a complete admin create/edit sequence; those remain setup gaps. No browser or login request was executed during inspection.

The next bounded runtime qualification can use this ordinary user login to establish whether the original built UI is functional, before any admin workflow or altered payloads. The result must include browser console/network failures and successful account readback rather than treating a visible page as proof of login. New workflow collection still needs a separately frozen schedule. No held-out application source was read.
