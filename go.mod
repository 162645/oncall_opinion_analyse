module code.byted.org/oec/oncall_opinion_analyse

go 1.18

require (
	code.byted.org/gopkg/context v0.0.1
	code.byted.org/gopkg/env v1.7.2
	code.byted.org/gopkg/logs v1.2.23
	code.byted.org/gopkg/logs/v2 v2.1.51
	code.byted.org/gopkg/metrics v1.4.25
	code.byted.org/gopkg/pkg v0.0.0-20210817064112-6fe00340bb36
	code.byted.org/gopkg/tccclient v1.4.3
	code.byted.org/gorm/bytedgen v0.3.24
	code.byted.org/gorm/bytedgorm v0.9.23
	code.byted.org/middleware/hertz v1.11.2
	code.byted.org/middleware/hertz_ext/v2 v2.1.7
	code.byted.org/oec/lazyman/metricsutil v1.0.4
	code.byted.org/oec/rpcv2_oec_security_dispose_center v0.0.0-20250721090431-d35501a8602f
	code.byted.org/oec/status_code v0.0.0-20231225091135-2f813a226737
	code.byted.org/shark/antispam_common v0.5.16
	github.com/bytedance/sonic v1.9.2
	github.com/cloudwego/hertz v0.7.3
	github.com/json-iterator/go v1.1.12
	github.com/stretchr/testify v1.8.3
	google.golang.org/protobuf v1.32.0
	gorm.io/driver/mysql v1.5.2
	gorm.io/gen v0.3.24
	gorm.io/gorm v1.25.5
	gorm.io/plugin/dbresolver v1.5.0
)

require (
	code.byted.org/aiops/apm_vendor_byted v0.0.24 // indirect
	code.byted.org/aiops/metrics_codec v0.0.21 // indirect
	code.byted.org/aiops/monitoring-common-go v0.0.5 // indirect
	code.byted.org/bytedance/concurrent_loader v1.0.0 // indirect
	code.byted.org/bytedtrace-contrib/kitex-go v1.1.48 // indirect
	code.byted.org/bytedtrace/bytedtrace-client-go v1.0.46 // indirect
	code.byted.org/bytedtrace/bytedtrace-common/go v0.0.12 // indirect
	code.byted.org/bytedtrace/bytedtrace-conf-provider-client-go v0.0.19 // indirect
	code.byted.org/bytedtrace/interface-go v1.0.20 // indirect
	code.byted.org/bytedtrace/serializer-go v1.0.0 // indirect
	code.byted.org/gopkg/apm_vendor_interface v0.0.3 // indirect
	code.byted.org/gopkg/asyncache v0.0.0-20210129072708-1df5611dba17 // indirect
	code.byted.org/gopkg/asynccache v0.0.0-20210422090342-26f94f7676b8 // indirect
	code.byted.org/gopkg/bytedmysql v1.1.20 // indirect
	code.byted.org/gopkg/consul v1.2.6 // indirect
	code.byted.org/gopkg/ctxvalues v0.6.0 // indirect
	code.byted.org/gopkg/debug v0.10.1 // indirect
	code.byted.org/gopkg/etcd_util v2.3.3+incompatible // indirect
	code.byted.org/gopkg/etcdproxy v0.1.1 // indirect
	code.byted.org/gopkg/lang v0.21.5 // indirect
	code.byted.org/gopkg/logid v0.0.0-20211104042040-f78600e482f2 // indirect
	code.byted.org/gopkg/metainfo v0.1.4 // indirect
	code.byted.org/gopkg/metrics/v3 v3.1.31 // indirect
	code.byted.org/gopkg/metrics/v4 v4.1.0 // indirect
	code.byted.org/gopkg/metrics_core v0.0.32 // indirect
	code.byted.org/gopkg/net2 v1.5.0 // indirect
	code.byted.org/gopkg/stats v1.2.7 // indirect
	code.byted.org/gopkg/thrift v1.6.1 // indirect
	code.byted.org/hystrix/hystrix-go v0.0.0-20190214095017-a2a890c81cd5 // indirect
	code.byted.org/ies/starling_goclient v0.2.7 // indirect
	code.byted.org/iespkg/bytedkits-go/goext v0.4.0 // indirect
	code.byted.org/iespkg/retry-go v0.1.2 // indirect
	code.byted.org/kite/endpoint v3.7.5+incompatible // indirect
	code.byted.org/kite/kitc v3.10.21+incompatible // indirect
	code.byted.org/kite/kitex v1.11.6 // indirect
	code.byted.org/kite/kitex-overpass-suite v0.0.35 // indirect
	code.byted.org/kite/kitutil v3.8.4+incompatible // indirect
	code.byted.org/kitex/apache_monitor v0.1.1 // indirect
	code.byted.org/lang/trace v0.0.2 // indirect
	code.byted.org/lidar/profiler v0.3.2 // indirect
	code.byted.org/lidar/profiler/hertz v0.0.0-20230801111316-7e5562fd8659 // indirect
	code.byted.org/log_market/gosdk v0.0.0-20230524072203-e069d8367314 // indirect
	code.byted.org/log_market/loghelper v0.1.10 // indirect
	code.byted.org/log_market/tracelog v0.1.4 // indirect
	code.byted.org/log_market/ttlogagent_gosdk v0.0.6 // indirect
	code.byted.org/log_market/ttlogagent_gosdk/v4 v4.0.51 // indirect
	code.byted.org/middleware/fic_client v0.2.2 // indirect
	code.byted.org/middleware/gocaller v0.0.4 // indirect
	code.byted.org/oec/lazyman v1.0.0 // indirect
	code.byted.org/oec/lazyman/starling v1.0.1 // indirect
	code.byted.org/oec/lazyman/strutil v1.0.0 // indirect
	code.byted.org/oec/overpass_common_shadow v0.0.0-20250721090140-311c3ba56a6c // indirect
	code.byted.org/oec/overpass_common_struct v0.0.0-20250721090220-1811d44debc3 // indirect
	code.byted.org/overpass/common v0.0.0-20241127033622-79f193603286 // indirect
	code.byted.org/security/go-spiffe-v2 v1.0.6 // indirect
	code.byted.org/security/memfd v0.0.1 // indirect
	code.byted.org/security/sensitive_finder_engine v0.3.18 // indirect
	code.byted.org/security/zti-jwt-helper-golang v1.0.16 // indirect
	code.byted.org/service_mesh/shmipc v0.2.13 // indirect
	code.byted.org/trace/trace-client-go v1.3.6 // indirect
	github.com/Knetic/govaluate v3.0.1-0.20171022003610-9aa49832a739+incompatible // indirect
	github.com/apache/thrift v0.13.0 // indirect
	github.com/beorn7/perks v1.0.1 // indirect
	github.com/bytedance/go-tagexpr/v2 v2.9.2 // indirect
	github.com/bytedance/gopkg v0.0.0-20230728082804-614d0af6619b // indirect
	github.com/caarlos0/env/v6 v6.10.1 // indirect
	github.com/chenzhuoyu/base64x v0.0.0-20221115062448-fe3a3abad311 // indirect
	github.com/chenzhuoyu/iasm v0.0.0-20230222070914-0b1b64b0e762 // indirect
	github.com/choleraehyq/pid v0.0.18 // indirect
	github.com/cloudwego/fastpb v0.0.4 // indirect
	github.com/cloudwego/frugal v0.1.6 // indirect
	github.com/cloudwego/kitex v0.5.2 // indirect
	github.com/cloudwego/localsession v0.1.0 // indirect
	github.com/cloudwego/netpoll v0.5.1 // indirect
	github.com/cloudwego/thriftgo v0.2.9 // indirect
	github.com/davecgh/go-spew v1.1.2-0.20180830191138-d8f796af33cc // indirect
	github.com/fsnotify/fsnotify v1.5.4 // indirect
	github.com/go-jose/go-jose/v3 v3.0.0 // indirect
	github.com/go-kit/log v0.2.1 // indirect
	github.com/go-logfmt/logfmt v0.6.0 // indirect
	github.com/go-ole/go-ole v1.2.6 // indirect
	github.com/go-sql-driver/mysql v1.7.1 // indirect
	github.com/gogo/protobuf v1.3.2 // indirect
	github.com/golang/mock v1.6.0 // indirect
	github.com/golang/protobuf v1.5.3 // indirect
	github.com/google/pprof v0.0.0-20221103000818-d260c55eee4c // indirect
	github.com/google/uuid v1.3.0 // indirect
	github.com/gorilla/mux v1.8.0 // indirect
	github.com/hashicorp/hcl v1.0.0 // indirect
	github.com/hbollon/go-edlib v1.6.0 // indirect
	github.com/henrylee2cn/ameda v1.4.10 // indirect
	github.com/henrylee2cn/goutil v0.0.0-20210127050712-89660552f6f8 // indirect
	github.com/hertz-contrib/http2 v0.1.1 // indirect
	github.com/hertz-contrib/localsession v0.0.0-20230912121050-49d165b95cbf // indirect
	github.com/jhump/protoreflect v1.8.2 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/klauspost/compress v1.16.7 // indirect
	github.com/klauspost/cpuid/v2 v2.2.5 // indirect
	github.com/magiconair/properties v1.8.5 // indirect
	github.com/mitchellh/mapstructure v1.4.0 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/gls v0.0.0-20220109145502-612d0167dce5 // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
	github.com/mohae/deepcopy v0.0.0-20170929034955-c48cc78d4826 // indirect
	github.com/nicksnyder/go-i18n/v2 v2.2.0 // indirect
	github.com/nyaruka/phonenumbers v1.0.56 // indirect
	github.com/oleiade/lane v1.0.1 // indirect
	github.com/opentracing/opentracing-go v1.2.0 // indirect
	github.com/pelletier/go-toml v1.9.0 // indirect
	github.com/pkg/errors v0.9.1 // indirect
	github.com/pmezard/go-difflib v1.0.1-0.20181226105442-5d4384ee4fb2 // indirect
	github.com/power-devops/perfstat v0.0.0-20210106213030-5aafc221ea8c // indirect
	github.com/shirou/gopsutil/v3 v3.22.1 // indirect
	github.com/sirupsen/logrus v1.9.3 // indirect
	github.com/spf13/afero v1.9.2 // indirect
	github.com/spf13/cast v1.3.1 // indirect
	github.com/spf13/jwalterweatherman v1.1.0 // indirect
	github.com/spf13/pflag v1.0.5 // indirect
	github.com/spf13/viper v1.7.1 // indirect
	github.com/subosito/gotenv v1.2.0 // indirect
	github.com/tidwall/gjson v1.14.4 // indirect
	github.com/tidwall/match v1.1.1 // indirect
	github.com/tidwall/pretty v1.2.0 // indirect
	github.com/twitchyliquid64/golang-asm v0.15.1 // indirect
	github.com/yusufpapurcu/wmi v1.2.2 // indirect
	github.com/zeebo/errs v1.3.0 // indirect
	golang.org/x/arch v0.4.0 // indirect
	golang.org/x/crypto v0.11.0 // indirect
	golang.org/x/mod v0.10.0 // indirect
	golang.org/x/net v0.12.0 // indirect
	golang.org/x/sync v0.2.0 // indirect
	golang.org/x/sys v0.24.0 // indirect
	golang.org/x/text v0.11.0 // indirect
	golang.org/x/time v0.3.0 // indirect
	golang.org/x/tools v0.9.1 // indirect
	google.golang.org/genproto v0.0.0-20230706204954-ccb25ca9f130 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20230720185612-659f7aaaa771 // indirect
	google.golang.org/grpc v1.56.2 // indirect
	gopkg.in/ini.v1 v1.62.0 // indirect
	gopkg.in/yaml.v2 v2.4.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
	gorm.io/datatypes v1.1.1-0.20230130040222-c43177d3cf8c // indirect
	gorm.io/hints v1.1.2 // indirect
)
