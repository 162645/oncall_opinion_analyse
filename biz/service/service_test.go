package service

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestBuildSolidMarkdown tests the markdown builder function
func TestBuildSolidMarkdown(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "simple text",
			input:    "hello",
			expected: "**hello**",
		},
		{
			name:     "empty string",
			input:    "",
			expected: "****",
		},
		{
			name:     "text with spaces",
			input:    "hello world",
			expected: "**hello world**",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := buildSolidMarkdown(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestGetAlterType tests the alter type detection
func TestGetAlterType(t *testing.T) {
	// Test with nil/empty tags
	result := GetAlterType(nil, nil)
	assert.Equal(t, "", result)
}
