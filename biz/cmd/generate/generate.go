package main

import (
	"code.byted.org/gorm/bytedgen"
	"code.byted.org/gorm/bytedgorm"
	"code.byted.org/oec/oncall_opinion_analyse/biz/config"
	"code.byted.org/oec/oncall_opinion_analyse/biz/dal/model"
	"fmt"
	"gorm.io/driver/mysql"
	"gorm.io/gen"
	"gorm.io/gorm"
	"os"
)

// db operate generate
func main() {
	g := bytedgen.NewGenerator(gen.Config{
		OutPath:           "./biz/dal/query",
		ModelPkgPath:      "./biz/dal/model",
		FieldNullable:     true,
		FieldWithIndexTag: true,
		FieldWithTypeTag:  true,
	})

	var DB *gorm.DB
	DB = ConnectDB()
	g.UseDB(DB)
	tbl1 := g.GenerateModel("oncall_origin_record")
	tbl2 := g.GenerateModel("oncall_listen_alert_task")
	tbl3 := g.GenerateModel("alert_task")
	tbl4 := g.GenerateModel("id_keyword_map")
	tbl5 := g.GenerateModel("cronjob_result")
	g.ApplyBasic(tbl1, tbl2, tbl3, tbl4, tbl5)
	g.ApplyInterface(func(model.Method) {}, tbl1)
	g.Execute()
}

func ConnectDB() (conn *gorm.DB) {
	var err error
	if os.Getenv("DB_CONNECT_MODE") == "DSN" {
		conn, err = gorm.Open(mysql.Open(config.MySQLDSN))
	} else {
		conn, err = gorm.Open(
			bytedgorm.MySQL(config.PSM /*数据库PSM*/, config.DBName /*数据库名*/).WithReadReplicas(),
			bytedgorm.WithDefaults(), bytedgorm.WithSingularTable(),
		)
	}
	if err != nil {
		panic(fmt.Errorf("cannot establish db connection: %w", err))
	}
	return conn
}
