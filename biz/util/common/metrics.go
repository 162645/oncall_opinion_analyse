package common

import (
	"code.byted.org/gopkg/logs"
	"code.byted.org/gopkg/metrics"
	"code.byted.org/oec/lazyman/metricsutil"
	"code.byted.org/oec/oncall_opinion_analyse/biz/config/bussinessmodel"
	"code.byted.org/oec/oncall_opinion_analyse/biz/dal/model"
	"code.byted.org/oec/oncall_opinion_analyse/biz/dal/query"
	"code.byted.org/oec/oncall_opinion_analyse/biz/model/governance_qa_serv"
	"context"
	"gorm.io/gorm"
	"strconv"
)

const (
	WorkOrderLevelMetric string = "workOrderLevel"
	MetricType           string = "metricType"
	TenantId             string = "tenantId"
	TenantName           string = "tenantName"
	OncallUrl            string = "oncallUrl"
	OncallUrls           string = "oncallUrls"
	Name                 string = "name"
	LevelAlarm           string = "levelAlarm"
	OriginalOncallId     string = "originalOncallId"
	OriginalOncallIds    string = "originalOncallIds"
	OriginalOncallInfos  string = "originalOncallInfos"
	RootField            string = "rootField"
	ShardId              string = "shardId"
	TotalShard           int64  = 16
)

var MetricsDescribeMap = map[string]string{
	WorkOrderLevelMetric: "**原始Oncall工单Level❗**",
	TenantId:             "租户id",
	TenantName:           "租户名称ℹ️",
	OncallUrl:            "**oncall工单原始地址🔗**",
	OncallUrls:           "oncall工单原始地址🔗",
	Name:                 "**oncall工单描述💻**",
	OriginalOncallId:     "oncall工单ID",
	OriginalOncallIds:    "oncall工单IDs",
	OriginalOncallInfos:  "oncall工单信息",
}

func EmitCounterWithWorkOrderLevel(ctx context.Context, originalRecord *governance_qa_serv.OncallFlow) {
	level := originalRecord.GetLevel()
	tenantId := strconv.FormatInt(originalRecord.GetTenantId(), 10)
	oncallId := strconv.FormatInt(originalRecord.GetId(), 10)
	shard := strconv.FormatInt(originalRecord.GetId()%TotalShard, 10)
	rootField := bussinessmodel.GetRootFieldById(originalRecord.GetTenantId())
	if needNewAlertMetrics(ctx, WorkOrderLevelMetric, originalRecord.GetId(), level, 1) {
		task := saveAlertMetricsTask(ctx, originalRecord, WorkOrderLevelMetric, level, rootField)
		if IsExistOrderLevelAlertTaskWithCrossOncallFlowIdAndRootFieldAndHasCallback(ctx, task) {
			logs.CtxInfo(ctx, "no need to take work order level metric again:[%v] %v", task.OncallOriginID, task)
			return
		}
		metricsutil.StoreValueWithTags(
			LevelAlarm, 1,
			metrics.T{Name: MetricType, Value: WorkOrderLevelMetric},
			metrics.T{Name: OriginalOncallId, Value: oncallId},
			metrics.T{Name: TenantId, Value: tenantId},
			metrics.T{Name: ShardId, Value: shard},
			metrics.T{Name: RootField, Value: rootField},
			metrics.T{Name: WorkOrderLevelMetric, Value: level})
	}
}

// IsExistOrderLevelAlertTaskWithCrossOncallFlowIdAndRootField 如果存在相同业务域的CrossOncallFlowId就不打点
func IsExistOrderLevelAlertTaskWithCrossOncallFlowIdAndRootFieldAndHasCallback(ctx context.Context, alertTask *model.AlertTask) bool {
	q := query.Use(query.ReadDB(ctx)).AlertTask
	num, _ := q.WithContext(ctx).Where(q.CrossOncallFlowID.Eq(*alertTask.CrossOncallFlowID),
		q.RootField.Eq(*alertTask.RootField), q.Level.Eq(*alertTask.Level), q.IsCallback.Eq(1)).Count()
	if num > 0 {
		return true
	}
	return false
}

func saveAlertMetricsTask(ctx context.Context, originalRecord *governance_qa_serv.OncallFlow, metricsType string, level string, rootField string) *model.AlertTask {
	var task *model.AlertTask
	task = new(model.AlertTask)
	task.OncallOriginID = originalRecord.Id
	task.CrossOncallFlowID = originalRecord.CrossOncallFlowId
	task.RootField = &rootField
	task.TenantID = originalRecord.GetTenantId()
	task.AlterType = &metricsType
	task.Level = &level
	q := query.Use(query.WriteDB(ctx))
	n, ee := q.AlertTask.WithContext(ctx).Where(q.AlertTask.OncallOriginID.Eq(*task.OncallOriginID),
		q.AlertTask.AlterType.Eq(metricsType), q.AlertTask.Level.Eq(level)).Count()
	if ee != nil {
		if ee.Error() == gorm.ErrRecordNotFound.Error() {
			err := q.AlertTask.WithContext(ctx).Save(task)
			if err != nil {
				logs.CtxError(ctx, "save alter task failed: %v", err.Error())
			}
			return task
		} else {
			logs.CtxError(ctx, "count alert task failed :%v", ee.Error())
			return task
		}
	}
	if n == 0 {
		err := q.AlertTask.WithContext(ctx).Save(task)
		if err != nil {
			logs.CtxError(ctx, "save alter task failed: %v", err.Error())
		}
		return task
	}
	logs.CtxInfo(ctx, "alert task exists and no save new info")
	return task
}

func needNewAlertMetrics(ctx context.Context, alertType string, oncallOriginID int64, level string, isCallback int32) bool {
	q := query.Use(query.ReadDB(ctx))
	var num int64
	var err error
	if isCallback == 99 {
		num, err = q.AlertTask.WithContext(ctx).
			Where(q.AlertTask.OncallOriginID.Eq(oncallOriginID)).
			Where(q.AlertTask.AlterType.Eq(alertType)).
			Where(q.AlertTask.Level.Eq(level)).
			Count()
	} else {
		num, err = q.AlertTask.WithContext(ctx).
			Where(q.AlertTask.OncallOriginID.Eq(oncallOriginID)).
			Where(q.AlertTask.AlterType.Eq(alertType)).
			Where(q.AlertTask.Level.Eq(level)).
			Where(q.AlertTask.IsCallback.Eq(isCallback)).
			Count()
	}

	if err != nil {
		return true
	}
	if num > 0 {
		return false
	}
	return true
}
