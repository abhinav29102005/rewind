from rewind.classifier.engine import ActionRequest, ActionRisk, ClassificationEngine
from rewind.classifier.rules import RuleClassifier


def test_safe_commands() -> None:
    classifier = RuleClassifier()
    engine = ClassificationEngine([classifier])

    safe_commands = [
        "ls -la",
        "cat /etc/passwd",
        "SELECT * FROM users",
        "git status",
        "echo 'hello'"
    ]

    for cmd in safe_commands:
        action = ActionRequest(tool_name="shell", method="exec", raw_command=cmd)
        result = engine.classify(action)
        assert result.risk == ActionRisk.SAFE, f"Expected {cmd} to be SAFE, got {result.risk}"

def test_irreversible_commands() -> None:
    classifier = RuleClassifier()
    engine = ClassificationEngine([classifier])

    irreversible_commands = [
        "DROP TABLE users",
        "rm -rf /",
        "git push --force origin main",
        "docker rm container_id"
    ]

    for cmd in irreversible_commands:
        action = ActionRequest(tool_name="shell", method="exec", raw_command=cmd)
        result = engine.classify(action)
        assert result.risk == ActionRisk.IRREVERSIBLE, f"Expected {cmd} to be IRREVERSIBLE, got {result.risk}"

def test_reversible_commands() -> None:
    classifier = RuleClassifier()
    engine = ClassificationEngine([classifier])

    reversible_commands = [
        "UPDATE users SET name='test'",
        "INSERT INTO users VALUES(1)",
        "cp file1 file2",
        "git commit -m 'test'"
    ]

    for cmd in reversible_commands:
        action = ActionRequest(tool_name="shell", method="exec", raw_command=cmd)
        result = engine.classify(action)
        assert result.risk == ActionRisk.REVERSIBLE, f"Expected {cmd} to be REVERSIBLE, got {result.risk}"

def test_failsafe() -> None:
    engine = ClassificationEngine() # Empty engine, no rules
    action = ActionRequest(tool_name="unknown", method="unknown", raw_command="unknown command")
    result = engine.classify(action)
    assert result.risk == ActionRisk.IRREVERSIBLE
    assert result.matched_rule == "__fail_safe__"
