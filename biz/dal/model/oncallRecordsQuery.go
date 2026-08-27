package model

import "gorm.io/gen"

type Method interface {

	//select * from @@table
	// {{where}}
	//  	is_solved = 0 and
	//	level = @level and
	//	oncall_response_time is true and
	//	TIMESTAMPDIFF(MINUTE,create_time,oncall_response_time) > @allowedMinuteTime and
	//  create_time >= @startTime
	//{{end}}
	FindNotSolveAndResponseTimeNotAllowed(level string, allowedMinuteTime int64, startTime string) ([]gen.T, error)

	//select * from @@table
	// {{where}}
	//  	is_solved = 0 and
	//	level = @level and
	//	oncall_response_time is NULL and
	//	TIMESTAMPDIFF(MINUTE,create_time,Now()) > @allowedMinuteTime and
	//  create_time >= @startTime
	//{{end}}
	FindNotSolveAndNoResponseTimeNotAllowed(level string, allowedMinuteTime int64, startTime string) ([]gen.T, error)
}
