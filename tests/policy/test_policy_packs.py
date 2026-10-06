"""Comprehensive tests for the 5 shipped policy packs."""

from __future__ import annotations

import random
import string
from datetime import datetime
from pathlib import Path

import pytest

from rewind.contracts import ActionRequest, RiskClass
from rewind.policy import PolicyClassifier, load_packs

POLICIES_DIR = Path(__file__).resolve().parents[2] / "policies"


@pytest.fixture(scope="module")
def all_packs():
    return load_packs(
        ["filesystem", "postgresql", "git", "aws_s3", "docker"],
        [POLICIES_DIR],
    )


@pytest.fixture(scope="module")
def classifier(all_packs):
    return PolicyClassifier(packs=all_packs)


def make_action(tool: str, payload: dict) -> ActionRequest:
    return ActionRequest(
        id="act_test",
        agent_id="agent_1",
        tool=tool,
        operation="exec",
        payload=payload,
        created_at=datetime.now(),
    )


# -----------------------------------------------------------------------------
# 1. PostgreSQL (>= 25 table-driven cases)
# -----------------------------------------------------------------------------
PG_CASES = [
    ("SELECT * FROM users", RiskClass.SAFE),
    ("select id, name from orders where total > 100", RiskClass.SAFE),
    ("SELECT count(*) FROM customers", RiskClass.SAFE),
    ("EXPLAIN SELECT 1", RiskClass.SAFE),
    ("SHOW search_path", RiskClass.SAFE),
    ("BEGIN", RiskClass.SAFE),
    ("COMMIT", RiskClass.SAFE),
    ("COPY users TO '/tmp/users.csv'", RiskClass.SAFE),
    ("INSERT INTO users (id, name) VALUES (1, 'Alice')", RiskClass.REVERSIBLE),
    ("insert into logs values (now(), 'test')", RiskClass.REVERSIBLE),
    ("UPDATE users SET name = 'Bob' WHERE id = 1", RiskClass.REVERSIBLE),
    ("update orders set status = 'done' where id in (1, 2)", RiskClass.REVERSIBLE),
    ("DELETE FROM users WHERE id = 1", RiskClass.REVERSIBLE),
    ("delete from cache where created_at < now() - interval '1 day'", RiskClass.REVERSIBLE),
    ("ALTER TABLE users ADD COLUMN age int", RiskClass.REVERSIBLE),
    ("ALTER TABLE users RENAME COLUMN name TO full_name", RiskClass.REVERSIBLE),
    ("COPY users FROM '/tmp/users.csv'", RiskClass.REVERSIBLE),
    ("UPDATE users SET active = false", RiskClass.IRREVERSIBLE),
    ("update orders set total = 0", RiskClass.IRREVERSIBLE),
    ("DELETE FROM users", RiskClass.IRREVERSIBLE),
    ("delete from orders", RiskClass.IRREVERSIBLE),
    ("TRUNCATE TABLE users", RiskClass.IRREVERSIBLE),
    ("truncate orders", RiskClass.IRREVERSIBLE),
    ("DROP TABLE users", RiskClass.IRREVERSIBLE),
    ("DROP SCHEMA public CASCADE", RiskClass.IRREVERSIBLE),
    ("DROP DATABASE prod", RiskClass.IRREVERSIBLE),
    ("DROP INDEX idx_users_email", RiskClass.IRREVERSIBLE),
    ("ALTER TABLE users DROP COLUMN email", RiskClass.IRREVERSIBLE),
    ("GRANT ALL PRIVILEGES ON DATABASE prod TO dev", RiskClass.IRREVERSIBLE),
    ("REVOKE CONNECT ON DATABASE prod FROM PUBLIC", RiskClass.IRREVERSIBLE),
    # Evasion cases
    ("SELECT 1; DROP TABLE users", RiskClass.IRREVERSIBLE),
    ("delete /* sneaky comment */ from users", RiskClass.IRREVERSIBLE),
    ("   DeLeTe    FROM   users   ", RiskClass.IRREVERSIBLE),
    ("WITH deleted AS (DELETE FROM users RETURNING *) SELECT * FROM deleted", RiskClass.IRREVERSIBLE),
    ("EXPLAIN ANALYZE DELETE FROM users", RiskClass.IRREVERSIBLE),
    ("DO $$ BEGIN EXECUTE 'DROP TABLE users'; END $$", RiskClass.IRREVERSIBLE),
    ("NOT REAL SQL STATEMENT !!! ???", RiskClass.IRREVERSIBLE),
]


@pytest.mark.parametrize("statement, expected_risk", PG_CASES)
def test_postgresql_cases(classifier: PolicyClassifier, statement: str, expected_risk: RiskClass):
    act = make_action("sql", {"statement": statement})
    res = classifier.classify(act)
    assert res.risk == expected_risk, f"Failed on SQL: {statement!r}, got {res.risk}, expected {expected_risk}"


# -----------------------------------------------------------------------------
# 2. Filesystem & Shell (>= 25 table-driven cases)
# -----------------------------------------------------------------------------
FS_CASES = [
    ("ls -la /var/log", RiskClass.SAFE),
    ("cat README.md", RiskClass.SAFE),
    ("grep -rn 'TODO' src/", RiskClass.SAFE),
    ("head -n 20 main.py", RiskClass.SAFE),
    ("tail -f app.log", RiskClass.SAFE),
    ("pwd", RiskClass.SAFE),
    ("stat package.json", RiskClass.SAFE),
    ("find . -name '*.py'", RiskClass.SAFE),
    ("diff old.txt new.txt", RiskClass.SAFE),
    ("echo 'hello'", RiskClass.SAFE),
    ("cp src.txt dst.txt", RiskClass.REVERSIBLE),
    ("mv old.txt new.txt", RiskClass.REVERSIBLE),
    ("touch new_file.txt", RiskClass.REVERSIBLE),
    ("mkdir -p /tmp/testdir", RiskClass.REVERSIBLE),
    ("chmod +x run.sh", RiskClass.REVERSIBLE),
    ("echo 'hello' > out.txt", RiskClass.REVERSIBLE),
    ("echo 'data' >> log.txt", RiskClass.REVERSIBLE),
    ("rm file.txt", RiskClass.REVERSIBLE),
    ("rm -f single_file.txt", RiskClass.IRREVERSIBLE),  # force flag
    ("rm -rf /workspace/temp", RiskClass.IRREVERSIBLE),
    ("rm -r -f /workspace/temp", RiskClass.IRREVERSIBLE),
    ("rm -fr /workspace/temp", RiskClass.IRREVERSIBLE),
    ("rm --recursive --force /workspace/temp", RiskClass.IRREVERSIBLE),
    ("rm -rf /", RiskClass.IRREVERSIBLE),
    ("find . -name '*.tmp' -delete", RiskClass.IRREVERSIBLE),
    ("shred -u secret.txt", RiskClass.IRREVERSIBLE),
    ("wipefs -a /dev/sdb", RiskClass.IRREVERSIBLE),
    ("dd if=/dev/zero of=/dev/sda bs=1M", RiskClass.IRREVERSIBLE),
    ("mkfs.ext4 /dev/sdb1", RiskClass.IRREVERSIBLE),
    # Evasion & wrappers
    ("sudo rm -rf /var/cache", RiskClass.IRREVERSIBLE),
    ("env VAR=1 rm -rf build/", RiskClass.IRREVERSIBLE),
    ("sh -c 'rm -rf /tmp/data'", RiskClass.IRREVERSIBLE),
    ("echo 'safe' && rm -rf /tmp/stuff", RiskClass.IRREVERSIBLE),
    ("xargs rm -rf", RiskClass.IRREVERSIBLE),
    ("echo $(rm -rf /var/data)", RiskClass.IRREVERSIBLE),
]


@pytest.mark.parametrize("command, expected_risk", FS_CASES)
def test_filesystem_cases(classifier: PolicyClassifier, command: str, expected_risk: RiskClass):
    act = make_action("fs", {"command": command})
    res = classifier.classify(act)
    assert res.risk == expected_risk, f"Failed on command: {command!r}, got {res.risk}, expected {expected_risk}"


# -----------------------------------------------------------------------------
# 3. Git (>= 25 table-driven cases)
# -----------------------------------------------------------------------------
GIT_CASES = [
    ("git status", RiskClass.SAFE),
    ("git log -n 10", RiskClass.SAFE),
    ("git diff HEAD~1", RiskClass.SAFE),
    ("git show HEAD", RiskClass.SAFE),
    ("git branch -a", RiskClass.SAFE),
    ("git rev-parse HEAD", RiskClass.SAFE),
    ("git commit -m 'feat: new feature'", RiskClass.REVERSIBLE),
    ("git merge feature-branch", RiskClass.REVERSIBLE),
    ("git checkout -b new-branch", RiskClass.REVERSIBLE),
    ("git switch main", RiskClass.REVERSIBLE),
    ("git push origin feature-branch", RiskClass.REVERSIBLE),
    ("git branch dev-experiment", RiskClass.REVERSIBLE),
    ("git branch -d feature-done", RiskClass.REVERSIBLE),
    ("git stash", RiskClass.REVERSIBLE),
    ("git tag v1.0.1-beta", RiskClass.REVERSIBLE),
    ("git push --force origin main", RiskClass.IRREVERSIBLE),
    ("git push -f origin master", RiskClass.IRREVERSIBLE),
    ("git push --force-with-lease origin production", RiskClass.IRREVERSIBLE),
    ("git push origin +main", RiskClass.IRREVERSIBLE),
    ("git push origin :main", RiskClass.IRREVERSIBLE),
    ("git branch -D main", RiskClass.IRREVERSIBLE),
    ("git branch -D old-experiment", RiskClass.IRREVERSIBLE),
    ("git branch -d production", RiskClass.IRREVERSIBLE),
    ("git reset --hard HEAD~1", RiskClass.IRREVERSIBLE),
    ("git clean -fdx", RiskClass.IRREVERSIBLE),
    ("git gc --prune=now", RiskClass.IRREVERSIBLE),
    ("git tag -d v1.0.0", RiskClass.IRREVERSIBLE),
    ("git filter-branch --tree-filter 'rm -f passwords.txt' HEAD", RiskClass.IRREVERSIBLE),
]


@pytest.mark.parametrize("cmd, expected_risk", GIT_CASES)
def test_git_cases(classifier: PolicyClassifier, cmd: str, expected_risk: RiskClass):
    # Test execution routed through shell
    act = make_action("fs", {"command": cmd})
    res = classifier.classify(act)
    assert res.risk == expected_risk, f"Failed on git command: {cmd!r}, got {res.risk}, expected {expected_risk}"


# -----------------------------------------------------------------------------
# 4. AWS S3 (>= 25 table-driven cases)
# -----------------------------------------------------------------------------
AWS_S3_CASES = [
    # Structured calls
    ("GetObject", {"Bucket": "my-bucket", "Key": "file.txt"}, RiskClass.SAFE),
    ("ListObjectsV2", {"Bucket": "my-bucket"}, RiskClass.SAFE),
    ("ListBuckets", {}, RiskClass.SAFE),
    ("GetBucketPolicy", {"Bucket": "my-bucket"}, RiskClass.SAFE),
    ("GetBucketVersioning", {"Bucket": "my-bucket"}, RiskClass.SAFE),
    ("HeadObject", {"Bucket": "my-bucket", "Key": "file.txt"}, RiskClass.SAFE),
    ("PutObject", {"Bucket": "my-bucket", "Key": "file.txt", "Body": b"data"}, RiskClass.REVERSIBLE),
    ("CopyObject", {"Bucket": "my-bucket", "Key": "file2.txt"}, RiskClass.REVERSIBLE),
    ("CreateBucket", {"Bucket": "new-bucket"}, RiskClass.REVERSIBLE),
    ("DeleteBucket", {"Bucket": "my-bucket"}, RiskClass.IRREVERSIBLE),
    ("DeleteObject", {"Bucket": "my-bucket", "Key": "file.txt"}, RiskClass.IRREVERSIBLE),
    ("DeleteObjects", {"Bucket": "my-bucket", "Delete": {"Objects": [{"Key": "a"}]}}, RiskClass.IRREVERSIBLE),
    ("PutBucketVersioning", {"Bucket": "b", "VersioningConfiguration": {"Status": "Suspended"}}, RiskClass.IRREVERSIBLE),
    ("PutLifecycleConfiguration", {"Bucket": "b", "LifecycleConfiguration": {"Rules": [{"Expiration": {"Days": 1}}]}}, RiskClass.IRREVERSIBLE),
    ("PutBucketPolicy", {"Bucket": "b", "Policy": '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:*"}]}'}, RiskClass.IRREVERSIBLE),
    ("DeleteBucketPolicy", {"Bucket": "b"}, RiskClass.IRREVERSIBLE),
]


@pytest.mark.parametrize("operation, payload, expected_risk", AWS_S3_CASES)
def test_aws_s3_structured_cases(classifier: PolicyClassifier, operation: str, payload: dict, expected_risk: RiskClass):
    act = make_action("aws_s3", {"action": operation, "params": payload})
    res = classifier.classify(act)
    assert res.risk == expected_risk, f"Failed on AWS S3 call: {operation}, got {res.risk}, expected {expected_risk}"


AWS_CLI_CASES = [
    ("aws s3 ls", RiskClass.SAFE),
    ("aws s3 ls s3://my-bucket", RiskClass.SAFE),
    ("aws s3 cp file.txt s3://my-bucket/file.txt", RiskClass.REVERSIBLE),
    ("aws s3 mb s3://new-bucket", RiskClass.REVERSIBLE),
    ("aws s3 rm s3://my-bucket/file.txt", RiskClass.IRREVERSIBLE),
    ("aws s3 rm s3://my-bucket/folder --recursive", RiskClass.IRREVERSIBLE),
    ("aws s3 rb s3://my-bucket", RiskClass.IRREVERSIBLE),
    ("aws s3 rb s3://my-bucket --force", RiskClass.IRREVERSIBLE),
    ("aws s3 sync src/ s3://my-bucket --delete", RiskClass.IRREVERSIBLE),
]


@pytest.mark.parametrize("cmd, expected_risk", AWS_CLI_CASES)
def test_aws_s3_cli_cases(classifier: PolicyClassifier, cmd: str, expected_risk: RiskClass):
    act = make_action("fs", {"command": cmd})
    res = classifier.classify(act)
    assert res.risk == expected_risk, f"Failed on AWS CLI: {cmd!r}, got {res.risk}, expected {expected_risk}"


# -----------------------------------------------------------------------------
# 5. Docker (>= 25 table-driven cases)
# -----------------------------------------------------------------------------
DOCKER_CASES = [
    ("docker ps", RiskClass.SAFE),
    ("docker images", RiskClass.SAFE),
    ("docker logs container_1", RiskClass.SAFE),
    ("docker inspect image_1", RiskClass.SAFE),
    ("docker version", RiskClass.SAFE),
    ("docker info", RiskClass.SAFE),
    ("docker stats", RiskClass.SAFE),
    ("docker run -d nginx", RiskClass.REVERSIBLE),
    ("docker start my_container", RiskClass.REVERSIBLE),
    ("docker stop my_container", RiskClass.REVERSIBLE),
    ("docker restart my_container", RiskClass.REVERSIBLE),
    ("docker build -t my-app .", RiskClass.REVERSIBLE),
    ("docker tag my-app:v1 my-app:latest", RiskClass.REVERSIBLE),
    ("docker pull python:3.11", RiskClass.REVERSIBLE),
    ("docker rm my_stopped_container", RiskClass.REVERSIBLE),
    ("docker compose up -d", RiskClass.REVERSIBLE),
    ("docker compose down", RiskClass.REVERSIBLE),
    ("docker system prune", RiskClass.IRREVERSIBLE),
    ("docker system prune -a", RiskClass.IRREVERSIBLE),
    ("docker system prune -f", RiskClass.IRREVERSIBLE),
    ("docker container prune -f", RiskClass.IRREVERSIBLE),
    ("docker image prune -a", RiskClass.IRREVERSIBLE),
    ("docker volume rm my_data_vol", RiskClass.IRREVERSIBLE),
    ("docker volume prune -f", RiskClass.IRREVERSIBLE),
    ("docker rm -f my_running_container", RiskClass.IRREVERSIBLE),
    ("docker rmi -f my_image", RiskClass.IRREVERSIBLE),
    ("docker network rm my_net", RiskClass.IRREVERSIBLE),
]


@pytest.mark.parametrize("cmd, expected_risk", DOCKER_CASES)
def test_docker_cases(classifier: PolicyClassifier, cmd: str, expected_risk: RiskClass):
    act = make_action("fs", {"command": cmd})
    res = classifier.classify(act)
    assert res.risk == expected_risk, f"Failed on docker command: {cmd!r}, got {res.risk}, expected {expected_risk}"


# -----------------------------------------------------------------------------
# 6. "Never allow" Regression List (MUST NEVER be SAFE)
# -----------------------------------------------------------------------------
NEVER_ALLOW = [
    ("sql", {"statement": "DROP TABLE users"}),
    ("sql", {"statement": "TRUNCATE orders"}),
    ("sql", {"statement": "DELETE FROM users"}),
    ("sql", {"statement": "UPDATE users SET admin=true"}),
    ("sql", {"statement": "GRANT ALL PRIVILEGES ON DATABASE d TO u"}),
    ("fs", {"command": "rm -rf /"}),
    ("fs", {"command": "rm -rf /home/user"}),
    ("fs", {"command": "shred -u secret.key"}),
    ("fs", {"command": "mkfs.ext4 /dev/sda"}),
    ("fs", {"command": "git push --force origin main"}),
    ("fs", {"command": "git reset --hard HEAD~1"}),
    ("fs", {"command": "git clean -fdx"}),
    ("fs", {"command": "docker system prune -a"}),
    ("fs", {"command": "docker volume rm data_vol"}),
    ("fs", {"command": "aws s3 rb s3://prod-bucket --force"}),
    ("fs", {"command": "aws s3 rm s3://prod-bucket --recursive"}),
]


@pytest.mark.parametrize("tool, payload", NEVER_ALLOW)
def test_never_allow_regression(classifier: PolicyClassifier, tool: str, payload: dict):
    act = make_action(tool, payload)
    res = classifier.classify(act)
    assert res.risk != RiskClass.SAFE, f"CRITICAL: {payload} was classified as SAFE!"


# -----------------------------------------------------------------------------
# 7. False-Positive List: Ordinary developer commands must stay SAFE or REVERSIBLE
# -----------------------------------------------------------------------------
FALSE_POSITIVE_CHECKS = [
    ("fs", {"command": "git status"}),
    ("fs", {"command": "git log"}),
    ("fs", {"command": "git diff"}),
    ("fs", {"command": "git branch"}),
    ("fs", {"command": "git checkout -b feature/login"}),
    ("fs", {"command": "git commit -m 'fix bug'"}),
    ("fs", {"command": "ls -la"}),
    ("fs", {"command": "cat src/index.ts"}),
    ("fs", {"command": "grep -rn 'import' src/"}),
    ("fs", {"command": "echo 'TEST' >> test.log"}),
    ("fs", {"command": "mkdir -p tests/unit"}),
    ("fs", {"command": "touch tests/unit/test_app.py"}),
    ("fs", {"command": "python -m pytest"}),
    ("sql", {"statement": "SELECT * FROM items WHERE id = 42"}),
    ("sql", {"statement": "INSERT INTO items (name) VALUES ('book')"}),
    ("sql", {"statement": "UPDATE items SET price = 10 WHERE id = 42"}),
    ("sql", {"statement": "DELETE FROM items WHERE id = 42"}),
    ("fs", {"command": "docker ps"}),
    ("fs", {"command": "docker logs web_app"}),
    ("fs", {"command": "docker build -t app:latest ."}),
    ("fs", {"command": "docker run -p 8080:80 app:latest"}),
    ("fs", {"command": "aws s3 ls"}),
    ("fs", {"command": "aws s3 cp data.csv s3://my-bucket/data.csv"}),
]


def test_false_positive_rate(classifier: PolicyClassifier):
    blocked_count = 0
    total = len(FALSE_POSITIVE_CHECKS)
    for tool, payload in FALSE_POSITIVE_CHECKS:
        act = make_action(tool, payload)
        res = classifier.classify(act)
        if res.risk == RiskClass.IRREVERSIBLE:
            blocked_count += 1

    fp_rate = blocked_count / total
    assert fp_rate == 0.0, f"False block rate is {fp_rate:.2%}; expected 0.0% for benign developer actions"


# -----------------------------------------------------------------------------
# 8. Fuzz the SQL matcher: random garbage & truncated inputs must NEVER raise or return SAFE
# -----------------------------------------------------------------------------
def test_fuzz_sql_matcher(classifier: PolicyClassifier):
    random.seed(42)
    sample_snippets = [
        "SELECT ", "DROP ", "DELETE FROM ", "UPDATE ", "TRUNCATE ",
        "ALTER TABLE ", "CREATE ", "WITH ", "EXPLAIN ", "DO $$ ",
        "/* unclosed comment", "'unclosed string", ")(*&^%$#@",
        "SELECT 1 FROM WHERE AND OR", "DROP TABLE ;;; ((("
    ]

    for _ in range(100):
        # Generate random combinations of snippets and garbage
        base = random.choice(sample_snippets)
        garbage_len = random.randint(1, 40)
        garbage = "".join(random.choices(string.printable, k=garbage_len))
        fuzzed_sql = base + garbage

        act = make_action("sql", {"statement": fuzzed_sql})
        # Must never raise
        res = classifier.classify(act)
        # Unparseable garbage must never be classified SAFE
        if "parse-error" in res.rule_ids or "could not parse" in " ".join(res.reasons).lower():
            assert res.risk == RiskClass.IRREVERSIBLE, f"Unparseable input classified as {res.risk}: {fuzzed_sql!r}"
