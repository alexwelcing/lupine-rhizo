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
mod telemetry;

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

    /// Existing glim-think OTLP relay base URL. Optional for local/manual paths.
    #[arg(long, env = "OTLP_RELAY_URL")]
    otlp_relay_url: Option<String>,

    /// Shared x-relay-token for the glim-think OTLP relay.
    #[arg(long, env = "OTLP_RELAY_TOKEN")]
    otlp_relay_token: Option<String>,

    /// Phoenix project receiving cloud campaign-cell traces.
    #[arg(long, env = "OTLP_PROJECT_NAME", default_value = "glim-think")]
    otlp_project_name: String,

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
    #[serde(default)]
    pub telemetry: Option<CloudCellTelemetry>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct CloudCellTelemetry {
    pub schema: String,
    pub origin: String,
    pub correlation_id: String,
    pub run_id: String,
    pub cell_id: String,
    pub row_id: String,
    pub mlip_id: String,
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
    trace_emitter: Arc<dyn telemetry::TraceEmitter>,
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
    let trace_emitter: Arc<dyn telemetry::TraceEmitter> =
        match (cli.otlp_relay_url.clone(), cli.otlp_relay_token.clone()) {
            (Some(endpoint), Some(token)) => Arc::new(telemetry::HttpTraceEmitter::new(
                endpoint,
                token,
                cli.otlp_project_name.clone(),
            )?),
            (None, None) => Arc::new(telemetry::NoopTraceEmitter),
            _ => anyhow::bail!("OTLP_RELAY_URL and OTLP_RELAY_TOKEN must be configured together"),
        };
    let state = AppState {
        cfg: Arc::new(cli),
        verifier,
        runner,
        budget_ledger,
        trace_emitter,
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

    if let Err(error) = validate_cloud_telemetry(&payload) {
        warn!(task = task_name, error = %error, "invalid cloud cell telemetry envelope");
        return (
            StatusCode::BAD_REQUEST,
            format!("invalid telemetry: {error}"),
        )
            .into_response();
    }

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
            if let Some(schedule) = payload
                .schedule_name
                .as_deref()
                .filter(|schedule| *schedule != "manual")
            {
                return no_retry_rejection(
                    schedule,
                    format!("backend_catalog_unavailable_no_retry: {e}"),
                    None,
                );
            }
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
    if let (Some(backend), Some(identity)) = (backend, payload.telemetry.as_ref()) {
        if backend != identity.mlip_id {
            return (
                StatusCode::BAD_REQUEST,
                "target_job backend does not match telemetry mlip_id".to_string(),
            )
                .into_response();
        }
    }
    let mut admission = None;
    if backend.is_some() {
        match payload.schedule_name.as_deref() {
            Some("manual") if owner_noted_manual => {
                info!(
                    task = task_name,
                    "explicit owner-noted manual dispatch excluded from schedule ledger"
                );
            }
            Some("manual") => {
                return (
                    StatusCode::BAD_REQUEST,
                    "manual MLIP dispatch requires x-lupine-owner-note".to_string(),
                )
                    .into_response();
            }
            None => {
                info!(
                    task = task_name,
                    target_job,
                    "legacy campaign dispatch has no schedule identity; admitting outside scheduled caps"
                );
            }
            Some(schedule) => {
                let policy =
                    match budget::load_policy(&state.cfg.schedule_policy_url, schedule).await {
                        Ok(policy) => policy,
                        Err(error) => {
                            error!(task = task_name, error = %error, "schedule policy unavailable");
                            return no_retry_rejection(
                                schedule,
                                format!("schedule_policy_unavailable_no_retry: {error:#}"),
                                None,
                            );
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
                match state
                    .budget_ledger
                    .reserve(&policy, task_name, &target_job)
                    .await
                {
                    Ok(value) if value.duplicate => {
                        warn!(
                            task = task_name,
                            schedule, "duplicate scheduled delivery acknowledged without dispatch"
                        );
                        return (
                            StatusCode::OK,
                            Json(RunResponse {
                                accepted: false,
                                operation_name: None,
                                reason: Some("duplicate_schedule_reservation".into()),
                                schedule: Some(value.schedule),
                                reserved_gpu_hours: Some(value.reserved_gpu_hours),
                                daily_gpu_hour_cap: Some(value.daily_gpu_hour_cap),
                            }),
                        )
                            .into_response();
                    }
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
            if let Some(identity) = payload.telemetry.as_ref() {
                let span = telemetry::CloudCellSpan::dispatched(
                    identity,
                    &req.job_name,
                    admission.as_ref(),
                    "admitted",
                );
                emit_trace_off_path(
                    state.trace_emitter.clone(),
                    span,
                    task_name.to_string(),
                    identity.run_id.clone(),
                    identity.cell_id.clone(),
                    "cloud cell OTLP export failed after dispatch; failure retained in Cloud Logging",
                );
            }
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
            if let Some(identity) = payload.telemetry.as_ref() {
                let span = telemetry::CloudCellSpan::dispatched(
                    identity,
                    &req.job_name,
                    admission.as_ref(),
                    "dispatch_failed",
                );
                emit_trace_off_path(
                    state.trace_emitter.clone(),
                    span,
                    task_name.to_string(),
                    identity.run_id.clone(),
                    identity.cell_id.clone(),
                    "cloud cell OTLP failure-span export failed; failure retained in Cloud Logging",
                );
            }
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
            if let Some(identity) = payload.telemetry.as_ref() {
                let span = telemetry::CloudCellSpan::dispatched(
                    identity,
                    &req.job_name,
                    None,
                    "dispatch_failed",
                );
                emit_trace_off_path(
                    state.trace_emitter.clone(),
                    span,
                    task_name.to_string(),
                    identity.run_id.clone(),
                    identity.cell_id.clone(),
                    "unscheduled cloud cell failure-span export failed; failure retained in Cloud Logging",
                );
            }
            (
                StatusCode::BAD_GATEWAY,
                format!("upstream job run failed: {e}"),
            )
                .into_response()
        }
    }
}

fn emit_trace_off_path(
    emitter: Arc<dyn telemetry::TraceEmitter>,
    span: telemetry::CloudCellSpan,
    task_name: String,
    run_id: String,
    cell_id: String,
    failure_message: &'static str,
) {
    let telemetry_delivery_id = format!("{task_name}:{cell_id}");
    info!(
        task = task_name,
        run_id,
        cell_id,
        telemetry_delivery_id,
        telemetry_delivery_state = "pending",
        "cloud cell OTLP export queued; stale pending record denotes undelivered telemetry"
    );
    tokio::spawn(async move {
        match emitter.emit(&span).await {
            Ok(()) => info!(
                task = task_name,
                run_id,
                cell_id,
                telemetry_delivery_id,
                telemetry_delivery_state = "delivered",
                "cloud cell OTLP export delivered"
            ),
            Err(error) => error!(
                task = task_name,
                run_id,
                cell_id,
                telemetry_delivery_id,
                telemetry_delivery_state = "failed",
                error = %error,
                failure_message
            ),
        }
    });
}

fn validate_cloud_telemetry(payload: &TaskPayload) -> anyhow::Result<()> {
    let telemetry = match payload.telemetry.as_ref() {
        Some(telemetry) => telemetry,
        None if payload
            .schedule_name
            .as_deref()
            .is_some_and(|schedule| schedule != "manual") =>
        {
            anyhow::bail!("scheduled cloud cell requires telemetry")
        }
        None => return Ok(()),
    };
    if telemetry.schema != "lupine.mlip.cloud_cell_span.v1" {
        anyhow::bail!("schema must be lupine.mlip.cloud_cell_span.v1");
    }
    if telemetry.origin != "cloud" {
        anyhow::bail!("origin must be cloud");
    }
    for (name, value) in [
        ("correlation_id", telemetry.correlation_id.as_str()),
        ("run_id", telemetry.run_id.as_str()),
        ("cell_id", telemetry.cell_id.as_str()),
        ("row_id", telemetry.row_id.as_str()),
        ("mlip_id", telemetry.mlip_id.as_str()),
    ] {
        if value.trim().is_empty() {
            anyhow::bail!("{name} must be non-empty");
        }
    }
    let identity_args = [
        ("--run-id", telemetry.run_id.as_str()),
        ("--cell-id", telemetry.cell_id.as_str()),
        ("--row-id", telemetry.row_id.as_str()),
        ("--mlip-id", telemetry.mlip_id.as_str()),
    ];
    for value in &payload.args {
        let candidate = value
            .split_once('=')
            .map_or(value.as_str(), |(name, _)| name);
        if candidate.starts_with("--")
            && !identity_args.iter().any(|(flag, _)| *flag == candidate)
            && identity_args
                .iter()
                .any(|(flag, _)| flag.starts_with(candidate))
        {
            anyhow::bail!("{candidate} is an abbreviated identity argument");
        }
    }
    for (flag, expected) in identity_args {
        let inline_prefix = format!("{flag}=");
        let matches = payload
            .args
            .iter()
            .enumerate()
            .filter_map(|(index, value)| {
                if value == flag {
                    Some((index, None))
                } else {
                    value
                        .strip_prefix(&inline_prefix)
                        .map(|inline| (index, Some(inline)))
                }
            })
            .collect::<Vec<_>>();
        let Some((position, inline_value)) = matches.first().copied() else {
            anyhow::bail!("missing {flag} argument")
        };
        if matches.len() != 1 {
            anyhow::bail!("duplicate {flag} argument");
        }
        let actual = inline_value
            .or_else(|| payload.args.get(position + 1).map(String::as_str))
            .ok_or_else(|| anyhow::anyhow!("missing {flag} argument"))?;
        if actual != expected {
            anyhow::bail!("{flag} does not match telemetry envelope");
        }
    }
    Ok(())
}

fn no_retry_rejection(
    schedule: &str,
    reason: String,
    daily_gpu_hour_cap: Option<f64>,
) -> axum::response::Response {
    (
        StatusCode::OK,
        Json(RunResponse {
            accepted: false,
            operation_name: None,
            reason: Some(reason),
            schedule: Some(schedule.to_string()),
            reserved_gpu_hours: None,
            daily_gpu_hour_cap,
        }),
    )
        .into_response()
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use std::collections::BTreeMap;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Mutex;
    use tower::ServiceExt;

    #[derive(Default)]
    struct RecordingRunner {
        calls: AtomicUsize,
        fail: bool,
    }

    #[axum::async_trait]
    impl JobRunner for RecordingRunner {
        async fn run(&self, _req: &jobrun::JobRunRequest) -> anyhow::Result<String> {
            self.calls.fetch_add(1, Ordering::SeqCst);
            if self.fail {
                anyhow::bail!("synthetic runner failure");
            }
            Ok("operations/test".into())
        }
    }

    struct RejectingLedger;

    #[axum::async_trait]
    impl budget::BudgetLedger for RejectingLedger {
        async fn reserve(
            &self,
            _policy: &budget::SchedulePolicy,
            _task_name: &str,
            _target_job: &str,
        ) -> anyhow::Result<budget::Admission> {
            anyhow::bail!("synthetic cap exhausted")
        }
    }

    #[derive(Default)]
    struct RecordingTraceEmitter {
        spans: Mutex<Vec<BTreeMap<String, serde_json::Value>>>,
    }

    #[axum::async_trait]
    impl telemetry::TraceEmitter for RecordingTraceEmitter {
        async fn emit(&self, span: &telemetry::CloudCellSpan) -> anyhow::Result<()> {
            self.spans.lock().unwrap().push(span.attributes());
            Ok(())
        }
    }

    async fn wait_for_spans(
        emitter: &RecordingTraceEmitter,
    ) -> Vec<BTreeMap<String, serde_json::Value>> {
        tokio::time::timeout(std::time::Duration::from_secs(1), async {
            loop {
                let spans = emitter.spans.lock().unwrap().clone();
                if !spans.is_empty() {
                    return spans;
                }
                tokio::task::yield_now().await;
            }
        })
        .await
        .expect("background telemetry export did not run")
    }

    struct FailingTraceEmitter;

    #[axum::async_trait]
    impl telemetry::TraceEmitter for FailingTraceEmitter {
        async fn emit(&self, _span: &telemetry::CloudCellSpan) -> anyhow::Result<()> {
            anyhow::bail!("synthetic relay outage")
        }
    }

    struct DispatchOrderTraceEmitter {
        runner: Arc<RecordingRunner>,
    }

    #[axum::async_trait]
    impl telemetry::TraceEmitter for DispatchOrderTraceEmitter {
        async fn emit(&self, _span: &telemetry::CloudCellSpan) -> anyhow::Result<()> {
            assert_eq!(
                self.runner.calls.load(Ordering::SeqCst),
                1,
                "optional relay I/O must start only after compute dispatch"
            );
            Ok(())
        }
    }

    struct HangingTraceEmitter;

    #[axum::async_trait]
    impl telemetry::TraceEmitter for HangingTraceEmitter {
        async fn emit(&self, _span: &telemetry::CloudCellSpan) -> anyhow::Result<()> {
            std::future::pending().await
        }
    }

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
            otlp_relay_url: None,
            otlp_relay_token: None,
            otlp_project_name: "glim-think".into(),
            dev_mode: true,
        }
    }

    fn app_with_runner(cli: Cli, runner: Arc<dyn JobRunner>) -> Router {
        app_with_dependencies(cli, runner, budget::memory_ledger())
    }

    fn app_with_dependencies(
        cli: Cli,
        runner: Arc<dyn JobRunner>,
        budget_ledger: Arc<dyn budget::BudgetLedger>,
    ) -> Router {
        Router::new()
            .route("/run", post(handle_run))
            .with_state(AppState {
                cfg: Arc::new(cli),
                verifier: Arc::new(auth::DevModeVerifier),
                runner,
                budget_ledger,
                trace_emitter: Arc::new(telemetry::NoopTraceEmitter),
            })
    }

    fn app_with_trace_emitter(
        cli: Cli,
        runner: Arc<dyn JobRunner>,
        trace_emitter: Arc<dyn telemetry::TraceEmitter>,
    ) -> Router {
        Router::new()
            .route("/run", post(handle_run))
            .with_state(AppState {
                cfg: Arc::new(cli),
                verifier: Arc::new(auth::DevModeVerifier),
                runner,
                budget_ledger: budget::memory_ledger(),
                trace_emitter,
            })
    }

    fn scheduled_body() -> serde_json::Value {
        serde_json::json!({
            "fixture_url": "gs://bucket/manifest.json",
            "command": "run-cell",
            "beat_emit_url": "https://glim-think.example.workers.dev/beat",
            "target_job": "mlip-cell-mace",
            "schedule_name": "nightly-baseline",
            "telemetry": {
                "schema": "lupine.mlip.cloud_cell_span.v1",
                "origin": "cloud",
                "correlation_id": "workflow-nightly-1",
                "run_id": "nightly-run-1",
                "cell_id": "nightly-run-1:baseline:energy_volume:mace-mp-0",
                "row_id": "energy_volume",
                "mlip_id": "mace-mp-0"
            },
            "args": [
                "--run-id", "nightly-run-1",
                "--cell-id", "nightly-run-1:baseline:energy_volume:mace-mp-0",
                "--row-id", "energy_volume",
                "--mlip-id", "mace-mp-0"
            ]
        })
    }

    #[tokio::test]
    async fn scheduled_cloud_cell_without_telemetry_fails_closed() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        let mut body = scheduled_body();
        body.as_object_mut().unwrap().remove("telemetry");
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "missing-telemetry")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn scheduled_cloud_cell_with_mismatched_ids_fails_closed() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        let mut body = scheduled_body();
        body["telemetry"]["cell_id"] = serde_json::Value::String("different-cell".into());
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "mismatched-telemetry")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn duplicate_identity_flags_fail_closed_before_dispatch() {
        for flag in ["--run-id", "--cell-id", "--row-id", "--mlip-id"] {
            let runner = Arc::new(RecordingRunner::default());
            let app = app_with_runner(dev_cli(), runner.clone());
            let mut body = scheduled_body();
            body["args"].as_array_mut().unwrap().extend([
                serde_json::Value::String(flag.into()),
                serde_json::Value::String("attacker-controlled".into()),
            ]);
            let res = app
                .oneshot(
                    Request::builder()
                        .method("POST")
                        .uri("/run")
                        .header("x-cloudtasks-taskname", format!("duplicate-{flag}"))
                        .body(Body::from(body.to_string()))
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(res.status(), StatusCode::BAD_REQUEST, "flag={flag}");
            assert_eq!(runner.calls.load(Ordering::SeqCst), 0, "flag={flag}");
        }
    }

    #[tokio::test]
    async fn mixed_form_duplicate_identity_flags_fail_closed_before_dispatch() {
        for flag in ["--run-id", "--cell-id", "--row-id", "--mlip-id"] {
            let runner = Arc::new(RecordingRunner::default());
            let app = app_with_runner(dev_cli(), runner.clone());
            let mut body = scheduled_body();
            body["args"]
                .as_array_mut()
                .unwrap()
                .push(serde_json::Value::String(format!(
                    "{flag}=attacker-controlled"
                )));
            let res = app
                .oneshot(
                    Request::builder()
                        .method("POST")
                        .uri("/run")
                        .header("x-cloudtasks-taskname", format!("mixed-duplicate-{flag}"))
                        .body(Body::from(body.to_string()))
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(res.status(), StatusCode::BAD_REQUEST, "flag={flag}");
            assert_eq!(runner.calls.load(Ordering::SeqCst), 0, "flag={flag}");
        }
    }

    #[tokio::test]
    async fn dangling_identity_flag_fails_closed_before_dispatch() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        let mut body = scheduled_body();
        body["args"] = serde_json::json!(["--run-id"]);
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "dangling-run-id")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn abbreviated_identity_flags_fail_closed_before_dispatch() {
        for flag in ["--run-i", "--cell-i", "--row-i", "--mlip-i"] {
            let runner = Arc::new(RecordingRunner::default());
            let app = app_with_runner(dev_cli(), runner.clone());
            let mut body = scheduled_body();
            body["args"].as_array_mut().unwrap().extend([
                serde_json::Value::String(flag.into()),
                serde_json::Value::String("attacker-controlled".into()),
            ]);
            let res = app
                .oneshot(
                    Request::builder()
                        .method("POST")
                        .uri("/run")
                        .header("x-cloudtasks-taskname", format!("abbreviated-{flag}"))
                        .body(Body::from(body.to_string()))
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(res.status(), StatusCode::BAD_REQUEST, "flag={flag}");
            assert_eq!(runner.calls.load(Ordering::SeqCst), 0, "flag={flag}");
        }
    }

    #[tokio::test]
    async fn admitted_scheduled_cell_emits_exactly_one_cost_capped_span() {
        let runner = Arc::new(RecordingRunner::default());
        let emitter = Arc::new(RecordingTraceEmitter::default());
        let app = app_with_trace_emitter(dev_cli(), runner.clone(), emitter.clone());
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "telemetry-cell-1")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
        let spans = wait_for_spans(&emitter).await;
        assert_eq!(spans.len(), 1);
        assert_eq!(
            spans[0]["mlip.cell_id"],
            scheduled_body()["telemetry"]["cell_id"]
        );
        assert_eq!(spans[0]["mlip.dispatch.status"], "admitted");
        assert_eq!(spans[0]["mlip.cost.daily_gpu_hour_cap"], 3.0);
    }

    #[tokio::test]
    async fn telemetry_io_starts_after_compute_dispatch() {
        let runner = Arc::new(RecordingRunner::default());
        let emitter = Arc::new(DispatchOrderTraceEmitter {
            runner: runner.clone(),
        });
        let app = app_with_trace_emitter(dev_cli(), runner.clone(), emitter);
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "dispatch-before-telemetry")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn telemetry_io_does_not_delay_dispatch_response() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_trace_emitter(dev_cli(), runner.clone(), Arc::new(HangingTraceEmitter));
        let response = tokio::time::timeout(
            std::time::Duration::from_millis(100),
            app.oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "nonblocking-telemetry")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            ),
        )
        .await
        .expect("optional relay I/O must not delay the dispatch response")
        .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn off_path_telemetry_records_durable_pending_and_terminal_states() {
        let source = include_str!("main.rs");
        assert!(source.contains("telemetry_delivery_state = \"pending\""));
        assert!(source.contains("telemetry_delivery_state = \"delivered\""));
        assert!(source.contains("telemetry_delivery_state = \"failed\""));
        assert!(source.contains("stale pending record denotes undelivered telemetry"));
    }

    #[tokio::test]
    async fn unscheduled_campaign_cell_emits_telemetry_after_dispatch() {
        let runner = Arc::new(RecordingRunner::default());
        let emitter = Arc::new(RecordingTraceEmitter::default());
        let app = app_with_trace_emitter(dev_cli(), runner.clone(), emitter.clone());
        let mut body = scheduled_body();
        body.as_object_mut().unwrap().remove("schedule_name");
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "unscheduled-campaign-cell")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
        let spans = wait_for_spans(&emitter).await;
        assert_eq!(spans.len(), 1);
        assert_eq!(spans[0]["mlip.schedule.name"], "unscheduled-campaign");
        assert_eq!(spans[0]["mlip.cost.reservation_gpu_hours"], 0.0);
    }

    #[tokio::test]
    async fn unscheduled_campaign_dispatch_failure_emits_failure_telemetry() {
        let runner = Arc::new(RecordingRunner {
            calls: AtomicUsize::new(0),
            fail: true,
        });
        let emitter = Arc::new(RecordingTraceEmitter::default());
        let app = app_with_trace_emitter(dev_cli(), runner.clone(), emitter.clone());
        let mut body = scheduled_body();
        body.as_object_mut().unwrap().remove("schedule_name");
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "unscheduled-campaign-failure")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::BAD_GATEWAY);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
        let spans = wait_for_spans(&emitter).await;
        assert_eq!(spans.len(), 1);
        assert_eq!(spans[0]["mlip.dispatch.status"], "dispatch_failed");
        assert_eq!(spans[0]["mlip.schedule.name"], "unscheduled-campaign");
    }

    #[tokio::test]
    async fn telemetry_transport_failure_does_not_block_an_admitted_cell() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_trace_emitter(dev_cli(), runner.clone(), Arc::new(FailingTraceEmitter));
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "telemetry-outage-cell")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
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
            "args": ["--run-id", "r1", "--cell-id", "cell-chgnet", "--row-id", "row-1", "--mlip-id", "chgnet"],
            "beat_emit_url": "https://glim-think.example.workers.dev/beat",
            "target_job": "mlip-cell-chgnet",
            "schedule_name": "nightly-baseline",
            "telemetry": {
                "schema": "lupine.mlip.cloud_cell_span.v1",
                "origin": "cloud",
                "correlation_id": "r1",
                "run_id": "r1",
                "cell_id": "cell-chgnet",
                "row_id": "row-1",
                "mlip_id": "chgnet"
            }
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
    async fn accepts_existing_unscheduled_mlip_campaign_path() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        let mut body = scheduled_body();
        body.as_object_mut().unwrap().remove("schedule_name");
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "legacy-campaign-task")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn policy_rejects_cloud_tasks_retry_without_dispatching() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        let body = scheduled_body();
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskretrycount", "1")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let bytes = res.into_body().collect().await.unwrap().to_bytes();
        let parsed: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(parsed["accepted"], false);
        assert_eq!(parsed["reason"], "cloud_tasks_retry_rejected_by_policy");
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn duplicate_schedule_delivery_dispatches_runner_once() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        for _ in 0..2 {
            let res = app
                .clone()
                .oneshot(
                    Request::builder()
                        .method("POST")
                        .uri("/run")
                        .header("x-cloudtasks-taskname", "same-scheduled-task")
                        .body(Body::from(scheduled_body().to_string()))
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(res.status(), StatusCode::OK);
        }
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn admitted_runner_failure_is_acknowledged_without_retry() {
        let runner = Arc::new(RecordingRunner {
            calls: AtomicUsize::new(0),
            fail: true,
        });
        let app = app_with_runner(dev_cli(), runner.clone());
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "failing-scheduled-task")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let bytes = res.into_body().collect().await.unwrap().to_bytes();
        let parsed: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(parsed["accepted"], false);
        assert!(parsed["reason"]
            .as_str()
            .unwrap()
            .starts_with("upstream_job_run_failed_no_retry:"));
        assert_eq!(runner.calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn cap_rejection_is_acknowledged_without_dispatching() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_dependencies(dev_cli(), runner.clone(), Arc::new(RejectingLedger));
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "over-cap-task")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let bytes = res.into_body().collect().await.unwrap().to_bytes();
        let parsed: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(parsed["accepted"], false);
        assert!(parsed["reason"]
            .as_str()
            .unwrap()
            .starts_with("schedule_budget_rejected:"));
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn scheduled_catalog_failure_is_acknowledged_without_retry_or_dispatch() {
        let runner = Arc::new(RecordingRunner::default());
        let mut cli = dev_cli();
        cli.backend_catalog_url = "/definitely/missing/backend_catalog.json".into();
        let app = app_with_runner(cli, runner.clone());
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "catalog-failure-task")
                    .body(Body::from(scheduled_body().to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let body: serde_json::Value =
            serde_json::from_slice(&res.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(body["accepted"], false);
        assert!(body["reason"]
            .as_str()
            .unwrap()
            .starts_with("backend_catalog_unavailable_no_retry:"));
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn scheduled_policy_failure_is_acknowledged_without_retry_or_dispatch() {
        let runner = Arc::new(RecordingRunner::default());
        let app = app_with_runner(dev_cli(), runner.clone());
        let mut body = scheduled_body();
        body["schedule_name"] = serde_json::Value::String("missing-policy".into());
        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/run")
                    .header("x-cloudtasks-taskname", "policy-failure-task")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let body: serde_json::Value =
            serde_json::from_slice(&res.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(body["accepted"], false);
        assert!(body["reason"]
            .as_str()
            .unwrap()
            .starts_with("schedule_policy_unavailable_no_retry:"));
        assert_eq!(runner.calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn checked_in_deploy_config_publishes_policies_and_disables_job_retries() {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
        let consumer_build = std::fs::read_to_string(root.join("cloudbuild.yaml")).unwrap();
        assert!(consumer_build.contains("policies/nightly-baseline.yml"));
        assert!(consumer_build.contains("policies/on-proof-complete.yml"));
        assert!(consumer_build.contains("OTLP_RELAY_URL=${_OTLP_RELAY_URL}"));
        assert!(consumer_build.contains("OTLP_RELAY_TOKEN=PHOENIX_RELAY_TOKEN:latest"));
        assert!(consumer_build.contains("--update-env-vars=\"SERVICE_URL=$$URL\""));
        assert_eq!(consumer_build.matches("--set-env-vars=").count(), 1);
        assert!(consumer_build.contains("--no-cpu-throttling"));

        let runner_build =
            std::fs::read_to_string(root.join("../mlip-cell-runner/cloudbuild.unified.yaml"))
                .unwrap();
        assert!(runner_build.contains("--max-retries=0"));
        assert!(!runner_build.contains("--max-retries=1"));
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
