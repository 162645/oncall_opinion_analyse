package bussinessmodel

const (
	CST     = "CST"
	SET     = "SET"
	RD      = "RD"
	UNKNOWN = "UNKNOWN"
)

func GetRootFieldById(i int64) string {
	buss, ok := IdToField[i]
	var rootField string
	if !ok {
		rootField = UNKNOWN
	} else {
		rootField = buss.RootField
	}
	return rootField
}

func GetTenantIdsByRootField(root string) []int64 {
	var res []int64
	for id, model := range IdToField {
		if root == model.RootField {
			res = append(res, id)
		}
	}
	return res
}

var IdToField = map[int64]BusinessModel{
	2856: {RootField: CST, SecondField: "直播工具"},
	2857: {RootField: CST, SecondField: "商家平台"},
	4268: {RootField: CST, SecondField: "商品问题"},
	4273: {RootField: CST, SecondField: "结算"},
	2858: {RootField: CST, SecondField: "达人联盟"},
	4270: {RootField: CST, SecondField: "履约"},
	2859: {RootField: CST, SecondField: "交易支付"},
	4272: {RootField: CST, SecondField: "逆向交易"},
	2860: {RootField: CST, SecondField: "营销"},
	2862: {RootField: CST, SecondField: "数据平台"},
	2863: {RootField: CST, SecondField: "other"},
	1916: {RootField: SET, SecondField: "国际电商Angel"},
	4524: {RootField: RD, SecondField: "TT-C端", ThirdField: "内容电商"},
	2267: {RootField: RD, SecondField: "TT-C端", ThirdField: "QA"},
	4523: {RootField: RD, SecondField: "TT-C端", ThirdField: "货架电商"},
	4520: {RootField: RD, SecondField: "TT-C端", ThirdField: "c端营销"},
	4525: {RootField: RD, SecondField: "TT-C端", ThirdField: "正向交易"},
	4526: {RootField: RD, SecondField: "TT-C端", ThirdField: "逆向售后"},
	4815: {RootField: RD, SecondField: "TT-C端", ThirdField: "店铺橱窗"},
	4816: {RootField: RD, SecondField: "TT-C端", ThirdField: "搜索"},
	4370: {RootField: RD, SecondField: "TT-C端", ThirdField: "QA"},
	4429: {RootField: RD, SecondField: "平台治理", ThirdField: "商家、商品治理"},
	4430: {RootField: RD, SecondField: "平台治理", ThirdField: "售后履约治理"},
	4428: {RootField: RD, SecondField: "平台治理", ThirdField: "达人、内容治理"},
	4786: {RootField: RD, SecondField: "平台治理", ThirdField: "生态&体验"},
	4785: {RootField: RD, SecondField: "平台治理", ThirdField: "安全合规风控"},
	3382: {RootField: RD, SecondField: "平台治理", ThirdField: "哨兵引擎"},
	4817: {RootField: RD, SecondField: "平台治理", ThirdField: "哨兵引擎QA"},
	3375: {RootField: RD, SecondField: "平台治理", ThirdField: "审核平台"},
	3380: {RootField: RD, SecondField: "平台治理", ThirdField: "决策处置（奖惩平台）"},
	2207: {RootField: RD, SecondField: "营销中心", ThirdField: "营销工具/价格中心"},
	2269: {RootField: RD, SecondField: "营销中心", ThirdField: "营销工具/价格中心QA"},
	3394: {RootField: RD, SecondField: "营销中心", ThirdField: "招商选品/搭建投放QA"},
	3390: {RootField: RD, SecondField: "营销中心", ThirdField: "搭建投放"},
	2203: {RootField: RD, SecondField: "达人联盟", ThirdField: "达人联盟"},
	2268: {RootField: RD, SecondField: "达人联盟", ThirdField: "达人联盟QA"},
	2211: {RootField: RD, SecondField: "运营平台", ThirdField: "运营平台"},
	3150: {RootField: RD, SecondField: "运营平台", ThirdField: "Pearl-Seller-Seller Center"},
	2212: {RootField: RD, SecondField: "开放平台", ThirdField: "开放平台"},
	2265: {RootField: RD, SecondField: "开放平台", ThirdField: "开放平台QA"},
	2205: {RootField: RD, SecondField: "数据中心", ThirdField: "数据中心"},
	2266: {RootField: RD, SecondField: "数据中心", ThirdField: "数据中心QA"},
	4818: {RootField: RD, SecondField: "数据中心", ThirdField: "pearl-DMP"},
	2204: {RootField: RD, SecondField: "交易中台", ThirdField: "正向交易-正向中台"},
	2272: {RootField: RD, SecondField: "交易中台", ThirdField: "交易中台QA"},
	2210: {RootField: RD, SecondField: "交易中台", ThirdField: "逆向交易-售后中台"},
	3383: {RootField: RD, SecondField: "支付中台", ThirdField: "支付退款"},
	2271: {RootField: RD, SecondField: "支付中台", ThirdField: "支付中台/税务QA"},
	4819: {RootField: RD, SecondField: "支付中台", ThirdField: "计费"},
	3385: {RootField: RD, SecondField: "支付中台", ThirdField: "结算"},
	2209: {RootField: RD, SecondField: "税务中台", ThirdField: "税务"},
	3768: {RootField: RD, SecondField: "履约中台", ThirdField: "履约中台QA"},
	3372: {RootField: RD, SecondField: "履约中台", ThirdField: "履约中台"},
	2456: {RootField: RD, SecondField: "商家中台", ThirdField: "商家中台"},
	2270: {RootField: RD, SecondField: "商家中台", ThirdField: "商家中台/商家平台QA"},
	2455: {RootField: RD, SecondField: "商家平台", ThirdField: "商家平台"},
	4484: {RootField: RD, SecondField: "商家客服", ThirdField: "商家客服"},
	3386: {RootField: RD, SecondField: "商品中台", ThirdField: "商品基础"},
	2822: {RootField: RD, SecondField: "商品中台", ThirdField: "商品中台"},
	4820: {RootField: RD, SecondField: "商品中台", ThirdField: "CPVB"},
	4821: {RootField: RD, SecondField: "商品中台", ThirdField: "商品发布"},
	4463: {RootField: RD, SecondField: "商品中台", ThirdField: "库存"},
	4822: {RootField: RD, SecondField: "物流中台", ThirdField: "实操配送"},
	4823: {RootField: RD, SecondField: "物流中台", ThirdField: "物流协同"},
	4780: {RootField: RD, SecondField: "供应链", ThirdField: "供应链"},
}

type BusinessModel struct {
	RootField   string
	SecondField string
	ThirdField  string
}
