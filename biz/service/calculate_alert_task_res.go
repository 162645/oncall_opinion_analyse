package service

import (
	"code.byted.org/gopkg/context"
	"code.byted.org/gopkg/logs"
	"code.byted.org/oec/oncall_opinion_analyse/biz/dal/model"
	"code.byted.org/oec/oncall_opinion_analyse/biz/dal/query"
	"code.byted.org/oec/oncall_opinion_analyse/biz/model/governance_qa_serv"
	"code.byted.org/oec/oncall_opinion_analyse/biz/util/common"
	"errors"
	"fmt"
	"google.golang.org/protobuf/proto"
	"strconv"
	"time"
)

// GenArgosAlertData 告警打点/打日志策略管理
// todo：规则自动注入，根据租户id
func GenArgosAlertData(ctx context.Context, originalRecord *governance_qa_serv.OncallFlow, task *model.OncallListenAlertTask) {
	// [OnCallAlterTaskRecord]|TenantId|originalLevel|d_level|detections|cluster|source_location
	logs.CtxInfo(ctx, "[OnCallAlterTaskRecord]|%v|%v|%v|%v|%v|%v|%v", originalRecord.GetId(), originalRecord.GetTenantId(), originalRecord.GetLevel(),
		*task.CalculatedAlertLevel, *task.MatchKeywords, *task.ClusterTags, originalRecord.GetSourceLocation())
	if originalRecord.GetLevel() != "" {
		common.EmitCounterWithWorkOrderLevel(ctx, originalRecord)
	}
}

// BuildDIYArgosCard 根据tag内的keyType来判断是哪个类型的告警
func BuildDIYArgosCard(ctx context.Context, req *governance_qa_serv.ArgosTagValsCallBackRequest) *governance_qa_serv.ArgosTagValsCallBackResponse {
	resp := new(governance_qa_serv.ArgosTagValsCallBackResponse)
	resp.Code = proto.Int64(0)
	resp.Data = new(governance_qa_serv.ArgosTagValsDIYData)
	tags := req.GetAlertContext().GetTags()
	alterType := GetAlterType(ctx, tags)
	switch alterType {
	case common.WorkOrderLevelMetric:
		BuildWorkOrderLevelCard(ctx, req, resp)
	default:
		BuildGeneralCard(req, resp)
	}
	resp.Data.Vars = req.GetAlertContext().GetVars()
	if len(req.GetAlertContext().GetDescriptions()) > 0 {
		resp.Data.Descriptions = req.GetAlertContext().Descriptions
	}
	return resp
}

func BuildWorkOrderLevelCard(ctx context.Context, req *governance_qa_serv.ArgosTagValsCallBackRequest,
	resp *governance_qa_serv.ArgosTagValsCallBackResponse) {
	//TenantId := getTenantId(ctx, req.GetAlertContext().GetTags())
	oncallId, err := getValueByKeyInList(ctx, common.OriginalOncallId, req.GetAlertContext().GetTags())
	if err != nil {
		logs.CtxInfo(ctx, "cannot find oncallId so go to BuildGeneralCard")
		BuildGeneralCard(req, resp)
	}
	originalOncallId, err := strconv.ParseInt(oncallId, 10, 64)
	if err != nil {
		logs.CtxInfo(ctx, "oncallId format is wrong so go to BuildGeneralCard")
		BuildGeneralCard(req, resp)
	}
	level, e := getValueByKeyInList(ctx, common.WorkOrderLevelMetric, req.GetAlertContext().GetTags())
	if e != nil {
		logs.CtxError(ctx, "get level error from argos callback :%v", e.Error())
	}
	// 查询告警列表
	//originalOncallId := GetLatestOncallRecordIdByAlterInfo(ctx, TenantId, common.WorkOrderLevelMetric, *req.AlertTimestamp)
	if originalOncallId == 0 {
		logs.CtxInfo(ctx, "cannot find oncallId so go to BuildGeneralCard")
		BuildGeneralCard(req, resp)
		return
	}
	// 查询工单记录
	q := query.Use(query.ReadDB(ctx))
	recordTable := q.OncallOriginRecord.WithContext(ctx)
	record, err := recordTable.Where(q.OncallOriginRecord.OncallOriginID.Eq(originalOncallId)).Take()
	if err != nil {
		logs.CtxInfo(ctx, "cannot find oncall record so go to BuildGeneralCard")
		BuildGeneralCard(req, resp)
		return
	}
	if record != nil {
		var tags []*governance_qa_serv.Kv
		reqTags := req.GetAlertContext().GetTags()
		//if *record.SourceLocation == "source_location" {
		//	record.SourceLocation = proto.String("https://oncall.bytedance.net/admin/review/all?id=" + oncallId + "&picked_detail=" + oncallId)
		//}
		for i := 0; i < len(reqTags); i++ {
			describe, ok := common.MetricsDescribeMap[reqTags[i].GetKey()]
			if ok {
				reqTags[i].Key = &describe
				tags = append(tags, reqTags[i])
			}
		}
		tenantName := &governance_qa_serv.Kv{
			Key:   proto.String(common.MetricsDescribeMap[common.TenantName]),
			Value: record.TenantName,
		}
		name := &governance_qa_serv.Kv{
			Key:   proto.String(common.MetricsDescribeMap[common.Name]),
			Value: proto.String("\n" + *record.Name),
		}
		oncallUrl := &governance_qa_serv.Kv{
			Key: proto.String(common.MetricsDescribeMap[common.OncallUrl]),
			//Value: record.SourceLocation,
			Value: proto.String("https://oncall.bytedance.net/admin/review/all?id=" + oncallId + "&picked_detail=" + oncallId),
		}
		isSolved := &governance_qa_serv.Kv{
			Key: proto.String("解决状态"),
			//Value: record.SourceLocation,
			Value: proto.String(strconv.FormatBool(*record.IsSolved)),
		}
		createTime := &governance_qa_serv.Kv{
			Key: proto.String("**工单创建时间🕰️**"),
			//Value: record.SourceLocation,
			Value: proto.String(fmt.Sprintf("%v", record.CreateTime)),
		}
		tags = append(tags, tenantName, name, oncallUrl, isSolved, createTime)
		resp.Data.Tags = tags
		resp.Data.Vars = req.GetAlertContext().Vars
		UpdateIsCallbackTrue(ctx, &model.AlertTask{
			OncallOriginID: &originalOncallId,
			AlterType:      proto.String(common.WorkOrderLevelMetric),
			Level:          proto.String(level),
		})
		return
	}
	BuildGeneralCard(req, resp)
	return
}

func buildSolidMarkdown(s string) string {
	return "**" + s + "**"
}

func UpdateIsCallbackTrue(ctx context.Context, at *model.AlertTask) {
	q := query.Use(query.ReadDB(ctx)).AlertTask
	_, err := q.WithContext(ctx).Where(q.OncallOriginID.Eq(*at.OncallOriginID),
		q.AlterType.Eq(*at.AlterType), q.Level.Eq(*at.Level)).UpdateColumn(q.IsCallback, 1)
	if err != nil {
		logs.CtxError(ctx, "update alter task is callback failed:%v", err.Error())
	}
}

func BuildGeneralCard(req *governance_qa_serv.ArgosTagValsCallBackRequest, resp *governance_qa_serv.ArgosTagValsCallBackResponse) {
	resp.Data.Tags = req.GetAlertContext().Tags
	resp.Data.Vars = req.GetAlertContext().Vars
}

func GetAlterType(ctx context.Context, tags []*governance_qa_serv.Kv) string {
	val, err := getValueByKeyInList(ctx, common.MetricType, tags)
	if err != nil {
		return ""
	}
	return val
}

func getTenantId(ctx context.Context, tags []*governance_qa_serv.Kv) int64 {
	val, err := getValueByKeyInList(ctx, common.TenantId, tags)
	if err != nil {
		return 0
	}
	intVar, err := strconv.ParseInt(val, 0, 64)
	if err != nil {
		return 0
	}
	return intVar
}

func getValueByKeyInList(ctx context.Context, key string, tags []*governance_qa_serv.Kv) (string, error) {
	for i := 0; i < len(tags); i++ {
		if tags[i].GetKey() == key {
			return tags[i].GetValue(), nil
		}
	}
	logs.CtxError(ctx, "not found key:[%v] in list", key)
	return "", errors.New("not found key in list")
}

func GetLatestOncallRecordIdByAlterInfo(ctx context.Context, tenantId int64, alterType string, timestamp int64) int64 {
	q := query.Use(query.ReadDB(ctx))
	taskTable := q.AlertTask.WithContext(ctx)
	res, err := taskTable.
		Where(q.AlertTask.TenantID.Eq(tenantId)).
		Where(q.AlertTask.AlterType.Eq(alterType)).
		Where(q.AlertTask.CTime.Between(time.UnixMilli(timestamp-86400000), time.UnixMilli(timestamp))).
		Last()
	if err != nil {
		logs.CtxError(ctx, "Get last 30min alter task failed : %v", err.Error())
		return 0
	}
	if res == nil || res.OncallOriginID == nil {
		logs.CtxError(ctx, "can not found alter task by %s-%s-%s", tenantId, alterType, timestamp)
		return 0
	}
	return *res.OncallOriginID
}

func GetAlertTaskRecordByOriginalOncallId(ctx context.Context, oncallId int64) *model.OncallListenAlertTask {
	q := query.Use(query.ReadDB(ctx))
	taskTable := q.OncallListenAlertTask.WithContext(ctx)
	res, err := taskTable.Where(q.OncallListenAlertTask.OncallOriginID.Eq(oncallId)).Take()
	if err != nil {
		logs.CtxError(ctx, "Get Oncall Listen Alert Task record error: %v", err.Error())
		return nil
	}
	return res
}
