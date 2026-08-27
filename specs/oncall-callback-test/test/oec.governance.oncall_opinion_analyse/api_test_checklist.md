# API Test Workflow Checklist: Oncall Callback Handler
**Mode**: Execute Only
**Created**: 2026-04-30
**PSM**: oec.governance.oncall_opinion_analyse

## Part 2: Test Case Execution & Reporting
- [x] Preparation: Install/Reinstall `api-mind` tool if not already done.
- [x] Preparation: Verify `api_test_case.yaml` exists. (Get X-Jwt-Token via `user_jwt` skill if not done yet).
- [x] Assess Risk: Check environment safety (boe/localhost vs ppe/prod) and test accounts.
- [x] Assess Risk: Check for write operations (POST/PUT/DELETE) in test cases.
- [x] Assess Risk: Obtain user confirmation to continue if the environment is unsafe and contains write operations.
- [x] Execution: Use `api-mind test-exec` to execute cases and save logs.
- [x] Reporting: Read `resources/test_report_guide.md` and generate `test_report.md`.
