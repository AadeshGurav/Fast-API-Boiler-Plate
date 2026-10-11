from lib import MONO, label_side, legend, node, path

SLUG = "ci-pipeline"
EYEBROW = "Process · for contributors and reviewers"
TITLE = "Every pull request clears four independent gates"
DESC = ("Continuous integration: each push or pull request runs four jobs in parallel: lint and tests on "
        "Python 3.11 and 3.13 with coverage and API fuzzing, after checking that uv.lock and its exports are current; the backend contract suite against real MongoDB, PostgreSQL and "
        "Redis; pip-audit over the whole locked dependency tree; and a Docker image build scanned by Trivy. All four "
        "must pass to merge; after a merge to develop a separate workflow refreshes the code graph.")
W, H = 960, 520

JOBS = [  # x, name, sub, tag
    (48, "Tests", "3.11 · 3.13 · lint · fuzz", "JOB"),
    (272, "Contract", "MongoDB · PostgreSQL · Redis", "JOB"),
    (496, "Audit", "pip-audit · whole uv.lock", "JOB"),
    (720, "Image", "docker build · Trivy", "JOB"),
]


def body():
    b = []
    for x, *_ in JOBS:
        cx = x + 96
        b.append(path(f"M {cx},104 V 166", "link"))
        b.append(path(f"M {cx},240 V 302"))
    b.append(path("M 480,360 V 414", "dashed"))
    b.append(label_side(144, 136, "PARALLEL", "link"))
    b.append(label_side(144, 272, "MUST PASS"))
    b.append(label_side(480, 388, "ON DEVELOP", "dashed"))
    b.append(node(48, 48, 864, 56, "Push or pull request", "uv sync --frozen · lock and exports checked · make lint, test, fuzz", "GIT", "input"))
    for x, name, sub, tag in JOBS:
        b.append(node(x, 168, 192, 72, name, sub, tag))
    b.append(node(48, 304, 864, 56, "Ready to merge", "branch protection: all four jobs green", "GATE", "focal"))
    b.append(node(320, 416, 320, 48, "graph.yml", "refreshes graphify-out/ after the merge", "BOT", "optional"))
    b.append(legend(488, W, [("link", "trigger"), ("muted", "result"), ("dashed", "after merge"),
                             ("focal", "the gate"), ("optional", "housekeeping")]))
    return "".join(b)
