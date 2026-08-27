package common

import (
	"code.byted.org/gopkg/logs"
	"code.byted.org/middleware/hertz/pkg/network/standard"
	"code.byted.org/oec/oncall_opinion_analyse/biz/dal/model"
	"code.byted.org/oec/oncall_opinion_analyse/biz/model/governance_qa_serv"
	"context"
	"fmt"
	"github.com/cloudwego/hertz/pkg/app/client"
	"net/url"
	"reflect"
	"runtime/debug"
	"strings"
	"time"
)

var HttpCli *client.Client
var ParseTemplate = "2006-01-02 15:04:05"

func SliceStringTime(t *string) string {
	if t == nil {
		return ""
	}
	res := *t
	if len(res) <= 20 {
		return strings.ReplaceAll(res, "T", " ")
	}
	return strings.ReplaceAll(res[0:19], "T", " ")

}

func HttpClientInit() {
	var err error
	HttpCli, err = client.NewClient(client.WithDialer(standard.NewDialer()))
	if err != nil {
		logs.Error("initial http client failed ......")
	}
}

func init() {
	HttpClientInit()
}

func StructCopy(from, to interface{}) {

	fromValue := reflect.ValueOf(from)

	toValue := reflect.ValueOf(to)

	// 必须是指针类型
	if fromValue.Kind() != reflect.Ptr || toValue.Kind() != reflect.Ptr {
		return
	}

	if fromValue.IsNil() || toValue.IsNil() {
		return
	}

	// 获取到来源数据
	fromElem := fromValue.Elem()

	// 需要的数据
	toElem := toValue.Elem()

	for i := 0; i < toElem.NumField(); i++ {

		toField := toElem.Type().Field(i)

		// 看看来源的结构体中是否有这个属性
		fromFieldName, ok := fromElem.Type().FieldByName(toField.Name)

		// 存在相同的属性名称并且类型一致
		// todo 可以根据需要判断是否是空值
		if ok {
			if fromFieldName.Type == toField.Type {
				toElem.Field(i).Set(fromElem.FieldByName(toField.Name))
			} else {
				switch toField.Type.Kind() {
				case reflect.Bool:
				case reflect.Int:
				case reflect.Int8:
				case reflect.Int16:
				case reflect.Int64:
				case reflect.String:
					toElem.Field(i).Set(fromElem.FieldByName(toField.Name).Convert(toField.Type))
				}
			}
		}
	}
}

// CopyOriginalOncallRecord db record info copy from request content
func CopyOriginalOncallRecord(originalRecord *governance_qa_serv.OncallFlow) (*model.OncallOriginRecord, error) {
	//data, err := json.Marshal(originalRecord)
	//if err != nil {
	//	return nil, err
	//}
	d := &model.OncallOriginRecord{}
	//err = json.Unmarshal(data, d)
	StructCopy(originalRecord, d)
	var temp int64
	d.OncallOriginId = originalRecord.Id
	d.ID = temp
	TimeParseFromString(d, originalRecord)
	//if err != nil {
	//	return nil, err
	//}
	return d, nil
}

// TimeParseFromString 时间格式额外转换逻辑
func TimeParseFromString(d *model.OncallOriginRecord, originalRecord *governance_qa_serv.OncallFlow) {

	createTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.CreateTime), time.Local)
	if err == nil {
		d.CreateTime = &createTime
	}
	updateTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.UpdateTime), time.Local)
	if err == nil {
		d.UpdateTime = &updateTime
	}
	solveTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.SolveTime), time.Local)
	if err == nil {
		d.SolveTime = &solveTime
	}

	fdbTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.FeedbackTime), time.Local)
	if err == nil {
		d.FeedbackTime = &fdbTime
	}
	osTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.OncallStartTime), time.Local)
	if err == nil {
		d.OncallStartTime = &osTime
	}
	oeTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.OncallEndTime), time.Local)
	if err == nil {
		d.OncallEndTime = &oeTime
	}
	orTime, err := time.ParseInLocation(ParseTemplate, SliceStringTime(originalRecord.OncallResponseTime), time.Local)
	if err == nil {
		d.OncallResponseTime = &orTime
	}
}

func Go(x func()) {
	go func() {
		defer func() {
			if err := recover(); err != nil {
				logs.CtxError(context.Background(), fmt.Sprintf("panic %s\n", err))
				logs.CtxError(context.Background(), fmt.Sprint(string(debug.Stack())))
			}
		}()
		x()
	}()
}

func IsValidUrl(s string) bool {
	url, err := url.ParseRequestURI(s)
	if err != nil || url == nil {
		return false
	}
	return true
}
