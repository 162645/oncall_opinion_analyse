package query

import (
	"code.byted.org/gopkg/env"
	"code.byted.org/gopkg/logs"
	"code.byted.org/gorm/bytedgorm"
	"code.byted.org/oec/oncall_opinion_analyse/biz/config"
	"context"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
	"gorm.io/plugin/dbresolver"
	"sync"
)

var (
	db   *gorm.DB
	once sync.Once
)

func Init() {
	once.Do(func() {
		// init
		DbRuntime := config.DBName
		psmRuntime := config.PSM
		if env.IsBoe() {
			DbRuntime = config.BOE_DBName
			psmRuntime = config.BOE_PSM
		}
		options := bytedgorm.WithDefaults()

		if env.IsBoe() {
			cfg := &gorm.Config{
				Logger: logger.Default.LogMode(logger.Info),
			}
			options.Options = append(options.Options, cfg)
		}

		DB, err := gorm.Open(
			bytedgorm.MySQL(psmRuntime /*数据库PSM*/, DbRuntime /*数据库名*/).WithReadReplicas(),
			options, bytedgorm.WithSingularTable(),
		)
		// check err
		if err != nil {
			panic(err)
		}
		db = DB
		if env.IsBoe() {
			db = db.Debug()
		}
		logs.Info("init mysql for %s success", psmRuntime)
	})
}

// WriteDB ...
func WriteDB(ctx context.Context) *gorm.DB {
	return db.Clauses(dbresolver.Write).WithContext(ctx)
}

// ReadDB ...
func ReadDB(ctx context.Context) *gorm.DB {
	return db.Clauses(dbresolver.Read).WithContext(ctx)
}

// Read write separation
func DB(ctx context.Context) *gorm.DB {
	return db.WithContext(ctx)
}
