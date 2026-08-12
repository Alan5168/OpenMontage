# Fixtures for Content Studio Director Skill

## show-gate fixture
示例输入: show-gate --project-id fixture-pi-resume-e2e
预期输出: schema_version=content-studio-sceneplan-gate/v1, checkpoint sha256, cuts[], visual_continuity

## submit-continuity-regen fixture
示例输入: submit-continuity-regen --project-id fixture-pi-resume-e2e
预期输出: {"status":"ACCEPTED","job_id":"...","production_started":false}

## VISUAL_QA fixture
已知 continuity failure 图片 -> VISUAL_QA.json with continuity=FAIL
VCP 重生新图 -> VISUAL_QA.json with continuity=PASS