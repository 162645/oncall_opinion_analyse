package common

type Level int32

const (
	P0 Level = iota
	P1
	P2
	P3
	P4
)

var (
	levelMap = map[string]Level{
		"P0": P0,
		"P1": P1,
		"P2": P2,
		"P3": P3,
		"P4": P4,
	}
)

func (s Level) String() string {
	switch s {
	case P0:
		return "P0"
	case P1:
		return "P1"
	case P2:
		return "P2"
	case P3:
		return "P3"
	case P4:
		return "P4"
	}
	return "unknown"
}
