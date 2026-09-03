namespace go oec.governance.oncall_opinion_analyse

struct IDVMockRequest {
	// sentry resp
	1:  string actionPackage    (api.query = 'action_package')
	2:  string eventCode        (api.query = 'event_code')
	3:  bool   ignoreExemption  (api.query = 'ignore_exemption')
	4:  string factorList       (api.query = 'factor_list')
	5:  string sceneCode        (api.query = 'scene_code')
	6:  i32    exemptDuration   (api.query = 'exempt_duration')
	7:  string exclude          (api.query = 'exclude')
	8:  string content          (api.query = 'content')
}


struct IDVMockResp{
    1: i32 code
    2: string msg
}

struct EmptyReq{

}

struct EmptyResp{

}

struct DisposeQA5Request {
    // 空请求体，该接口不需要特定参数
}

struct DisposeQA5Response {
    1: i32 code
    2: string msg
    3: optional string notice
}


service MockService{
    IDVMockResp IDVMock(1: IDVMockRequest req) (api.any='/osgw_v2/mock/idv')
    EmptyReq GetOncallArgosDIYCardCallback(1: EmptyReq req) (api.post='/api/v:version/oec/governance/qa/argos/callback')
    EmptyReq GetOncallCallback(1: EmptyReq req) (api.post='/api/v:version/oec/oncall/workorder/callback')
    IDVMockResp AutoTestIdv(1: IDVMockRequest req) (api.any='/osgw_v2/autotest/idv')
    DisposeQA5Response DisposeQA5(1: DisposeQA5Request req) (api.post='/osgw_v2/new/dispose/qa5')
}
