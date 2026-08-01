//! Cloud Tasks → atlas-distill Cloud Run Job dispatcher.
//!
//! The queue `atlas-distill-jobs` (us-central1) targets this service. We:
//!   1. validate the Cloud Tasks OIDC `Authorization` bearer token
//!   2. parse the task envelope
//!   3. invoke `projects.locations.jobs.run` for the `atlas-distill` Cloud Run Job
//!      with container overrides carrying `command` + `args` + `--beat-emit-url`
//!   4. return 200 once the Job RUN is accepted (we don't wait for completion)
//!
//! See unit-08 of the handoff plan and docs/handoff/03_gcp_heavy_workload_blueprint.md.

use std::net::SocketAddr;
use std::sync::Arc;

use axum::{
    extract::State,
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use clap::Parser;
use serde::{Deserialize, Serialize};
use tracing::{error, info, warn};

mod auth;
mod budget;
mod catalog;
mod jobrun;

use auth::{verify_oidc, OidcVerifier};
use jobrun::{run_job, JobRunner, RealJobRunner};

#[derive(Parser, Debug, Clone)]
#[command(version, about = "Cloud Tasks consumer for atlas-distill")]
struct Cli {
    /// Port to bind. Cloud Run injects $PORT.
    #[arg(long, env = "PORT", default_value_t = 8080)]
    port: u16,

    /// Public URL of this service (Cloud Run injects via env). Used as expected `aud` in OIDC.
    #[arg(long, env = "SERVICE_URL")]
    service_url: Option<String>,

    /// GCP project id.
    #[arg(long, env = "GCP_PROJECT_ID", default_value = "shed-489901")]
    project_id: String,

    /// Cloud Run region.
    #[arg(long, env = "GCP_REGION", default_value = "us-central1")]
    region: String,

    /// Name of the Cloud Run Job to trigger.
    #[arg(long, env = "TARGET_JOB", default_value = "atlas-distill")]
    target_job: String,

    /// Runtime backend catalog. Supports a local path, https://, or gs:// URL.
    #[arg(
        long,
        env = "BACKEND_CATALOG_URL",
        default_value = "gs://shed-489901-atlas-inputs/mlip-policies/backend_catalog.json"
    )]
    backend_catalog_url: String,

    /// Runtime policy directory. Supports a local directory or gs:// prefix.
    #[arg(
        long,
        env = "SCHEDULE_POLICY_URL",
        default_value = "gs://shed-489901-atlas-inputs/mlip-policies"
    )]
    schedule_policy_url: String,

    /// Atomic schedule reservation ledgers (one generation-matched object/day).
    #[arg(
        long,
        env = "BUDGET_LEDGER_URL",
        default_value = "gs://shed-489901-atlas-inputs/mlip-budget-ledgers"
    )]
    budget_ledger_url: String,

    /// Skip OIDC verification and use a no-op job runner. For local E2E only.
    #[arg(long, env = "DEV_MODE", default_value_t = false)]
    dev_mode: bool,
}

/// Cloud Tasks envelope. Matches the body the dispatcher writes on the Cloudflare side.
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct TaskPayload {
    pub fixture_url: String,
    pub command: String,
    #[serde(default)]
    pub args: Vec<String>,
    pub beat_emit_url: String,
    #[serde(default)]
    pub target_job: Option<String>,
    #[serde(default)]
    pub schedule_name: Option<String>,
}

#[derive(Debug, Serialize)]
struct RunResponse {
    accepted: bool,
    operation_name: Option<String>,
    reason: Option<String>,
    schedule: Option<String>,
    reserved_gpu_hours: Option<f64>,
    daily_gpu_hour_cap: Option<f64>,
}

#[derive(Clone)]
struct AppState {
    cfg: Arc<Cli>,
    verifier: Arc<dyn OidcVerifier>,
    runner: Arc<dyn JobRunner>,
    budget_ledger: Arc<dyn budget::BudgetLedger>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,tasks_consumer=debug".into()),
        )
        .with_target(false)
        .json()
        .init();

    let cli = Cli::parse();
    let app = build_app(cli.clone()).await?;
    let addr = SocketAddr::from(([0, 0, 0, 0], cli.port));
    info!(
        port = cli.port,
        dev_mode = cli.dev_mode,
        "tasks-consumer listening"
    );
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;
    Ok(())
}

async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
    info!("shutdown signal received");
}

async fn build_app(cli: Cli) -> anyhow::Result<Router> {
    let verifier: Arc<dyn OidcVerifier> = if cli.dev_mode {
        Arc::new(auth::DevModeVerifier)
    } else {
        Arc::new(auth::GoogleJwksVerifier::new().await?)
    };
    let runner: Arc<dyn JobRunner> = if cli.dev_mode {
        Arc::new(jobrun::DevModeJobRunner)
    } else {
        Arc::new(RealJobRunner::new()?)
    };
    let budget_ledger: Arc<dyn budget::BudgetLedger> = if cli.dev_mode {
        budget::memory_ledger()
    } else {
        Arc::new(budget::GcsBudgetLedger::from_url(&cli.budget_ledger_url)?)
    };
    let state = AppState {
        cfg: Arc::new(cli),
        verifier,
        runner,
        budget_ledger,
    };
    Ok(Router::new()
        .route("/healthz", get(|| async { "ok" }))
        .route("/run", post(handle_run))
        .with_state(state))
}

async fn handle_run(
    State(state): State<AppState>,
    headers: HeaderMap,
    body: axum::body::Bytes,
) -> impl IntoResponse {
    let payload: TaskPayload = match serde_json::from_slice(&body) {
        Ok(p) => p,
        Err(e) => {
            warn!(error = %e, "invalid task payload");
            return (StatusCode::BAD_REQUEST, format!("invalid payload: {e}")).into_response();
        }
    };

    let task_name = headers
        .get("x-cloudtasks-taskname")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("(unknown)");

    let target_job = payload
        .target_job
        .as_deref()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or(&state.cfg.target_job)
        .trim()
        .to_string();
    let catalog = match catalog::load_catalog(&state.cfg.backend_catalog_url).await {
        Ok(catalog) => catalog,
        Err(e) => {
            error!(task = task_name, error = %e, "backend catalog unavailable");
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                format!("backend catalog unavailable: {e}"),
            )
                .into_response();
        }
    };
    let mut allowed = catalog.jobs.clone();
    // The control-plane job is not an MLIP backend and therefore remains an
    // explicit singleton. Every mlip-cell-* target comes from the live catalog.
    allowed.insert(state.cfg.target_job.clone());
    if !allowed.contains(&target_job) {
        warn!(task = task_name, target_job = %target_job, allowed = ?allowed, "target job rejected");
        return (
            StatusCode::BAD_REQUEST,
            format!("target_job not allowed: {target_job}"),
        )
            .into_response();
    }

    if !state.cfg.dev_mode {
        match verify_oidc(
            state.verifier.as_ref(),
            &headers,
            state.cfg.service_url.as_deref(),
        )
        .await
        {
            Ok(claims) => info!(task = task_name, sub = %claims.sub, "oidc verified"),
            Err(e) => {
                warn!(task = task_name, error = %e, "oidc verification failed");
                return (StatusCode::UNAUTHORIZED, format!("unauthorized: {e}")).into_response();
            }
        }
    }

    let retry_count = headers
        .get("x-cloudtasks-taskretrycount")
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.parse::<u32>().ok())
        .unwrap_or(0);
    let owner_noted_manual = headers
        .get("x-lupine-owner-note")
        .and_then(|value| value.to_str().ok())
        .is_some_and(|value| !value.trim().is_empty());
    let backend = catalog.backend_by_job.get(&target_job).map(String::as_str);
    let mut admission = None;
    if backend.is_some() {
        match payload.schedule_name.as_deref() {
            Some("manual") if owner_noted_manual => {
                info!(
                    task = task_name,
                    "explicit owner-noted manual dispatch excluded from schedule ledger"
                );
            }
            Some("manual") | None => {
                return (
                    StatusCode::BAD_REQUEST,
                    "MLIP dispatch requires schedule_name, or manual plus x-lupine-owner-note"
                        .to_string(),
                )
                    .into_response();
            }
            Some(schedule) => {
                let policy =
                    match budget::load_policy(&state.cfg.schedule_policy_url, schedule).await {
                        Ok(policy) => policy,
                        Err(error) => {
                            error!(task = task_name, error = %error, "schedule policy unavailable");
                            return (
                                StatusCode::SERVICE_UNAVAILABLE,
                                format!("schedule policy unavailable: {error:#}"),
                            )
                                .into_response();
                        }
                    };
                if let Err(error) = policy.validate(backend) {
                    return (
                        StatusCode::BAD_REQUEST,
                        format!("schedule admission rejected: {error}"),
                    )
                        .into_response();
                }
                if retry_count > 0 {
                    warn!(
                        task = task_name,
                        schedule, retry_count, "no-silent-retry policy rejected Cloud Tasks retry"
                    );
                    return (
                        StatusCode::OK,
                        Json(RunResponse {
                            accepted: false,
                            operation_name: None,
                            reason: Some("cloud_tasks_retry_rejected_by_policy".into()),
                            schedule: Some(schedule.into()),
                            reserved_gpu_hours: None,
                            daily_gpu_hour_cap: Some(policy.budget.daily_gpu_hours),
                        }),
                    )
                        .into_response();
                }
                match state.budget_ledger.reserve(&policy, task_name).await {
                    Ok(value) => admission = Some(value),
                    Err(error) => {
                        warn!(task = task_name, schedule, error = %error, "fail-closed schedule budget admission rejected");
                        return (
                            StatusCode::OK,
                            Json(RunResponse {
                                accepted: false,
                                operation_name: None,
                                reason: Some(format!("schedule_budget_rejected: {error}")),
                                schedule: Some(schedule.into()),
                                reserved_gpu_hours: None,
                                daily_gpu_hour_cap: Some(policy.budget.daily_gpu_hours),
                            }),
                        )
                            .into_response();
                    }
                }
            }
        }
    }

    let mut overrides_args = vec![payload.command.clone()];
    overrides_args.extend(payload.args.iter().cloned());
    overrides_args.push("--beat-emit-url".into());
    overrides_args.push(payload.beat_emit_url.clone());
    overrides_args.push("--fixture-url".into());
    overrides_args.push(payload.fixture_url.clone());
    let container_env = admission.as_ref().map_or_else(Vec::new, |value| {
        vec![
            ("LUPINE_SCHEDULE_NAME".into(), value.schedule.clone()),
            (
                "LUPINE_BUDGET_RESERVATION_GPU_HOURS".into(),
                value.reservation_gpu_hours.to_string(),
            ),
        ]
    });

    let req = jobrun::JobRunRequest {
        project_id: state.cfg.project_id.clone(),
        region: state.cfg.region.clone(),
        job_name: target_job,
        container_args: overrides_args,
        container_env,
    };

    match run_job(state.runner.as_ref(), &req).await {
        Ok(op) => {
            info!(task = task_name, operation = %op, "job run accepted");
            (
                StatusCode::OK,
                Json(RunResponse {
                    accepted: true,
                    operation_name: Some(op),
                    reason: None,
                    schedule: admission.as_ref().map(|value| value.schedule.clone()),
                    reserved_gpu_hours: admission.as_ref().map(|value| value.reserved_gpu_hours),
                    daily_gpu_hour_cap: admission.as_ref().map(|value| value.daily_gpu_hour_cap),
                }),
            )
                .into_response()
        }
        Err(e) if admission.is_some() => {
            error!(task = task_name, error = %e, "job run failed; no-silent-retry policy consumed reservation");
            (
                StatusCode::OK,
                Json(RunResponse {
                    accepted: false,
                    operation_name: None,
                    reason: Some(format!("upstream_job_run_failed_no_retry: {e}")),
                    schedule: admission.as_ref().map(|value| value.schedule.clone()),
                    reserved_gpu_hours: admission.as_ref().map(|value| value.reserved_gpu_hours),
                    daily_gpu_hour_cap: admission.as_ref().map(|value| value.daily_gpu_hour_cap),
                }),
            )
                .into_response()
        }
        Err(e) => {
            error!(task = task_name, error = %e, "job run failed");
            (
                StatusCode::BAD_GATEWAY,
                format!("upstream job run failed: {e}"),
            )
                .into_response()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    fn dev_cli() -> Cli {
        Cli {
            port: 0,
            service_url: Some("https://example.run.app".into()),
            project_id: "test-project".into(),
            region: "us-central1".into(),
            target_job: "atlas-distill".into(),
            backend_catalog_url: format!(
                "{}/../mlip-cell-runner/backend_catalog.json",
                env!("CARGO_MANIFEST_DIR")
            ),
            schedule_policy_url: format!(
                "{}/../mlip-cell-runner/policies",
                env!("CARGO_MANIFEST_DIR")
            ),
            budget_ledger_url: "gs://unused/dev".into(),
            dev_mode: true,
        }
    }

    #[tokio::test]
    async fn rejects_malformed_body() {
        let app = build_app(dev_cli()).await.unwrap();
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("content-type", "application/json")
                    .body(Body::from("{not-json}"))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn accepts_valid_dev_mode_request() {
        let app = build_app(dev_cli()).await.unwrap();
        let body = serde_json::json!({
            "fixture_url": "gs://bucket/path.dump",
            "command": "auto-research",
            "args": ["--element", "Al"],
            "beat_emit_url": "https://glim-think.example.workers.dev/beat"
        });
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("content-type", "application/json")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let bytes = res.into_body().collect().await.unwrap().to_bytes();
        let parsed: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(parsed["accepted"], serde_json::Value::Bool(true));
    }

    #[tokio::test]
    async fn healthz_ok() {
        let app = build_app(dev_cli()).await.unwrap();
        let res = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/healthz")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn rejects_missing_required_field() {
        let app = build_app(dev_cli()).await.unwrap();
        // missing fixture_url
        let body = serde_json::json!({
            "command": "auto-research",
            "args": [],
            "beat_emit_url": "https://x.example/beat"
        });
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn rejects_target_job_outside_allowlist() {
        let app = build_app(dev_cli()).await.unwrap();
        let body = serde_json::json!({
            "fixture_url": "gs://bucket/path.dump",
            "command": "run-cell",
            "args": [],
            "beat_emit_url": "https://glim-think.example.workers.dev/beat",
            "target_job": "not-approved"
        });
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn accepts_allowlisted_mlip_target_job() {
        let app = build_app(dev_cli()).await.unwrap();
        let body = serde_json::json!({
            "fixture_url": "gs://bucket/manifest.json",
            "command": "run-cell",
            "args": ["--run-id", "r1"],
            "beat_emit_url": "https://glim-think.example.workers.dev/beat",
            "target_job": "mlip-cell-chgnet",
            "schedule_name": "nightly-baseline"
        });
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        let status = res.status();
        let response_body = res.into_body().collect().await.unwrap().to_bytes();
        assert_eq!(
            status,
            StatusCode::OK,
            "{}",
            String::from_utf8_lossy(&response_body)
        );
    }

    #[tokio::test]
    async fn catalog_entry_is_sufficient_to_allow_a_new_target_job() {
        let path = std::env::temp_dir().join(format!(
            "tasks-consumer-catalog-{}.json",
            std::process::id()
        ));
        std::fs::write(
            &path,
            r#"{"schema":"lupine.mlip.backend_catalog.v1","backends":[{"mlip_id":"new-backend","target_job":"mlip-cell-new-backend"}]}"#,
        )
        .unwrap();
        let mut cli = dev_cli();
        cli.backend_catalog_url = path.to_string_lossy().into_owned();
        let app = build_app(cli).await.unwrap();
        let body = serde_json::json!({
            "fixture_url": "gs://bucket/manifest.json",
            "command": "run-cell",
            "args": [],
            "beat_emit_url": "https://glim-think.example.workers.dev/beat",
            "target_job": "mlip-cell-new-backend",
            "schedule_name": "manual"
        });
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-lupine-owner-note", "catalog onboarding verification")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        std::fs::remove_file(path).unwrap();
        assert_eq!(res.status(), StatusCode::OK);
    }
}
