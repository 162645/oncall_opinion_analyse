package common

import (
	"context"
	"sync"
	"time"

	"code.byted.org/gopkg/logs"

	"code.byted.org/gopkg/tccclient"
	"code.byted.org/shark/antispam_common/tcc"
)

var (
	tccCli     *tccclient.ClientV2
	tccManager *tcc.TccManager
)

const (
	TCC_SERVICE_NAME      = "oec.governance.oncall_opinion_analyse"
	COLOR_POSION_TEST1    = "color_posion_test1"
	COLOR_POSION_TEST2    = "color_posion_test2"
	COLOR_POSION_TEST3    = "color_posion_test3"
	COLOR_POSION_TEST4    = "color_posion_test4"
	COLOR_POSION_TEST5    = "color_posion_test5"
	COLOR_POSION_TEST6    = "color_posion_test6"
	COLOR_POSION_TEST7    = "color_posion_test7"
	COLOR_POSION_TEST8    = "color_posion_test8"
	COLOR_POSION_TEST9    = "color_posion_test9"
	COLOR_POSION_TEST10   = "color_posion_test10"
	COLOR_POSION_STRESS1  = "color_posion_stress1"
	COLOR_POSION_STRESS2  = "color_posion_stress2"
	COLOR_POSION_STRESS3  = "color_posion_stress3"
	COLOR_POSION_STRESS4  = "color_posion_stress4"
	COLOR_POSION_STRESS5  = "color_posion_stress5"
	COLOR_POSION_STRESS6  = "color_posion_stress6"
	COLOR_POSION_STRESS7  = "color_posion_stress7"
	COLOR_POSION_STRESS8  = "color_posion_stress8"
	COLOR_POSION_STRESS9  = "color_posion_stress9"
	COLOR_POSION_STRESS10 = "color_posion_stress10"
	COLOR_POSION_STRESS11 = "color_posion_stress11"
	COLOR_POSION_STRESS12 = "color_posion_stress12"
	COLOR_POSION_STRESS13 = "color_posion_stress13"
	COLOR_POSION_STRESS20 = "color_posion_stress20"
	COLOR_POSION_STRESS21 = "color_posion_stress21"
	COLOR_POSION_STRESS22 = "color_posion_stress22"
	COLOR_POSION_STRESS23 = "color_posion_stress23"
	COLOR_POSION_STRESS24 = "color_posion_stress24"
	COLOR_POSION_STRESS25 = "color_posion_stress25"
	COLOR_POSION_STRESS26 = "color_posion_stress26"
	COLOR_POSION_STRESS27 = "color_posion_stress27"
	COLOR_POSION_STRESS28 = "color_posion_stress28"
	POSION_TEST1          = "posion_test1"
	POSION_TEST2          = "posion_test2"
	POSION_TEST3          = "posion_test3"
	POSION_TEST4          = "posion_test4"
	POSION_TEST5          = "posion_test5"
	POSION_TEST6          = "posion_test6"
	POSION_TEST7          = "posion_test7"

	PER_DOMAIN_SETTING_UPDATE_TIMER = 10
)

func init() {
	logs.CtxInfo(context.Background(), "tcc init --")

	config := tccclient.NewConfigV2()
	var err error
	tccCli, err = tccclient.NewClientV2(TCC_SERVICE_NAME, config)
	if err != nil {
		panic(err)
	}

	tccManager, err = tcc.NewTccManager(tccCli, 30*time.Second)
	if err != nil {
		panic(err)
	}
}

func GetColorPosionTest1(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST1)
	logs.CtxInfo(ctx, "DisposeTest1 : tcc color_posion_test1 : %v", config)
	return config, err
}

func GetColorPosionTest2(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST2)
	logs.CtxInfo(ctx, "DisposeTest2 : tcc color_posion_test2 : %v", config)
	return config, err
}

func GetColorPosionTest3(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST3)
	logs.CtxInfo(ctx, "DisposeTest3 : tcc color_posion_test3 : %v", config)
	return config, err
}

func GetColorPosionTest4(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST4)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test4 : %v", config)
	return config, err
}

func GetColorPosionTest5(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST5)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test5 : %v", config)
	return config, err
}

func GetColorPosionTest6(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST6)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test6 : %v", config)
	return config, err
}

func GetColorPosionTest7(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST7)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test7 : %v", config)
	return config, err
}

func GetColorPosionTest8(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST8)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test8 : %v", config)
	return config, err
}

func GetColorPosionTest9(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST9)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test9 : %v", config)
	return config, err
}

func GetColorPosionTest10(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_TEST10)
	logs.CtxInfo(ctx, "DisposeTest4 : tcc color_posion_test10 : %v", config)
	return config, err
}

func GetDisposeStress1(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS1)
	logs.CtxInfo(ctx, "DisposeStress1 : tcc color_posion_stress1 : %v", config)
	return config, err
}

func GetDisposeStress2(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS2)
	logs.CtxInfo(ctx, "DisposeStress2 : tcc color_posion_stress2 : %v", config)
	return config, err
}

func GetDisposeStress3(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS3)
	logs.CtxInfo(ctx, "DisposeStress3 : tcc color_posion_stress3 : %v", config)
	return config, err
}

func GetDisposeStress4(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS4)
	logs.CtxInfo(ctx, "DisposeStress4 : tcc color_posion_stress4 : %v", config)
	return config, err
}

func GetDisposeStress5(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS5)
	logs.CtxInfo(ctx, "DisposeStress5 : tcc color_posion_stress5 : %v", config)
	return config, err
}

func GetDisposeStress6(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS6)
	logs.CtxInfo(ctx, "DisposeStress6 : tcc color_posion_stress6 : %v", config)
	return config, err
}

func GetDisposeStress7(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS7)
	logs.CtxInfo(ctx, "DisposeStress7 : tcc color_posion_stress7 : %v", config)
	return config, err
}

func GetDisposeStress8(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS8)
	logs.CtxInfo(ctx, "DisposeStress8 : tcc color_posion_stress8 : %v", config)
	return config, err
}

func GetDisposeStress9(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS9)
	logs.CtxInfo(ctx, "DisposeStress9 : tcc color_posion_stress9 : %v", config)
	return config, err
}

func GetDisposeStress10(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS10)
	logs.CtxInfo(ctx, "DisposeStress10 : tcc color_posion_stress10 : %v", config)
	return config, err
}

func GetDisposeStress11(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS11)
	logs.CtxInfo(ctx, "DisposeStress11 : tcc color_posion_stress11 : %v", config)
	return config, err
}

func GetDisposeStress12(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS12)
	logs.CtxInfo(ctx, "DisposeStress12 : tcc color_posion_stress12 : %v", config)
	return config, err
}

func GetDisposeStress13(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS13)
	logs.CtxInfo(ctx, "DisposeStress13 : tcc color_posion_stress13 : %v", config)
	return config, err
}

//
//func UpdateTest1() {
//	updateTest1()
//	ticker := time.NewTicker(time.Second * PER_DOMAIN_SETTING_UPDATE_TIMER)
//	go func() {
//		defer func() {
//			if err := recover(); err != nil {
//				logs.Warn("UpdateTest1 updateDomainSetting")
//			}
//		}()
//		for t := range ticker.C {
//			logs.Info("UpdateTest1 update domain setting range,Tick at", t)
//			updateTest1()
//		}
//	}()
//}

func GetDisposeStress20(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS20)
	logs.CtxInfo(ctx, "DisposeStress20 : tcc color_posion_stress20 : %v", config)
	return config, err
}

func GetDisposeStress21(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS21)
	logs.CtxInfo(ctx, "DisposeStress21 : tcc color_posion_stress21 : %v", config)
	return config, err
}

func GetDisposeStress22(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS22)
	logs.CtxInfo(ctx, "DisposeStress22 : tcc color_posion_stress22 : %v", config)
	return config, err
}

func GetDisposeStress23(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS23)
	logs.CtxInfo(ctx, "DisposeStress23 : tcc color_posion_stress23 : %v", config)
	return config, err
}

func GetDisposeStress24(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS24)
	logs.CtxInfo(ctx, "DisposeStress24 : tcc color_posion_stress24 : %v", config)
	return config, err
}

func GetDisposeStress25(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS25)
	logs.CtxInfo(ctx, "DisposeStress25 : tcc color_posion_stress25 : %v", config)
	return config, err
}

func GetDisposeStress26(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS26)
	logs.CtxInfo(ctx, "DisposeStress26 : tcc color_posion_stress26 : %v", config)
	return config, err
}
func GetDisposeStress27(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS27)
	logs.CtxInfo(ctx, "DisposeStress27 : tcc color_posion_stress27 : %v", config)
	return config, err
}

func GetDisposeStress28(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, COLOR_POSION_STRESS28)
	logs.CtxInfo(ctx, "DisposeStress28 : tcc color_posion_stress28 : %v", config)
	return config, err
}

func GetPosionTest1(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST1)
	logs.CtxInfo(ctx, "PosionTest1 : tcc posion_test1 : %v", config)
	return config, err
}

func GetPosionTest2(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST2)
	logs.CtxInfo(ctx, "PosionTest2 : tcc posion_test2 : %v", config)
	return config, err
}

func GetPosionTest3(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST3)
	logs.CtxInfo(ctx, "PosionTest3 : tcc posion_test3 : %v", config)
	return config, err
}

func GetPosionTest4(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST4)
	logs.CtxInfo(ctx, "PosionTest4 : tcc posion_test4 : %v", config)
	return config, err
}

func GetPosionTest5(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST5)
	logs.CtxInfo(ctx, "PosionTest5 : tcc posion_test5 : %v", config)
	return config, err
}

func GetPosionTest6(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST6)
	logs.CtxInfo(ctx, "PosionTest6 : tcc posion_test6 : %v", config)
	return config, err
}

func GetPosionTest7(ctx context.Context) (string, error) {
	config, err := tccCli.Get(ctx, POSION_TEST7)
	logs.CtxInfo(ctx, "PosionTest7 : tcc posion_test7 : %v", config)
	return config, err
}

var (
	listenerCache = sync.Map{}
)

func TccGet(ctx context.Context, key string) (string, error) {
	_, ok := listenerCache.Load(key)
	if !ok {
		err := tccCli.AddListener(key, func(value string, err error) {
			if err != nil {
				logs.CtxWarn(ctx, "tccGet err : %v", err)
				return
			}
			logs.CtxInfo(ctx, "tccGet key:%v, value:%v, err:%v", key, value, err)
			listenerCache.Store(key, value)
		})
		if err != nil {
			logs.CtxFatal(ctx, "tcc listen err : %v", err)
			return "", err
		}
	}
	v, _ := listenerCache.Load(key)
	return v.(string), nil
}
