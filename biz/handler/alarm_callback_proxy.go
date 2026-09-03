package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"code.byted.org/gopkg/logs"
	"code.byted.org/middleware/hertz/pkg/app"
	"code.byted.org/oec/oncall_opinion_analyse/biz/util/common"
)

type AlarmCallbackReq struct {
	AlarmData AlarmData `json:"alarm_data"`
}

type AlarmData struct {
	RuleUID          string           `json:"rule_uid"`           // 报警规则uid，即 unique id 全球唯一，没有冲突的
	CheckVregion     string           `json:"check_vregion"`      // 报警监控区域
	RuleName         string           `json:"rule_name"`          // 规则名称
	Tags             []KeyValue       `json:"tags"`               // 原始报警tags
	Vars             []KeyValue       `json:"vars"`               // 原始报警vars
	AlertTime        time.Time        `json:"alert_time"`         // 报警发生时间
	AlarmForeignID   AlarmForeignID   `json:"alarm_foreign_id"`   // 报警关联ID
	UserActionResult UserActionResult `json:"user_action_result"` // argos 报警用户操作数据
}

type KeyValue struct {
	Key string `json:"key"`
	Val string `json:"val"`
}

type AlarmForeignID struct {
	SendItemID string `json:"send_item_id"` // 报警发送id
}

type UserActionResult struct {
	Acked          bool   `json:"acked"`            // 表示此报警是否被 ack
	ActionTypeFrom string `json:"action_type_from"` // 此次回调是因为何种用户操作而被触发，e.g. ack/silence/reset_silence/mark/create_group/create_ticket. 若此次回调不是由用户触发，而是由发送报警触发，则为 ""
}

type Response struct {
	BaseResponse
	Data  interface{} `json:"data"`
	Total int64       `json:"total"`
}

type BaseResponse struct {
	ErrCode   int    `json:"err_code"`
	ErrMsg    string `json:"err_msg"`
	Timestamp int64  `json:"timestamp"`
}

type Page struct {
	Page     int   `json:"page" form:"page"`
	PageSize int   `json:"page_size" form:"page_size"`
	Total    int64 `json:"total" form:"total"`
}

func HandleAlarmCallback(ctx context.Context, c *app.RequestContext) {
	var req AlarmCallbackReq
	var err error
	if err = c.Bind(&req); err != nil {
		logs.Error("bind parameter err: %v", err)
		c.JSON(http.StatusOK, "bind parameter err")
		return
	}

	logs.CtxInfo(ctx, "alarm callback called, req : %v", req)
	resp := &Response{
		BaseResponse: BaseResponse{},
		Data:         nil,
		Total:        0,
	}

	var httpCode int = 0
	defer func() {
		// 超时直接返回
		if httpCode == http.StatusGatewayTimeout {
			c.JSON(http.StatusGatewayTimeout, "StatusGatewayTimeout")
			return
		}
		// 跨区域调用失败
		if httpCode == http.StatusInternalServerError {
			c.JSON(http.StatusInternalServerError, "StatusInternalServerError")
			return
		}

		if err != nil {
			c.JSON(http.StatusOK, err.Error())
			return
		}
		c.JSON(http.StatusOK, resp)
	}()

	// header
	header := make(map[string]string)
	c.Request.Header.VisitAll(func(key, value []byte) {
		if string(key) == "X-Tt-Logid" {
			header[string(key)] = string(value)
		}
	})

	marshal, _ := json.Marshal(req)
	httpCode, err = common.CrossIDCCallV2(ctx, "sg1", "/api/osgw/wares_alarm/alarm_detail/callback", "POST", marshal, header, &resp)
}
