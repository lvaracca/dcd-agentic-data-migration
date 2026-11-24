#!/usr/bin/env python3
"""
Deploys local `gcp-target/dataform/` files into a real Google Cloud Dataform
Repository & Workspace (`us-central1`), compiles the DAG, executes a full
Workflow Invocation (including Dataform assertions), and prints every action's
status so the Compiled Graph is live in BigQuery Studio!
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

DATAFORM_DIR = Path(__file__).resolve().parent
ROOT_DIR = DATAFORM_DIR.parents[1]


def get_access_token() -> str:
    env = os.environ.copy()
    env["CLOUDSDK_METRICS_ENVIRONMENT"] = (
        f"{env.get('CLOUDSDK_METRICS_ENVIRONMENT', '')} datacloud.antigravity".strip()
    )
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True, env=env
    ).strip()


def df_api(method: str, url: str, token: str, body: dict | None = None, project_id: str | None = None) -> dict:
    cmd = [
        "curl", "-sS", "-w", "\n%{http_code}", "-X", method,
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
    ]
    if project_id:
        cmd += ["-H", f"x-goog-user-project: {project_id}"]
    if body is not None:
        cmd += ["--data-binary", "@-"]
    cmd.append(url)
    res = subprocess.run(
        cmd,
        input=json.dumps(body) if body is not None else None,
        text=True,
        capture_output=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"curl failed on {method} {url}: {res.stderr}")
    raw, code_str = res.stdout.rsplit("\n", 1)
    code = int(code_str.strip())
    if code >= 400:
        raise RuntimeError(f"HTTP {code} {method} {url}: {raw}")
    return json.loads(raw) if raw.strip() else {}


def ensure_dataform_iam(project_id: str) -> None:
    env = os.environ.copy()
    env["CLOUDSDK_METRICS_ENVIRONMENT"] = (
        f"{env.get('CLOUDSDK_METRICS_ENVIRONMENT', '')} datacloud.antigravity".strip()
    )
    proj_num = subprocess.check_output(
        ["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"],
        text=True,
        env=env,
    ).strip()
    sa = f"service-{proj_num}@gcp-sa-dataform.iam.gserviceaccount.com"
    exec_sa = f"quickbite-airbyte-sa@{project_id}.iam.gserviceaccount.com"
    for role in ("roles/bigquery.admin", "roles/storage.objectViewer"):
        subprocess.run(
            [
                "gcloud", "projects", "add-iam-policy-binding", project_id,
                f"--member=serviceAccount:{sa}",
                f"--role={role}",
                "--condition=None",
            ],
            check=False,
            capture_output=True,
            env=env,
        )
    # Allow Dataform service agent to act-as exec_sa (Argolis strict actAs compliance)
    for role in ("roles/iam.serviceAccountTokenCreator", "roles/iam.serviceAccountUser"):
        subprocess.run(
            [
                "gcloud", "iam", "service-accounts", "add-iam-policy-binding", exec_sa,
                f"--project={project_id}",
                f"--member=serviceAccount:{sa}",
                f"--role={role}",
                "--condition=None",
            ],
            check=False,
            capture_output=True,
            env=env,
        )
    return exec_sa


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_REGION", "us-central1")
    repo_id = "quickbite-lakehouse-dag"
    ws_id = "dev-antigravity"

    exec_sa = ensure_dataform_iam(project_id)
    token = get_access_token()
    base = f"https://dataform.googleapis.com/v1beta1/projects/{project_id}/locations/{region}"
    repo_name = f"projects/{project_id}/locations/{region}/repositories/{repo_id}"
    ws_name = f"{repo_name}/workspaces/{ws_id}"

    # 1. Create repository if missing
    try:
        df_api("GET", f"{base}/repositories/{repo_id}", token, project_id=project_id)
        print(f"[1/5] Dataform repository '{repo_id}' already exists.")
    except RuntimeError:
        df_api("POST", f"{base}/repositories?repositoryId={repo_id}", token, {"displayName": "QuickBite Lakehouse DAG"}, project_id=project_id)
        print(f"[1/5] Created Dataform repository '{repo_id}' in {region}.")

    # 2. Create workspace if missing
    try:
        df_api("GET", f"{base}/repositories/{repo_id}/workspaces/{ws_id}", token, project_id=project_id)
        print(f"[2/5] Dataform workspace '{ws_id}' already exists.")
    except RuntimeError:
        df_api("POST", f"{base}/repositories/{repo_id}/workspaces?workspaceId={ws_id}", token, {}, project_id=project_id)
        print(f"[2/5] Created Dataform workspace '{ws_id}'.")

    # 3. Upload all local Dataform files (workflow_settings.yaml, package.json, definitions/*)
    print("[3/5] Syncing local Dataform .sqlx / .js / .yaml files to GCP Workspace...")
    files_to_push = [
        p for p in sorted(DATAFORM_DIR.rglob("*"))
        if p.is_file() and p.name != Path(__file__).name and not p.name.startswith(".")
    ]
    for fp in files_to_push:
        rel = fp.relative_to(DATAFORM_DIR).as_posix()
        b64 = base64.b64encode(fp.read_bytes()).decode()
        df_api(
            "POST",
            f"https://dataform.googleapis.com/v1beta1/{ws_name}:writeFile",
            token,
            {"path": rel, "contents": b64},
            project_id=project_id,
        )
        print(f"      -> uploaded {rel}")

    # Remove legacy package.json if present (Dataform 3.x uses dataformCoreVersion in workflow_settings.yaml)
    try:
        df_api(
            "POST",
            f"https://dataform.googleapis.com/v1beta1/{ws_name}:removeFile",
            token,
            {"path": "package.json"},
            project_id=project_id,
        )
    except RuntimeError:
        pass

    # 4. Compile DAG
    print("[4/5] Compiling Dataform DAG in GCP...")
    comp = df_api(
        "POST",
        f"https://dataform.googleapis.com/v1beta1/{repo_name}/compilationResults",
        token,
        {"workspace": ws_name},
        project_id=project_id,
    )
    comp_name = comp["name"]
    comp_errs = comp.get("compilationErrors", [])
    if comp_errs:
        print("COMPILATION ERRORS:", json.dumps(comp_errs, indent=2), file=sys.stderr)
        sys.exit(1)

    actions = df_api(
        "GET",
        f"https://dataform.googleapis.com/v1beta1/{comp_name}:query",
        token,
        project_id=project_id,
    ).get("compilationResultActions", [])
    print(f"      ✅ Compiled cleanly with 0 errors! ({len(actions)} DAG actions)")

    # 5. Execute Workflow Invocation
    print("[5/5] Executing Dataform Workflow Invocation on BigQuery...")
    inv = df_api(
        "POST",
        f"https://dataform.googleapis.com/v1beta1/{repo_name}/workflowInvocations",
        token,
        {
            "compilationResult": comp_name,
            "invocationConfig": {
                "serviceAccount": exec_sa,
                "transitiveDependenciesIncluded": True,
            },
        },
        project_id=project_id,
    )
    inv_name = inv["name"]
    for _ in range(90):
        time.sleep(3)
        st = df_api("GET", f"https://dataform.googleapis.com/v1beta1/{inv_name}", token, project_id=project_id)
        state = st.get("state")
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            inv_actions = df_api(
                "GET",
                f"https://dataform.googleapis.com/v1beta1/{inv_name}:query",
                token,
                project_id=project_id,
            ).get("workflowInvocationActions", [])
            for a in inv_actions:
                t = a.get("target", {})
                print(f"      [{a.get('state'):<10}] {t.get('schema')}.{t.get('name')} {a.get('failureReason', '')}")
            if state != "SUCCEEDED":
                print(f"❌ Dataform Workflow Invocation ended with state={state}", file=sys.stderr)
                sys.exit(1)
            print(f"\n✅ Dataform DAG SUCCEEDED! View Compiled Graph in BigQuery Studio -> Dataform -> {repo_id} ({ws_id})")
            return
    print("Timed out waiting for Dataform Workflow Invocation.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
