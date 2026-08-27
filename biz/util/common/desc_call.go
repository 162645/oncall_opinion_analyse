package common

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"io/ioutil"
	"net/http"
	"time"

	"code.byted.org/gopkg/env"
	"code.byted.org/gopkg/logs"
	"code.byted.org/gopkg/pkg/errors"
)

var descHttpClient = http.Client{
	Transport: &http.Transport{
		MaxIdleConnsPerHost: 100,
		MaxConnsPerHost:     1000,
		IdleConnTimeout:     10 * time.Minute,
	},
	Timeout: time.Minute * 10,
}

// CrossIDCCallV2,通过打标，实现跨机房调用
func CrossIDCCallV2(ctx context.Context, destIDC string, rawUrl string, method string, body []byte, headers map[string]string, out interface{}) (httpStatus int, err error) {
	if env.IsBoe() {
		return 0, nil
	}
	if len(destIDC) == 0 {
		return 0, errors.New("AsyncTTpCds idc is nil")
	}

	// 1. httpClient Transport
	headers["x-tt-env"] = "ppe_feature_ware_alarm"
	headers["x-use-ppe"] = "1"
	headers["Content-Type"] = "application/json;charset=UTF-8"

	url := "http://oec-rmc-sg.byteintl.net" + rawUrl
	var reqBody io.Reader = nil
	if body != nil {
		reqBody = bytes.NewBuffer(body)
	}

	// 2.发起请求
	request, err := http.NewRequest(method, url, reqBody)

	if err != nil {
		return 0, errors.Wrap(err, "create request err")
	}

	for key, value := range headers {
		request.Header.Set(key, value)
	}

	logs.CtxInfo(ctx, "show the header: %v", request.Header)
	resp, err := descHttpClient.Do(request)
	if err != nil {
		return 0, errors.Wrap(err, "http do err")
	}

	defer resp.Body.Close()
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, err
	}

	// 3.解析结果
	if resp.StatusCode != 200 {
		logs.CtxInfo(ctx, "error resp body: %v", string(respBody))
		return resp.StatusCode, errors.Errorf("http err, resp code is:%d", resp.StatusCode)
	}
	return resp.StatusCode, json.Unmarshal(respBody, out)
}
