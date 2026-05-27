package source

import "strconv"

// parseFloat parses a decimal string into a float64. It exists so the sources
// share one lenient parser and stay easy to test.
func parseFloat(s string) (float64, error) {
	return strconv.ParseFloat(s, 64)
}
