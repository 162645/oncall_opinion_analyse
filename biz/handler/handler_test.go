package handler

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestPing tests the ping handler
func TestPing(t *testing.T) {
	// Basic test to verify handler package compiles
	assert.NotNil(t, Ping)
}
