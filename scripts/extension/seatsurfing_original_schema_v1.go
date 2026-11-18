// Original request decoding/tag validation probe. Build only inside the frozen
// SeatSurfing source module under the separately registered runtime recipe.
// This imports the original router; it must not run on the local workstation.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http/httptest"
	"os"

	"github.com/seatsurfing/seatsurfing/server/router"
)

func main() {
	const maxBytes = 65536
	raw, err := io.ReadAll(io.LimitReader(os.Stdin, maxBytes+1))
	if err != nil || len(raw) > maxBytes {
		fmt.Fprintln(os.Stderr, "schema probe input unavailable or exceeds bound")
		os.Exit(2)
	}
	request := httptest.NewRequest("POST", "http://fixture.invalid/location/", bytes.NewReader(raw))
	request.Header.Set("Content-Type", "application/json")
	var model router.CreateLocationRequest
	validationErr := router.UnmarshalValidateBody(request, &model)
	result := map[string]interface{}{
		"baseline": "original_request_decode_and_tag_validation",
		"schema_type": "router.CreateLocationRequest",
		"accepted": validationErr == nil,
		"decoded_model": model,
		"handler_invoked_by_probe": false,
	}
	if validationErr != nil {
		result["error"] = validationErr.Error()
	}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		os.Exit(2)
	}
}
