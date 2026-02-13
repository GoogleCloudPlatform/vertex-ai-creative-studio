package security

import (
	"net"
	"net/http"
	"strings"
)

// GetClientIP extracts the client's IP address from the request.
// It prioritizes X-Forwarded-For for proxy compatibility.
func GetClientIP(r *http.Request) string {
	// Check X-Forwarded-For header
	forwarded := r.Header.Get("X-Forwarded-For")
	if forwarded != "" {
		// XFF can be comma separated, take the first one
		parts := strings.Split(forwarded, ",")
		return strings.TrimSpace(parts[0])
	}

	// Fallback to RemoteAddr
	ip, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		// If SplitHostPort fails (e.g. no port), return RemoteAddr as is
		return r.RemoteAddr
	}
	return ip
}
