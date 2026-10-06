"""Docker and Kubernetes fact extraction from argv."""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING, Any

from .shell_fs import parse_flags

if TYPE_CHECKING:
    from . import Facts

DOCKER_FACT_KEYS = {"subcommand", "flags", "positionals", "force", "all", "volumes", "args"}
K8S_FACT_KEYS = {"verb", "kind", "kinds", "names", "flags", "all", "replicas", "production",
                 "namespace", "context", "from_file", "args", "subverb"}

_DOCKER_GLOBAL_WITH_VALUE = {"--context", "-c", "-H", "--host", "--config", "--log-level", "-l",
                             "--tlscacert", "--tlscert", "--tlskey"}
_DOCKER_ALIASES = {
    "container rm": "rm", "container kill": "kill", "container prune": "container prune",
    "container stop": "stop", "container start": "start", "container ls": "ps",
    "container list": "ps", "container run": "run", "container exec": "exec",
    "image rm": "rmi", "image ls": "images", "image list": "images",
    "network rm": "network rm", "volume remove": "volume rm",
    "compose rm": "compose rm",
}
_DOCKER_GROUPS = {"container", "image", "volume", "network", "system", "builder", "compose",
                  "buildx", "context", "plugin", "secret", "service", "stack", "swarm", "node",
                  "config", "manifest", "trust"}


def docker_from_argv(prog: str, args: list[str]) -> Facts:
    if prog == "docker-compose":
        args = ["compose", *args]
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if (args[i] in _DOCKER_GLOBAL_WITH_VALUE and "=" not in args[i]) else 1
    rest = args[i:]
    if not rest:
        return {"subcommand": "", "args": args, "flags": [], "positionals": []}
    words = [rest[0].lower()]
    tail = rest[1:]
    if words[0] in _DOCKER_GROUPS:
        # Skip compose-level options like `-f file` / `-p project`.
        j = 0
        while j < len(tail) and tail[j].startswith("-"):
            j += 2 if tail[j] in ("-f", "--file", "-p", "--project-name", "--profile",
                                  "--env-file", "--project-directory") else 1
        if j < len(tail):
            words.append(tail[j].lower())
            tail = tail[j + 1 :]
        else:
            tail = []
    sub = " ".join(words)
    sub = _DOCKER_ALIASES.get(sub, sub)
    flags, pos = parse_flags(tail)
    return {
        "subcommand": sub,
        "args": tail,
        "flags": sorted(flags),
        "positionals": pos,
        "force": bool({"f", "force"} & flags),
        "all": bool({"a", "all"} & flags),
        "volumes": bool({"v", "volumes"} & flags),
    }


_K8S_KIND_ALIASES = {
    "ns": "namespace", "namespaces": "namespace", "pv": "persistentvolume",
    "persistentvolumes": "persistentvolume", "pvc": "persistentvolumeclaim",
    "persistentvolumeclaims": "persistentvolumeclaim", "po": "pod", "pods": "pod",
    "deploy": "deployment", "deployments": "deployment", "svc": "service", "services": "service",
    "sts": "statefulset", "statefulsets": "statefulset", "ds": "daemonset",
    "daemonsets": "daemonset", "rs": "replicaset", "replicasets": "replicaset",
    "crd": "customresourcedefinition", "crds": "customresourcedefinition",
    "customresourcedefinitions": "customresourcedefinition", "secrets": "secret",
    "cm": "configmap", "configmaps": "configmap", "no": "node", "nodes": "node",
    "sc": "storageclass", "storageclasses": "storageclass", "jobs": "job", "cronjobs": "cronjob",
    "cj": "cronjob", "ing": "ingress", "ingresses": "ingress", "sa": "serviceaccount",
    "clusterroles": "clusterrole", "clusterrolebindings": "clusterrolebinding",
    "roles": "role", "rolebindings": "rolebinding",
}
_K8S_GLOBAL_WITH_VALUE = {"-n", "--namespace", "--context", "--kubeconfig", "--cluster", "--user",
                          "-s", "--server", "--token", "--as", "--as-group", "-l", "--selector",
                          "-o", "--output", "-f", "--filename", "-c", "--container",
                          "--field-selector", "--grace-period", "--timeout", "-k", "--kustomize"}
DEFAULT_PRODUCTION_PATTERNS = ["prod", "prod-*", "*-prod", "production", "production-*", "*-production"]


def _kind(tok: str) -> str:
    base = tok.split("/", 1)[0].split(".", 1)[0].lower()
    return _K8S_KIND_ALIASES.get(base, base)


def k8s_from_argv(args: list[str], params: dict[str, Any] | None = None) -> Facts:
    params = params or {}
    prod_patterns = list(params.get("production_patterns") or DEFAULT_PRODUCTION_PATTERNS)
    if "--" in args:
        args = args[: args.index("--")]
    namespace = context = None
    replicas: int | None = None
    from_file = False
    positionals: list[str] = []
    flag_names: set[str] = set()
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("-"):
            name, _, inline = a.partition("=")
            value = inline if inline else (args[i + 1] if i + 1 < len(args) else "")
            consumed = name in _K8S_GLOBAL_WITH_VALUE or name == "--replicas"
            if name in ("-n", "--namespace"):
                namespace = value
            elif name == "--context":
                context = value
            elif name in ("-f", "--filename", "-k", "--kustomize"):
                from_file = True
            elif name == "--replicas":
                try:
                    replicas = int(value)
                except ValueError:
                    replicas = None
            flag_names.add(name.lstrip("-"))
            if name in ("-A",):
                flag_names.add("all-namespaces")
            i += 1 if inline or not consumed else 2
            continue
        positionals.append(a)
        i += 1
    verb = positionals[0].lower() if positionals else ""
    rest = positionals[1:]
    subverb = ""
    if verb in ("rollout", "config", "auth", "certificate", "set", "create") and rest:
        subverb = rest[0].lower()
        rest = rest[1:]
    kinds: list[str] = []
    names: list[str] = []
    if rest:
        if "/" in rest[0]:
            for r in rest:
                kinds.append(_kind(r))
                names.append(r.split("/", 1)[1] if "/" in r else r)
        else:
            kinds = [_kind(k) for k in rest[0].split(",")]
            names = rest[1:]
    def is_prod(v: str | None) -> bool:
        return bool(v) and any(fnmatch.fnmatchcase(str(v).lower(), p) for p in prod_patterns)

    production = is_prod(namespace) or is_prod(context) or (
        verb == "delete" and "namespace" in kinds and any(is_prod(n) for n in names)
    )
    return {
        "verb": verb,
        "subverb": subverb,
        "kind": kinds[0] if kinds else "",
        "kinds": kinds,
        "names": names,
        "flags": sorted(flag_names),
        "all": bool({"all", "all-namespaces", "A"} & flag_names),
        "replicas": replicas,
        "namespace": namespace,
        "context": context,
        "production": production,
        "from_file": from_file,
        "args": args,
    }
