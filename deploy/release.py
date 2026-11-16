"""Manager-side exact-main Clockin release. Never prints runtime credentials."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

SERVICE = "employee_activity_tracker"
REPOSITORY = "ardzix/employee_activity_tracker"
SOURCE = Path("/root/Project/employee_daily_activity")


def run(args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, timeout=900, **kwargs)
    if result.returncode:
        # Docker diagnostics can echo secret-valued command arguments. Preserve
        # them privately; the console receives only the failed program name.
        raise RuntimeError("Release gate failed: " + args[0])
    return result.stdout


def save(path, value):
    path.write_text(json.dumps(value, indent=2))
    path.chmod(0o600)


def service():
    return json.loads(run(["docker", "service", "inspect", SERVICE]))[0]


def containers():
    return run(["docker", "ps", "--filter", "label=com.docker.swarm.service.name=" + SERVICE, "--format", "{{.ID}}"]).splitlines()


def wait_task(name):
    for _ in range(90):
        ids = run(["docker", "service", "ps", "-q", name]).splitlines()
        if ids:
            task = json.loads(run(["docker", "inspect", ids[0]]))[0]["Status"]
            if task["State"] == "complete" and task.get("ContainerStatus", {}).get("ExitCode") == 0:
                return
            if task["State"] in ("failed", "rejected", "shutdown"):
                raise RuntimeError("Clockin migration failed; rollout was not started")
        time.sleep(2)
    raise RuntimeError("Clockin migration timed out")


def build(commit, folder):
    if not SOURCE.exists():
        run(["git", "clone", "https://github.com/ardzix/employee_daily_activity.git", str(SOURCE)])
    run(["git", "-C", str(SOURCE), "fetch", "origin", "main"])
    if run(["git", "-C", str(SOURCE), "rev-parse", "origin/main"]).strip() != commit:
        raise RuntimeError("Release must use the exact remote main commit")
    if (folder / "release.json").exists():
        raise RuntimeError("Release already exists; inspect it before retrying")
    with tempfile.TemporaryDirectory(prefix="clockin-build-") as temporary:
        context = Path(temporary)
        archive = subprocess.check_output(["git", "-C", str(SOURCE), "archive", commit])
        import io
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(context, filter="data")
        tag = REPOSITORY + ":central-" + commit[:12]
        run(["docker", "build", "--label", "org.opencontainers.image.revision=" + commit, "-t", tag, str(context)])
        checks = run(["docker", "run", "--rm", "--network", "none", "-e", "USE_POSTGRES=False", "-e", "DEBUG=False",
                      "-e", "SECRET_KEY=isolated-clockin-test-only", "--entrypoint", "python", tag,
                      "manage.py", "test", "authentication.test_central_sso", "--settings=employee_activity_tracker.test_settings"])
        run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python", tag,
             "-m", "unittest", "discover", "-s", "deploy/tests", "-v"])
        with tempfile.TemporaryDirectory(prefix="clockin-registry-") as auth:
            registry = Path.home() / ".docker/config.json"
            if not registry.exists():
                raise RuntimeError("The manager registry credential is unavailable")
            shutil.copy2(registry, Path(auth) / "config.json")
            run(["docker", "--config", auth, "push", tag])
            run(["docker", "--config", auth, "pull", tag])
        image = json.loads(run(["docker", "image", "inspect", tag]))[0]
        digest = next(value for value in image["RepoDigests"] if value.startswith(REPOSITORY + "@sha256:"))
        if image["Config"].get("Labels", {}).get("org.opencontainers.image.revision") != commit:
            raise RuntimeError("Clockin image provenance mismatch")
        save(folder / "release.json", {"commit": commit, "digest": digest, "tests": "passed", "status": "published"})
        print(json.dumps({"commit": commit, "digest": digest, "tests": "passed", "status": "published"}), flush=True)


def roll(commit, folder):
    record = json.loads((folder / "release.json").read_text())
    if record["commit"] != commit or record["tests"] != "passed":
        raise RuntimeError("Wrong or untested Clockin release")
    old = service()
    save(folder / "previous-service.json", old)
    cs = old["Spec"]["TaskTemplate"]["ContainerSpec"]
    running = containers()
    if len(running) != 1:
        raise RuntimeError("Expected one baseline Clockin replica")
    runtime = dict(item.split("=", 1) for item in cs.get("Env", []) if "=" in item)
    if "CLOCKIN_RUNTIME_SECRET_PATH" in runtime:
        runtime = json.loads(run(["docker", "exec", running[0], "cat", "/run/secrets/clockin_runtime"]))
    if not runtime.get("SECRET_KEY") or not all(runtime.get(key) for key in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")):
        raise RuntimeError("Existing full Clockin runtime configuration is incomplete")
    if runtime.get("USE_POSTGRES", "").lower() != "true":
        raise RuntimeError("Review persistent SQLite storage before rolling Clockin")
    keypath = runtime.get("SSO_PUBLIC_KEY_PATH", "public.pem")
    if not keypath.startswith("/"):
        keypath = "/usr/src/app/" + keypath
    public_key = run(["docker", "exec", running[0], "cat", keypath])
    if "BEGIN PUBLIC KEY" not in public_key:
        raise RuntimeError("Existing SSO public key is invalid")
    runtime.update(DEBUG="False", SSO_PUBLIC_KEY_PATH="/run/secrets/clockin_sso_public",
                   PUBLIC_SITE_URL="https://clockin.arnatech.id")
    suffix = commit[:12] + "-" + os.urandom(4).hex()
    secrets = {"runtime": "clockin-runtime-" + suffix, "public": "clockin-sso-public-" + suffix}
    run(["docker", "secret", "create", secrets["runtime"], "-"], input=json.dumps(runtime))
    run(["docker", "secret", "create", secrets["public"], "-"], input=public_key)
    options = ["--network", "production", "--env", "CLOCKIN_RUNTIME_SECRET_PATH=/run/secrets/clockin_runtime",
               "--secret", "source=" + secrets["runtime"] + ",target=clockin_runtime,mode=0400",
               "--secret", "source=" + secrets["public"] + ",target=clockin_sso_public,mode=0400"]
    migration = "clockin-migrate-" + suffix
    try:
        run(["docker", "service", "create", "--detach=true", "--name", migration, "--restart-condition", "none",
             "--entrypoint", "python", *options, record["digest"], "manage.py", "migrate", "--noinput"])
        wait_task(migration)
        record["migration"] = "complete_exit_0"
        save(folder / "release.json", record)
    finally:
        subprocess.run(["docker", "service", "rm", migration], capture_output=True)
    update = ["docker", "service", "update", "--with-registry-auth", "--image", record["digest"],
              "--update-parallelism", "1", "--update-order", "stop-first", "--update-monitor", "30s",
              "--update-failure-action", "rollback", "--rollback-order", "stop-first", "--stop-grace-period", "45s",
              "--health-cmd", "python /usr/src/app/deploy/healthcheck.py", "--health-interval", "15s",
              "--health-timeout", "6s", "--health-retries", "3", "--health-start-period", "45s"]
    for value in cs.get("Env", []):
        update += ["--env-rm", value.split("=", 1)[0]]
    for item in cs.get("Secrets", []):
        if item["File"]["Name"] not in ("clockin_runtime", "clockin_sso_public"):
            raise RuntimeError("Unknown Clockin secret target; review before rollout")
        update += ["--secret-rm", item["SecretName"]]
    update += ["--env-add", "CLOCKIN_RUNTIME_SECRET_PATH=/run/secrets/clockin_runtime"]
    for name, target in [("runtime", "clockin_runtime"), ("public", "clockin_sso_public")]:
        update += ["--secret-add", "source=" + secrets[name] + ",target=" + target + ",mode=0400"]
    run([*update, SERVICE])
    record.update(status="deployed", secrets=secrets, public_key_fingerprint=hashlib.sha256(public_key.encode()).hexdigest())
    save(folder / "release.json", record)
    verify(commit, folder)


def verify(commit, folder):
    record = json.loads((folder / "release.json").read_text())
    for _ in range(60):
        live = service()
        state = live.get("UpdateStatus", {}).get("State")
        if state in ("paused", "rollback_started", "rollback_completed"):
            raise RuntimeError("Clockin release failed or rolled back")
        running = containers()
        if state == "completed" and len(running) == 1:
            c = json.loads(run(["docker", "inspect", running[0]]))[0]
            if c["State"].get("Health", {}).get("Status") == "healthy":
                break
        time.sleep(3)
    else:
        raise RuntimeError("Clockin rollout did not converge")
    if live["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"] != record["digest"]:
        raise RuntimeError("Wrong Clockin digest")
    from urllib.request import urlopen
    with urlopen("https://clockin.arnatech.id/health/ready", timeout=15) as response:
        if response.status != 200:
            raise RuntimeError("Public Clockin readiness failed")
    record.update(status="verified", replicas_healthy=1)
    save(folder / "release.json", record)
    print(json.dumps({key: record[key] for key in ("commit", "digest", "status", "replicas_healthy")}), flush=True)


if __name__ == "__main__":
    mode, commit = sys.argv[1:]
    if mode not in {"build", "roll", "verify"} or not re.fullmatch("[0-9a-f]{40}", commit):
        raise SystemExit("Expected {build,roll,verify} FULL_MAIN_SHA")
    folder = Path("/root/arnatech-releases/clockin-" + commit[:12])
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    globals()[mode](commit, folder)
