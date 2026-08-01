//! `monitor_cloud_run` — periodic Cloud Run service/job health and cost
//! reporter for the Lupine ops fleet.
//!
//! Replaces the never-shipped `monitor_cloud_run.py` referenced in
//! `docs/handoff/04_autonomous_handoff_protocol.md`. The binary
//! authenticates to GCP, walks Cloud Run admin APIs in the configured
//! project/region, queries Cloud Monitoring for a 24h cost proxy, then
//! emits a human-readable summary to stdout and (optionally) POSTs the
//! structured payload to a report URL — intended to feed the
//! `glim-think` CF Worker fleet dashboard.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration as StdDuration;

use anyhow::{Context, Result, anyhow};
use clap::Parser;
use gcp_auth::{Token, TokenProvider};
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use time::OffsetDateTime;
use time::format_description::well_known::Rfc3339;

const CLOUD_PLATFORM_SCOPE: &str = "https://www.googleapis.com/auth/cloud-platform";
const CLOUD_RUN_BASE: &str = "https://run.googleapis.com/v2";
const MONITORING_BASE: &str = "https://monitoring.googleapis.com/v3";
const IDLE_FLAG_THRESHOLD_SECS: i64 = 10 * 60;

#[derive(Parser, Debug, Clone)]
#[command(
    name = "monitor_cloud_run",
    about = "Poll Cloud Run services/jobs and surface cost + idle anomalies.",
    version
)]
struct Args {
    /// GCP project ID to inspect.
    #[arg(long, default_value = "shed-489901")]
    project: String,

    /// Cloud Run region (single-region polling — extend later if multi-region matters).
    #[arg(long, default_value = "us-central1")]
    region: String,

    /// Run a single poll then exit. Default: loop forever.
    #[arg(long)]
    once: bool,

    /// Poll interval when running in loop mode.
    #[arg(long, default_value_t = 300, value_name = "SECS")]
    interval_secs: u64,

    /// 24h cost ceiling (USD). Services exceeding this trigger a `flags.cost_exceeded` entry.
    #[arg(long, default_value_t = 50.0, value_name = "USD")]
    cost_cap_usd: f64,

    /// Directory containing lupine.mlip.run_policy.v1 YAML files.
    #[arg(
        long,
        default_value = "gcp/mlip-cell-runner/policies",
        value_name = "DIR"
    )]
    policy_dir: PathBuf,

    /// Backend catalog used to resolve policy backend ids to Cloud Run jobs.
    #[arg(
        long,
        default_value = "gcp/mlip-cell-runner/backend_catalog.json",
        value_name = "FILE"
    )]
    backend_catalog: PathBuf,

    /// GCS prefix containing atomic per-schedule daily reservation ledgers.
    #[arg(
        long,
        default_value = "gs://shed-489901-atlas-inputs/mlip-budget-ledgers",
        value_name = "GS_URL"
    )]
    budget_ledger_url: String,

    /// If set, POST the JSON-shaped summary to this URL after each poll
    /// (intended for the glim-think CF Worker ingestion endpoint).
    #[arg(long, value_name = "URL")]
    report_url: Option<String>,
}

/// Minimal Cloud Run v2 service shape — only the fields we actually surface.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunService {
    name: String,
    #[serde(default)]
    latest_ready_revision: Option<String>,
    #[serde(default)]
    update_time: Option<String>,
    #[serde(default)]
    terminal_condition: Option<TerminalCondition>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunJob {
    name: String,
    #[serde(default)]
    update_time: Option<String>,
    #[serde(default)]
    latest_created_execution: Option<JobExecutionRef>,
    #[serde(default)]
    terminal_condition: Option<TerminalCondition>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct JobExecutionRef {
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    completion_time: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TerminalCondition {
    #[serde(default)]
    state: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ListServicesResponse {
    #[serde(default)]
    services: Vec<RunService>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ListJobsResponse {
    #[serde(default)]
    jobs: Vec<RunJob>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ListExecutionsResponse {
    #[serde(default)]
    executions: Vec<RunExecution>,
    #[serde(default)]
    next_page_token: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunExecution {
    job: String,
    #[serde(default)]
    start_time: Option<String>,
    #[serde(default)]
    completion_time: Option<String>,
    #[serde(default)]
    template: ExecutionTaskTemplate,
}

#[derive(Debug, Default, Deserialize)]
struct ExecutionTaskTemplate {
    #[serde(default)]
    containers: Vec<ExecutionContainer>,
}

#[derive(Debug, Default, Deserialize)]
struct ExecutionContainer {
    #[serde(default)]
    env: Vec<ExecutionEnvVar>,
}

#[derive(Debug, Deserialize)]
struct ExecutionEnvVar {
    name: String,
    #[serde(default)]
    value: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TimeSeriesResponse {
    #[serde(default)]
    time_series: Vec<TimeSeries>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TimeSeries {
    #[serde(default)]
    resource: Option<MonitoredResource>,
    #[serde(default)]
    points: Vec<Point>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct MonitoredResource {
    #[serde(default)]
    labels: std::collections::BTreeMap<String, String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Point {
    #[serde(default)]
    value: PointValue,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
struct PointValue {
    #[serde(default)]
    double_value: Option<f64>,
    #[serde(default)]
    int64_value: Option<String>,
}

#[derive(Debug, Serialize)]
struct ServiceReport {
    name: String,
    short_name: String,
    latest_revision: Option<String>,
    status: String,
    last_activity: Option<String>,
    instance_count: u64,
    proxy_metric_24h: f64,
    estimated_cost_usd: Option<f64>,
    flags: Vec<String>,
}

#[derive(Debug, Serialize)]
struct JobReport {
    name: String,
    short_name: String,
    status: String,
    last_activity: Option<String>,
    latest_execution: Option<String>,
    flags: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct BackendCatalog {
    schema: String,
    backends: Vec<BackendCatalogEntry>,
}

#[derive(Debug, Deserialize)]
struct BackendCatalogEntry {
    mlip_id: String,
    target_job: String,
}

#[derive(Debug, Deserialize)]
struct SchedulePolicy {
    name: String,
    #[serde(default)]
    active: bool,
    run: PolicyRun,
    #[serde(default)]
    budget: Option<PolicyBudget>,
}

#[derive(Debug, Deserialize)]
struct PolicyRun {
    #[serde(default)]
    backends: Vec<String>,
    #[serde(default)]
    #[serde(alias = "allow_dynamic_backend")]
    dynamic_catalog_backends: bool,
}

#[derive(Debug, Deserialize)]
struct PolicyBudget {
    daily_gpu_hours: f64,
    cost_basis: String,
    retry: String,
    #[serde(default)]
    owner_note: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CostBasis {
    schema: String,
    id: String,
    status: String,
    authoritative_ledger: AuthoritativeLedger,
    conflicting_claim: ConflictingClaim,
    gpu_estimate: GpuEstimate,
    owner_note_gate: OwnerNoteGate,
}

#[derive(Debug, Deserialize)]
struct AuthoritativeLedger {
    path: PathBuf,
    sha256: String,
    anchors: u64,
    cloud_equivalent_usd: f64,
}

#[derive(Debug, Deserialize)]
struct ConflictingClaim {
    anchors: u64,
    cloud_equivalent_usd: f64,
    disposition: String,
}

#[derive(Debug, Deserialize)]
struct GpuEstimate {
    usd_per_gpu_hour: f64,
}

#[derive(Debug, Deserialize)]
struct OwnerNoteGate {
    multiple_of_verified_unit: f64,
    usd: f64,
    require_owner_note_above: bool,
    silent_retry_allowed: bool,
}

#[derive(Debug, Serialize)]
struct ScheduleUsageReport {
    name: String,
    jobs: Vec<String>,
    reserved_gpu_hours: f64,
    gpu_hours_utc_day: f64,
    daily_gpu_hour_cap: f64,
    utilization_percent: f64,
    cost_basis: String,
    retry: String,
    attribution: String,
    flags: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct BudgetLedgerDocument {
    schema: String,
    schedule: String,
    utc_date: String,
    reserved_gpu_hours: f64,
    #[serde(default)]
    reservations: Vec<BudgetReservation>,
}

#[derive(Debug, Deserialize)]
struct BudgetReservation {
    #[serde(default)]
    target_job: String,
    gpu_hours: f64,
}

#[derive(Debug, Default)]
struct ScheduleReservations {
    reserved_gpu_hours: f64,
    legacy_unattributed_gpu_hours: f64,
}

#[derive(Debug, Default)]
struct ExecutionUsage {
    total_seconds_by_job: BTreeMap<String, f64>,
    scheduled_seconds_by_schedule_job: BTreeMap<(String, String), f64>,
}

#[derive(Debug, Serialize)]
struct PollSummary {
    project: String,
    region: String,
    polled_at: String,
    cost_cap_usd: f64,
    cost_metric_note: String,
    services: Vec<ServiceReport>,
    jobs: Vec<JobReport>,
    schedules: Vec<ScheduleUsageReport>,
    flags: Vec<String>,
}

struct Auth {
    provider: Arc<dyn TokenProvider>,
}

impl Auth {
    async fn new() -> Result<Self> {
        let provider = gcp_auth::provider()
            .await
            .context("gcp_auth: could not resolve credentials (set GOOGLE_APPLICATION_CREDENTIALS or run inside Cloud Run/GCE)")?;
        Ok(Self { provider })
    }

    async fn token(&self) -> Result<Arc<Token>> {
        let scopes = &[CLOUD_PLATFORM_SCOPE];
        self.provider
            .token(scopes)
            .await
            .context("gcp_auth: failed to mint access token for cloud-platform scope")
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();
    let auth = Auth::new().await?;
    let client = Client::builder()
        .timeout(StdDuration::from_secs(30))
        .build()
        .context("building reqwest client")?;

    if args.once {
        run_once(&args, &auth, &client).await?;
        return Ok(());
    }

    // Loop forever. Ctrl-C terminates cleanly via tokio::signal.
    let mut ticker = tokio::time::interval(StdDuration::from_secs(args.interval_secs.max(1)));
    ticker.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    loop {
        tokio::select! {
            _ = ticker.tick() => {
                if let Err(e) = run_once(&args, &auth, &client).await {
                    eprintln!("poll error: {e:#}");
                }
            }
            _ = tokio::signal::ctrl_c() => {
                eprintln!("ctrl-c received; exiting monitor loop");
                return Ok(());
            }
        }
    }
}

async fn run_once(args: &Args, auth: &Auth, client: &Client) -> Result<()> {
    let summary = collect_summary(args, auth, client).await?;
    print_human(&summary);

    if let Some(url) = &args.report_url
        && let Err(e) = post_report(client, url, &summary).await
    {
        eprintln!("warning: report POST to {url} failed: {e:#}");
    }
    Ok(())
}

async fn collect_summary(args: &Args, auth: &Auth, client: &Client) -> Result<PollSummary> {
    let token = auth.token().await?;
    let bearer = format!("Bearer {}", token.as_str());
    let policies = load_active_policies(&args.policy_dir)?;
    let backend_catalog = load_backend_catalog(&args.backend_catalog)?;

    // Cloud Run admin calls and the monitoring window query are independent —
    // fan them out concurrently and join.
    let (services_res, jobs_res, executions_res, requests_res, billable_res, reservations_res) = tokio::join!(
        list_services(client, &bearer, &args.project, &args.region),
        list_jobs(client, &bearer, &args.project, &args.region),
        list_executions(client, &bearer, &args.project, &args.region),
        fetch_request_counts(client, &bearer, &args.project),
        fetch_billable_instance_seconds(client, &bearer, &args.project, &args.region),
        fetch_schedule_reservations(client, &bearer, &args.budget_ledger_url, &policies),
    );

    let services = services_res?;
    let jobs = jobs_res?;
    let executions = executions_res?;
    let requests_by_service = requests_res.unwrap_or_else(|e| {
        eprintln!("warning: request-count metric unavailable: {e:#}");
        std::collections::BTreeMap::new()
    });
    // Budget telemetry fails closed: an API/permission/schema failure must not
    // become a healthy-looking zero-usage report.
    let billable_seconds_by_job = billable_res?;
    let reservations_by_schedule = reservations_res?;
    let now = OffsetDateTime::now_utc();
    let execution_usage =
        aggregate_execution_usage(&executions, now.replace_time(time::Time::MIDNIGHT), now)?;
    let schedule_usage = build_schedule_usage(
        &policies,
        &backend_catalog,
        &reservations_by_schedule,
        &billable_seconds_by_job,
        &execution_usage,
    )?;

    let mut summary = PollSummary {
        project: args.project.clone(),
        region: args.region.clone(),
        polled_at: now.format(&Rfc3339).unwrap_or_else(|_| now.to_string()),
        cost_cap_usd: args.cost_cap_usd,
        cost_metric_note: "billing/aggregated_cost is not directly queryable via Monitoring; \
            using run.googleapis.com/request_count over 24h as a proxy. Hook BigQuery billing export \
            to swap for true cost."
            .to_string(),
        services: Vec::with_capacity(services.len()),
        jobs: Vec::with_capacity(jobs.len()),
        schedules: schedule_usage,
        flags: Vec::new(),
    };

    for svc in services {
        let short_name = short_name(&svc.name);
        let proxy_metric_24h = requests_by_service.get(&short_name).copied().unwrap_or(0.0);
        // Naive pricing proxy: Cloud Run requests are negligible; the actual
        // bill is dominated by compute. Treat the request proxy as informational
        // only — `estimated_cost_usd` is None unless we wire BQ billing.
        let estimated_cost_usd: Option<f64> = None;
        let status = svc
            .terminal_condition
            .as_ref()
            .and_then(|c| c.state.clone())
            .unwrap_or_else(|| "UNKNOWN".to_string());
        let last_activity = svc.update_time.clone();

        let mut flags = Vec::new();
        if let Some(idle_secs) = idle_seconds(&last_activity, now)
            && idle_secs > IDLE_FLAG_THRESHOLD_SECS
            && status == "CONDITION_SUCCEEDED"
        {
            flags.push(format!("idle_{idle_secs}s_over_threshold"));
        }
        if let Some(cost) = estimated_cost_usd
            && cost > args.cost_cap_usd
        {
            flags.push(format!(
                "cost_exceeded_{:.2}_over_{:.2}",
                cost, args.cost_cap_usd
            ));
        }

        summary.services.push(ServiceReport {
            name: svc.name,
            short_name,
            latest_revision: svc.latest_ready_revision,
            status,
            last_activity,
            instance_count: 0, // True instance count requires the metric run.googleapis.com/container/instance_count — see TODO.
            proxy_metric_24h,
            estimated_cost_usd,
            flags,
        });
    }

    for job in jobs {
        let short_name = short_name(&job.name);
        let status = job
            .terminal_condition
            .as_ref()
            .and_then(|c| c.state.clone())
            .unwrap_or_else(|| "UNKNOWN".to_string());
        let latest_execution = job
            .latest_created_execution
            .as_ref()
            .and_then(|e| e.name.as_deref())
            .map(self::short_name);
        let last_activity = job
            .latest_created_execution
            .as_ref()
            .and_then(|e| e.completion_time.clone())
            .or(job.update_time);

        summary.jobs.push(JobReport {
            name: job.name,
            short_name,
            status,
            last_activity,
            latest_execution,
            flags: Vec::new(),
        });
    }

    // Roll service-level flags up to the top level so the report consumer can
    // alert without walking the full payload.
    for svc in &summary.services {
        for f in &svc.flags {
            summary.flags.push(format!("{}: {}", svc.short_name, f));
        }
    }
    for schedule in &summary.schedules {
        for flag in &schedule.flags {
            summary
                .flags
                .push(format!("schedule {}: {}", schedule.name, flag));
        }
    }

    Ok(summary)
}

async fn list_services(
    client: &Client,
    bearer: &str,
    project: &str,
    region: &str,
) -> Result<Vec<RunService>> {
    let url = format!("{CLOUD_RUN_BASE}/projects/{project}/locations/{region}/services");
    let resp = client
        .get(&url)
        .header("Authorization", bearer)
        .send()
        .await
        .with_context(|| format!("GET {url}"))?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(api_error("list_services", status, &body));
    }
    let parsed: ListServicesResponse = resp.json().await.context("decode list_services JSON")?;
    Ok(parsed.services)
}

async fn list_jobs(
    client: &Client,
    bearer: &str,
    project: &str,
    region: &str,
) -> Result<Vec<RunJob>> {
    let url = format!("{CLOUD_RUN_BASE}/projects/{project}/locations/{region}/jobs");
    let resp = client
        .get(&url)
        .header("Authorization", bearer)
        .send()
        .await
        .with_context(|| format!("GET {url}"))?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(api_error("list_jobs", status, &body));
    }
    let parsed: ListJobsResponse = resp.json().await.context("decode list_jobs JSON")?;
    Ok(parsed.jobs)
}

async fn list_executions(
    client: &Client,
    bearer: &str,
    project: &str,
    region: &str,
) -> Result<Vec<RunExecution>> {
    let url = format!("{CLOUD_RUN_BASE}/projects/{project}/locations/{region}/jobs/-/executions");
    let mut executions = Vec::new();
    let mut page_token: Option<String> = None;
    loop {
        let mut request = client
            .get(&url)
            .header("Authorization", bearer)
            .query(&[("pageSize", "1000")]);
        if let Some(token) = page_token.as_deref() {
            request = request.query(&[("pageToken", token)]);
        }
        let response = request.send().await.with_context(|| format!("GET {url}"))?;
        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            return Err(api_error("list_executions", status, &body));
        }
        let page: ListExecutionsResponse = response
            .json()
            .await
            .context("decode list_executions JSON")?;
        executions.extend(page.executions);
        page_token = page.next_page_token.filter(|token| !token.is_empty());
        if page_token.is_none() {
            return Ok(executions);
        }
    }
}

fn aggregate_execution_usage(
    executions: &[RunExecution],
    window_start: OffsetDateTime,
    window_end: OffsetDateTime,
) -> Result<ExecutionUsage> {
    let mut usage = ExecutionUsage::default();
    for execution in executions {
        let Some(start_raw) = execution.start_time.as_deref() else {
            continue;
        };
        let start = OffsetDateTime::parse(start_raw, &Rfc3339)
            .with_context(|| format!("invalid execution startTime: {start_raw}"))?;
        let end = match execution.completion_time.as_deref() {
            Some(raw) => OffsetDateTime::parse(raw, &Rfc3339)
                .with_context(|| format!("invalid execution completionTime: {raw}"))?,
            None => window_end,
        };
        let bounded_start = start.max(window_start);
        let bounded_end = end.min(window_end);
        if bounded_end <= bounded_start {
            continue;
        }
        let seconds = (bounded_end - bounded_start).as_seconds_f64();
        let job = short_name(&execution.job);
        *usage.total_seconds_by_job.entry(job.clone()).or_insert(0.0) += seconds;

        let schedule = execution
            .template
            .containers
            .iter()
            .flat_map(|container| &container.env)
            .find(|var| var.name == "LUPINE_SCHEDULE_NAME")
            .map(|var| var.value.trim())
            .filter(|value| !value.is_empty());
        if let Some(schedule) = schedule {
            *usage
                .scheduled_seconds_by_schedule_job
                .entry((schedule.to_string(), job))
                .or_insert(0.0) += seconds;
        }
    }
    Ok(usage)
}

/// Pulls 24h request-count totals per Cloud Run service via Cloud Monitoring.
/// Used as a cheap activity/cost proxy until we have BQ billing export wired.
async fn fetch_request_counts(
    client: &Client,
    bearer: &str,
    project: &str,
) -> Result<std::collections::BTreeMap<String, f64>> {
    let now = OffsetDateTime::now_utc();
    let start = now - time::Duration::hours(24);
    let url = format!("{MONITORING_BASE}/projects/{project}/timeSeries");

    let resp = client
        .get(&url)
        .header("Authorization", bearer)
        .query(&[
            (
                "filter",
                r#"metric.type="run.googleapis.com/request_count""#,
            ),
            ("interval.startTime", &start.format(&Rfc3339)?),
            ("interval.endTime", &now.format(&Rfc3339)?),
            ("aggregation.alignmentPeriod", "86400s"),
            ("aggregation.perSeriesAligner", "ALIGN_SUM"),
            ("aggregation.crossSeriesReducer", "REDUCE_SUM"),
            ("aggregation.groupByFields", "resource.label.service_name"),
        ])
        .send()
        .await
        .context("GET monitoring timeSeries")?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(api_error("monitoring.timeSeries", status, &body));
    }
    let parsed: TimeSeriesResponse = resp.json().await.context("decode timeSeries JSON")?;

    let mut out = std::collections::BTreeMap::new();
    for ts in parsed.time_series {
        let svc = ts
            .resource
            .as_ref()
            .and_then(|r| r.labels.get("service_name"))
            .cloned()
            .unwrap_or_else(|| "<unknown>".to_string());
        let total: f64 = ts.points.iter().map(|p| point_value(&p.value)).sum();
        *out.entry(svc).or_insert(0.0) += total;
    }
    Ok(out)
}

async fn fetch_billable_instance_seconds(
    client: &Client,
    bearer: &str,
    project: &str,
    region: &str,
) -> Result<BTreeMap<String, f64>> {
    let now = OffsetDateTime::now_utc();
    // The reservation ledger resets at UTC midnight; use the same window for
    // billable runtime so a daily cap never mixes two ledger days.
    let start = now.replace_time(time::Time::MIDNIGHT);
    let url = format!("{MONITORING_BASE}/projects/{project}/timeSeries");
    let filter = billable_instance_filter(region)?;
    let start_time = start.format(&Rfc3339)?;
    let end_time = now.format(&Rfc3339)?;
    let resp = client
        .get(&url)
        .header("Authorization", bearer)
        .query(&[
            ("filter", filter.as_str()),
            ("interval.startTime", start_time.as_str()),
            ("interval.endTime", end_time.as_str()),
            ("aggregation.alignmentPeriod", "86400s"),
            ("aggregation.perSeriesAligner", "ALIGN_SUM"),
            ("aggregation.crossSeriesReducer", "REDUCE_SUM"),
            ("aggregation.groupByFields", "resource.label.job_name"),
        ])
        .send()
        .await
        .context("GET billable instance timeSeries")?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(api_error(
            "monitoring.billable_instance_time",
            status,
            &body,
        ));
    }
    let parsed: TimeSeriesResponse = resp
        .json()
        .await
        .context("decode billable instance timeSeries JSON")?;
    let mut out = BTreeMap::new();
    for ts in parsed.time_series {
        let Some(job) = ts
            .resource
            .as_ref()
            .and_then(|resource| resource.labels.get("job_name"))
            .cloned()
        else {
            continue;
        };
        let total: f64 = ts
            .points
            .iter()
            .map(|point| point_value(&point.value))
            .sum();
        *out.entry(job).or_insert(0.0) += total;
    }
    Ok(out)
}

fn billable_instance_filter(region: &str) -> Result<String> {
    if region.is_empty()
        || !region
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
    {
        return Err(anyhow!("invalid Cloud Run region for metric filter"));
    }
    Ok(format!(
        r#"metric.type="run.googleapis.com/container/billable_instance_time" AND resource.type="cloud_run_job" AND resource.label.location="{region}""#
    ))
}

async fn fetch_schedule_reservations(
    client: &Client,
    bearer: &str,
    ledger_url: &str,
    policies: &[SchedulePolicy],
) -> Result<BTreeMap<String, ScheduleReservations>> {
    let rest = ledger_url
        .strip_prefix("gs://")
        .ok_or_else(|| anyhow!("budget ledger URL must use gs://"))?;
    let (bucket, prefix) = rest.split_once('/').unwrap_or((rest, ""));
    if bucket.is_empty() {
        return Err(anyhow!("budget ledger URL has no bucket"));
    }
    let day = OffsetDateTime::now_utc().date().to_string();
    let mut usage = BTreeMap::new();
    for policy in policies.iter().filter(|policy| policy.active) {
        let object = format!(
            "{}{}/{}.json",
            if prefix.trim_matches('/').is_empty() {
                String::new()
            } else {
                format!("{}/", prefix.trim_matches('/'))
            },
            policy.name,
            day
        );
        let mut url = reqwest::Url::parse(&format!(
            "https://storage.googleapis.com/storage/v1/b/{bucket}/o/"
        ))?;
        url.path_segments_mut()
            .map_err(|_| anyhow!("invalid GCS budget ledger URL"))?
            .pop_if_empty()
            .push(&object);
        url.query_pairs_mut().append_pair("alt", "media");
        let response = client
            .get(url)
            .header("Authorization", bearer)
            .send()
            .await
            .with_context(|| format!("GET budget ledger for {}", policy.name))?;
        if response.status() == StatusCode::NOT_FOUND {
            usage.insert(policy.name.clone(), ScheduleReservations::default());
            continue;
        }
        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            return Err(api_error("gcs.schedule_budget_ledger", status, &body));
        }
        let document: BudgetLedgerDocument = response
            .json()
            .await
            .context("decode schedule budget ledger JSON")?;
        if document.schema != "lupine.mlip.schedule_budget_ledger.v1"
            || document.schedule != policy.name
            || document.utc_date != day
            || !document.reserved_gpu_hours.is_finite()
            || document.reserved_gpu_hours < 0.0
        {
            return Err(anyhow!(
                "invalid schedule budget ledger for {}",
                policy.name
            ));
        }
        let mut reservation_sum = 0.0;
        let mut legacy_unattributed_gpu_hours = 0.0;
        for reservation in document.reservations {
            if !reservation.gpu_hours.is_finite() || reservation.gpu_hours <= 0.0 {
                return Err(anyhow!(
                    "invalid reservation provenance for schedule {}",
                    policy.name
                ));
            }
            reservation_sum += reservation.gpu_hours;
            if reservation.target_job.is_empty() {
                // Ledgers written before target-job provenance was added remain
                // readable for the rest of that UTC day. Execution env metadata
                // is authoritative for measured-runtime attribution.
                legacy_unattributed_gpu_hours += reservation.gpu_hours;
                continue;
            }
            if !reservation.target_job.starts_with("mlip-cell-") {
                return Err(anyhow!(
                    "invalid reservation target job for schedule {}",
                    policy.name
                ));
            }
        }
        if (reservation_sum - document.reserved_gpu_hours).abs() > 1e-6 {
            return Err(anyhow!(
                "reservation total mismatch for schedule {}",
                policy.name
            ));
        }
        usage.insert(
            policy.name.clone(),
            ScheduleReservations {
                reserved_gpu_hours: document.reserved_gpu_hours,
                legacy_unattributed_gpu_hours,
            },
        );
    }
    Ok(usage)
}

fn load_backend_catalog(path: &Path) -> Result<BTreeMap<String, String>> {
    let bytes = std::fs::read(path)
        .with_context(|| format!("reading backend catalog {}", path.display()))?;
    let catalog: BackendCatalog = serde_json::from_slice(&bytes)
        .with_context(|| format!("decoding backend catalog {}", path.display()))?;
    if catalog.schema != "lupine.mlip.backend_catalog.v1" {
        return Err(anyhow!(
            "unsupported backend catalog schema: {}",
            catalog.schema
        ));
    }
    let mut out = BTreeMap::new();
    let mut targets = BTreeSet::new();
    for backend in catalog.backends {
        if !backend.target_job.starts_with("mlip-cell-")
            || !targets.insert(backend.target_job.clone())
        {
            return Err(anyhow!(
                "invalid or duplicate backend catalog target: {}",
                backend.target_job
            ));
        }
        if out
            .insert(backend.mlip_id.clone(), backend.target_job)
            .is_some()
        {
            return Err(anyhow!("duplicate backend catalog id: {}", backend.mlip_id));
        }
    }
    Ok(out)
}

fn load_active_policies(dir: &Path) -> Result<Vec<SchedulePolicy>> {
    let cost_basis_path = dir.join("cost-basis.json");
    let cost_basis: CostBasis = serde_json::from_slice(
        &std::fs::read(&cost_basis_path)
            .with_context(|| format!("reading cost basis {}", cost_basis_path.display()))?,
    )
    .with_context(|| format!("decoding cost basis {}", cost_basis_path.display()))?;
    validate_cost_basis(&cost_basis, dir)?;
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading policy directory {}", dir.display()))?
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .filter(|path| {
            matches!(
                path.extension().and_then(|ext| ext.to_str()),
                Some("yml" | "yaml")
            )
        })
        .collect();
    paths.sort();
    let mut policies = Vec::new();
    for path in paths {
        let bytes = std::fs::read(&path)
            .with_context(|| format!("reading schedule policy {}", path.display()))?;
        let policy: SchedulePolicy = serde_yaml::from_slice(&bytes)
            .with_context(|| format!("decoding schedule policy {}", path.display()))?;
        if policy.active {
            let budget = policy
                .budget
                .as_ref()
                .ok_or_else(|| anyhow!("active policy {} has no budget", policy.name))?;
            validate_budget(&policy.name, budget, &cost_basis)?;
            policies.push(policy);
        }
    }
    Ok(policies)
}

fn validate_cost_basis(basis: &CostBasis, policy_dir: &Path) -> Result<()> {
    if basis.schema != "lupine.mlip.cost_basis.v1" || basis.status != "reconciled" {
        return Err(anyhow!(
            "cost basis {} is not a reconciled lupine.mlip.cost_basis.v1 artifact",
            basis.id
        ));
    }
    let ledger_path = policy_dir
        .ancestors()
        .map(|ancestor| ancestor.join(&basis.authoritative_ledger.path))
        .find(|candidate| candidate.is_file())
        .ok_or_else(|| {
            anyhow!(
                "authoritative cost ledger not found from policy directory {}: {}",
                policy_dir.display(),
                basis.authoritative_ledger.path.display()
            )
        })?;
    let ledger = std::fs::read(&ledger_path).with_context(|| {
        format!(
            "reading authoritative cost ledger {}",
            ledger_path.display()
        )
    })?;
    let actual_hash = format!("{:x}", Sha256::digest(&ledger));
    if actual_hash != basis.authoritative_ledger.sha256 {
        return Err(anyhow!(
            "authoritative cost ledger hash mismatch: expected {}, got {actual_hash}",
            basis.authoritative_ledger.sha256
        ));
    }
    if basis.authoritative_ledger.anchors == 0
        || !basis.authoritative_ledger.cloud_equivalent_usd.is_finite()
        || basis.authoritative_ledger.cloud_equivalent_usd <= 0.0
    {
        return Err(anyhow!("authoritative cost ledger unit is invalid"));
    }
    if basis.conflicting_claim.anchors == 0
        || !basis.conflicting_claim.cloud_equivalent_usd.is_finite()
        || basis.conflicting_claim.cloud_equivalent_usd <= 0.0
        || basis.conflicting_claim.disposition.trim().is_empty()
        || (basis.conflicting_claim.cloud_equivalent_usd
            - basis.authoritative_ledger.cloud_equivalent_usd)
            .abs()
            < f64::EPSILON
    {
        return Err(anyhow!(
            "cost basis must preserve the conflicting cost claim"
        ));
    }
    let expected_gate = basis.authoritative_ledger.cloud_equivalent_usd
        * basis.owner_note_gate.multiple_of_verified_unit;
    if (basis.owner_note_gate.multiple_of_verified_unit - 10.0).abs() > f64::EPSILON
        || (basis.owner_note_gate.usd - expected_gate).abs() > 0.005
    {
        return Err(anyhow!(
            "owner-note gate must equal 10x the verified cost unit (${expected_gate:.2})"
        ));
    }
    Ok(())
}

fn validate_budget(name: &str, budget: &PolicyBudget, basis: &CostBasis) -> Result<()> {
    if budget.cost_basis != basis.id {
        return Err(anyhow!(
            "active policy {name} references unknown cost basis {}",
            budget.cost_basis
        ));
    }
    if budget.retry != "no-silent-retry" || basis.owner_note_gate.silent_retry_allowed {
        return Err(anyhow!("active policy {name} must disable silent retry"));
    }
    let estimated_daily_usd = budget.daily_gpu_hours * basis.gpu_estimate.usd_per_gpu_hour;
    if basis.owner_note_gate.require_owner_note_above
        && estimated_daily_usd > basis.owner_note_gate.usd
        && budget
            .owner_note
            .as_deref()
            .is_none_or(|note| note.trim().is_empty())
    {
        return Err(anyhow!(
            "active policy {name} estimates ${estimated_daily_usd:.2}/day above the ${:.2} owner-note gate",
            basis.owner_note_gate.usd
        ));
    }
    Ok(())
}

fn build_schedule_usage(
    policies: &[SchedulePolicy],
    catalog: &BTreeMap<String, String>,
    reservations_by_schedule: &BTreeMap<String, ScheduleReservations>,
    billable_seconds_by_job: &BTreeMap<String, f64>,
    execution_usage: &ExecutionUsage,
) -> Result<Vec<ScheduleUsageReport>> {
    let mut reports = Vec::new();
    for policy in policies.iter().filter(|policy| policy.active) {
        let budget = policy
            .budget
            .as_ref()
            .ok_or_else(|| anyhow!("active policy {} has no budget", policy.name))?;
        if !budget.daily_gpu_hours.is_finite() || budget.daily_gpu_hours <= 0.0 {
            return Err(anyhow!(
                "active policy {} has invalid daily GPU-hour cap",
                policy.name
            ));
        }
        if budget.retry != "no-silent-retry" {
            return Err(anyhow!(
                "active policy {} must use no-silent-retry",
                policy.name
            ));
        }
        let mut jobs = BTreeSet::new();
        if policy.run.dynamic_catalog_backends {
            jobs.extend(catalog.values().cloned());
        } else {
            for backend in &policy.run.backends {
                jobs.insert(catalog.get(backend).cloned().ok_or_else(|| {
                    anyhow!("policy {} backend not in catalog: {backend}", policy.name)
                })?);
            }
        }
        let reservations = reservations_by_schedule
            .get(&policy.name)
            .ok_or_else(|| anyhow!("schedule {} reservation usage unavailable", policy.name))?;
        let mut measured_gpu_hours = 0.0;
        for job in &jobs {
            let billable_seconds = billable_seconds_by_job.get(job).copied().unwrap_or(0.0);
            if !billable_seconds.is_finite() || billable_seconds < 0.0 {
                return Err(anyhow!("invalid billable runtime for job {job}"));
            }
            if billable_seconds <= 0.0 {
                continue;
            }
            let total_execution_seconds = execution_usage
                .total_seconds_by_job
                .get(job)
                .copied()
                .unwrap_or(0.0);
            if total_execution_seconds <= 0.0 {
                return Err(anyhow!(
                    "billable runtime for job {job} has no execution provenance"
                ));
            }
            let scheduled_execution_seconds = execution_usage
                .scheduled_seconds_by_schedule_job
                .get(&(policy.name.clone(), job.clone()))
                .copied()
                .unwrap_or(0.0);
            if scheduled_execution_seconds > total_execution_seconds + f64::EPSILON {
                return Err(anyhow!(
                    "scheduled execution time exceeds total execution time for job {job}"
                ));
            }
            measured_gpu_hours +=
                billable_seconds / 3600.0 * scheduled_execution_seconds / total_execution_seconds;
        }
        // Reservations account for admitted/in-flight work before Cloud
        // Monitoring emits telemetry. Measured runtime takes over when actual
        // execution exceeds the fixed admission estimate.
        let gpu_hours_utc_day = measured_gpu_hours.max(reservations.reserved_gpu_hours);
        let mut flags = Vec::new();
        if reservations.legacy_unattributed_gpu_hours > 0.0 {
            flags.push("legacy_reservation_provenance_missing".to_string());
        }
        if gpu_hours_utc_day > budget.daily_gpu_hours {
            flags.push("gpu_hour_cap_exceeded".to_string());
        }
        reports.push(ScheduleUsageReport {
            name: policy.name.clone(),
            jobs: jobs.into_iter().collect(),
            reserved_gpu_hours: reservations.reserved_gpu_hours,
            gpu_hours_utc_day,
            daily_gpu_hour_cap: budget.daily_gpu_hours,
            utilization_percent: gpu_hours_utc_day / budget.daily_gpu_hours * 100.0,
            cost_basis: budget.cost_basis.clone(),
            retry: budget.retry.clone(),
            attribution: "measured_billable_runtime_reconciled_by_execution_env".into(),
            flags,
        });
    }
    Ok(reports)
}

fn point_value(v: &PointValue) -> f64 {
    if let Some(d) = v.double_value {
        return d;
    }
    if let Some(s) = &v.int64_value
        && let Ok(n) = s.parse::<f64>()
    {
        return n;
    }
    0.0
}

fn api_error(op: &str, status: StatusCode, body: &str) -> anyhow::Error {
    let snippet: String = body.chars().take(500).collect();
    anyhow!("{op}: HTTP {status}: {snippet}")
}

async fn post_report(client: &Client, url: &str, summary: &PollSummary) -> Result<()> {
    let resp = client
        .post(url)
        .json(summary)
        .send()
        .await
        .with_context(|| format!("POST {url}"))?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(api_error("report_post", status, &body));
    }
    Ok(())
}

fn print_human(s: &PollSummary) {
    println!(
        "== Cloud Run poll: project={} region={} @ {} ==",
        s.project, s.region, s.polled_at
    );
    println!(
        "cost cap: ${:.2} USD/24h  | metric note: {}",
        s.cost_cap_usd, s.cost_metric_note
    );
    println!();
    println!("Services ({}):", s.services.len());
    if s.services.is_empty() {
        println!("  (none)");
    }
    for svc in &s.services {
        println!(
            "  - {} | status={} | rev={} | last_activity={} | req_24h={:.0} | flags={}",
            svc.short_name,
            svc.status,
            svc.latest_revision.as_deref().unwrap_or("-"),
            svc.last_activity.as_deref().unwrap_or("-"),
            svc.proxy_metric_24h,
            if svc.flags.is_empty() {
                "ok".to_string()
            } else {
                svc.flags.join(",")
            }
        );
    }
    println!();
    println!("Jobs ({}):", s.jobs.len());
    if s.jobs.is_empty() {
        println!("  (none)");
    }
    for job in &s.jobs {
        println!(
            "  - {} | status={} | last_activity={} | latest_execution={}",
            job.short_name,
            job.status,
            job.last_activity.as_deref().unwrap_or("-"),
            job.latest_execution.as_deref().unwrap_or("-")
        );
    }
    println!();
    println!("Active schedule GPU budgets ({}):", s.schedules.len());
    if s.schedules.is_empty() {
        println!("  (none)");
    }
    for schedule in &s.schedules {
        println!(
            "  - {} | gpu_hours_utc_day={:.4}/{:.4} ({:.1}%) | reserved={:.4} | jobs={} | cost_basis={} | retry={} | attribution={} | flags={}",
            schedule.name,
            schedule.gpu_hours_utc_day,
            schedule.daily_gpu_hour_cap,
            schedule.utilization_percent,
            schedule.reserved_gpu_hours,
            schedule.jobs.join(","),
            schedule.cost_basis,
            schedule.retry,
            schedule.attribution,
            if schedule.flags.is_empty() {
                "ok".to_string()
            } else {
                schedule.flags.join(",")
            }
        );
    }
    if !s.flags.is_empty() {
        println!();
        println!("FLAGS:");
        for f in &s.flags {
            println!("  ! {f}");
        }
    }
}

/// "projects/p/locations/r/services/foo" -> "foo".
/// Also handles execution names like ".../jobs/foo/executions/foo-abc" -> "foo-abc".
fn short_name(full: &str) -> String {
    full.rsplit('/').next().unwrap_or(full).to_string()
}

/// Returns the elapsed seconds between `ts` (RFC3339) and `now`, if parsable.
fn idle_seconds(ts: &Option<String>, now: OffsetDateTime) -> Option<i64> {
    let raw = ts.as_deref()?;
    let parsed = OffsetDateTime::parse(raw, &Rfc3339).ok()?;
    Some((now - parsed).whole_seconds())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn short_name_strips_resource_prefix() {
        assert_eq!(
            short_name("projects/p/locations/us-central1/services/lupine-site"),
            "lupine-site"
        );
        assert_eq!(short_name("bare"), "bare");
        assert_eq!(
            short_name("projects/p/locations/us-central1/jobs/foo/executions/foo-abc"),
            "foo-abc"
        );
    }

    #[test]
    fn point_value_prefers_double_then_int_string() {
        let pv = PointValue {
            double_value: Some(12.5),
            int64_value: Some("99".into()),
        };
        assert!((point_value(&pv) - 12.5).abs() < 1e-9);

        let pv = PointValue {
            double_value: None,
            int64_value: Some("42".into()),
        };
        assert!((point_value(&pv) - 42.0).abs() < 1e-9);

        let pv = PointValue {
            double_value: None,
            int64_value: None,
        };
        assert_eq!(point_value(&pv), 0.0);
    }

    #[test]
    fn monitoring_response_decodes_google_camel_case_fields() {
        let parsed: TimeSeriesResponse = serde_json::from_str(
            r#"{"timeSeries":[{"resource":{"labels":{"job_name":"mlip-cell-mace"}},"points":[{"value":{"doubleValue":58.5}}]}]}"#,
        )
        .unwrap();
        assert_eq!(parsed.time_series.len(), 1);
        assert!((point_value(&parsed.time_series[0].points[0].value) - 58.5).abs() < 1e-9);
    }

    #[test]
    fn legacy_reservation_without_target_job_remains_readable() {
        let reservation: BudgetReservation = serde_json::from_str(
            r#"{"task_name":"legacy-task","gpu_hours":0.05,"reserved_at":"2026-08-01T00:00:00Z"}"#,
        )
        .unwrap();
        assert!(reservation.target_job.is_empty());
        assert_eq!(reservation.gpu_hours, 0.05);
    }

    #[test]
    fn idle_seconds_handles_missing_and_malformed_timestamps() {
        let now = OffsetDateTime::now_utc();
        assert_eq!(idle_seconds(&None, now), None);
        assert_eq!(idle_seconds(&Some("not-a-date".into()), now), None);

        let past = (now - time::Duration::seconds(700))
            .format(&Rfc3339)
            .unwrap();
        let elapsed = idle_seconds(&Some(past), now).unwrap();
        assert!((690..=710).contains(&elapsed));
    }

    #[test]
    fn schedule_usage_sums_catalog_jobs_and_flags_cap_excess() {
        let policy = SchedulePolicy {
            name: "nightly-baseline".into(),
            active: true,
            run: PolicyRun {
                backends: vec!["mace-mp-0".into(), "chgnet".into()],
                dynamic_catalog_backends: false,
            },
            budget: Some(PolicyBudget {
                daily_gpu_hours: 1.0,
                cost_basis: "z1-union-2026-07-24".into(),
                retry: "no-silent-retry".into(),
                owner_note: None,
            }),
        };
        let catalog = std::collections::BTreeMap::from([
            ("mace-mp-0".into(), "mlip-cell-mace".into()),
            ("chgnet".into(), "mlip-cell-chgnet".into()),
        ]);
        let reservations = BTreeMap::from([(
            "nightly-baseline".into(),
            ScheduleReservations {
                reserved_gpu_hours: 2.0,
                ..Default::default()
            },
        )]);
        let usage = build_schedule_usage(
            &[policy],
            &catalog,
            &reservations,
            &BTreeMap::new(),
            &ExecutionUsage::default(),
        )
        .unwrap();
        assert_eq!(usage.len(), 1);
        assert!((usage[0].gpu_hours_utc_day - 2.0).abs() < 1e-9);
        assert_eq!(usage[0].daily_gpu_hour_cap, 1.0);
        assert!(
            usage[0]
                .flags
                .iter()
                .any(|flag| flag == "gpu_hour_cap_exceeded")
        );
    }

    #[test]
    fn schedule_usage_reconciles_reservations_to_measured_billable_runtime() {
        let policy = SchedulePolicy {
            name: "nightly-baseline".into(),
            active: true,
            run: PolicyRun {
                backends: vec!["mace-mp-0".into(), "chgnet".into()],
                dynamic_catalog_backends: false,
            },
            budget: Some(PolicyBudget {
                daily_gpu_hours: 3.0,
                cost_basis: "z1-union-2026-07-24".into(),
                retry: "no-silent-retry".into(),
                owner_note: None,
            }),
        };
        let catalog = BTreeMap::from([
            ("mace-mp-0".into(), "mlip-cell-mace".into()),
            ("chgnet".into(), "mlip-cell-chgnet".into()),
        ]);
        let reservations = BTreeMap::from([(
            "nightly-baseline".into(),
            ScheduleReservations {
                reserved_gpu_hours: 0.1,
                ..Default::default()
            },
        )]);
        let billable_seconds = BTreeMap::from([
            ("mlip-cell-mace".into(), 3600.0),
            ("mlip-cell-chgnet".into(), 1800.0),
        ]);
        let execution_usage = ExecutionUsage {
            total_seconds_by_job: billable_seconds.clone(),
            scheduled_seconds_by_schedule_job: BTreeMap::from([
                (("nightly-baseline".into(), "mlip-cell-mace".into()), 3600.0),
                (
                    ("nightly-baseline".into(), "mlip-cell-chgnet".into()),
                    1800.0,
                ),
            ]),
        };

        let usage = build_schedule_usage(
            &[policy],
            &catalog,
            &reservations,
            &billable_seconds,
            &execution_usage,
        )
        .unwrap();

        assert!((usage[0].gpu_hours_utc_day - 1.5).abs() < 1e-9);
        assert_eq!(usage[0].reserved_gpu_hours, 0.1);
        assert_eq!(
            usage[0].attribution,
            "measured_billable_runtime_reconciled_by_execution_env"
        );
    }

    #[test]
    fn execution_provenance_excludes_manual_runtime_from_schedule_usage() {
        let start = OffsetDateTime::parse("2026-08-01T00:00:00Z", &Rfc3339).unwrap();
        let end = OffsetDateTime::parse("2026-08-01T03:00:00Z", &Rfc3339).unwrap();
        let execution =
            |start_time: &str, completion_time: &str, schedule: Option<&str>| RunExecution {
                job: "projects/p/locations/us-central1/jobs/mlip-cell-mace".into(),
                start_time: Some(start_time.into()),
                completion_time: Some(completion_time.into()),
                template: ExecutionTaskTemplate {
                    containers: vec![ExecutionContainer {
                        env: schedule
                            .map(|value| {
                                vec![ExecutionEnvVar {
                                    name: "LUPINE_SCHEDULE_NAME".into(),
                                    value: value.into(),
                                }]
                            })
                            .unwrap_or_default(),
                    }],
                },
            };
        let executions = [
            execution(
                "2026-08-01T00:00:00Z",
                "2026-08-01T01:00:00Z",
                Some("nightly-baseline"),
            ),
            execution("2026-08-01T01:00:00Z", "2026-08-01T02:00:00Z", None),
        ];
        let execution_usage = aggregate_execution_usage(&executions, start, end).unwrap();
        assert_eq!(
            execution_usage.total_seconds_by_job["mlip-cell-mace"],
            7200.0
        );

        let policy = SchedulePolicy {
            name: "nightly-baseline".into(),
            active: true,
            run: PolicyRun {
                backends: vec!["mace-mp-0".into()],
                dynamic_catalog_backends: false,
            },
            budget: Some(PolicyBudget {
                daily_gpu_hours: 3.0,
                cost_basis: "z1-union-2026-07-24".into(),
                retry: "no-silent-retry".into(),
                owner_note: None,
            }),
        };
        let catalog = BTreeMap::from([("mace-mp-0".into(), "mlip-cell-mace".into())]);
        let reservations = BTreeMap::from([(
            "nightly-baseline".into(),
            ScheduleReservations {
                reserved_gpu_hours: 0.05,
                ..Default::default()
            },
        )]);
        let billable_seconds = BTreeMap::from([("mlip-cell-mace".into(), 3600.0)]);

        let usage = build_schedule_usage(
            &[policy],
            &catalog,
            &reservations,
            &billable_seconds,
            &execution_usage,
        )
        .unwrap();

        assert!((usage[0].gpu_hours_utc_day - 0.5).abs() < 1e-9);
    }

    #[test]
    fn shared_job_billable_runtime_is_allocated_once_across_schedules() {
        let make_policy = |name: &str| SchedulePolicy {
            name: name.into(),
            active: true,
            run: PolicyRun {
                backends: vec!["mace-mp-0".into()],
                dynamic_catalog_backends: false,
            },
            budget: Some(PolicyBudget {
                daily_gpu_hours: 3.0,
                cost_basis: "z1-union-2026-07-24".into(),
                retry: "no-silent-retry".into(),
                owner_note: None,
            }),
        };
        let policies = [
            make_policy("nightly-baseline"),
            make_policy("on-proof-complete"),
        ];
        let catalog = BTreeMap::from([("mace-mp-0".into(), "mlip-cell-mace".into())]);
        let reservations = BTreeMap::from([
            (
                "nightly-baseline".into(),
                ScheduleReservations {
                    reserved_gpu_hours: 0.15,
                    ..Default::default()
                },
            ),
            (
                "on-proof-complete".into(),
                ScheduleReservations {
                    reserved_gpu_hours: 0.05,
                    ..Default::default()
                },
            ),
        ]);
        let billable_seconds = BTreeMap::from([("mlip-cell-mace".into(), 3600.0)]);
        let execution_usage = ExecutionUsage {
            total_seconds_by_job: BTreeMap::from([("mlip-cell-mace".into(), 3600.0)]),
            scheduled_seconds_by_schedule_job: BTreeMap::from([
                (("nightly-baseline".into(), "mlip-cell-mace".into()), 2700.0),
                (("on-proof-complete".into(), "mlip-cell-mace".into()), 900.0),
            ]),
        };

        let usage = build_schedule_usage(
            &policies,
            &catalog,
            &reservations,
            &billable_seconds,
            &execution_usage,
        )
        .unwrap();

        let total: f64 = usage.iter().map(|item| item.gpu_hours_utc_day).sum();
        assert!((total - 1.0).abs() < 1e-9);
        assert!((usage[0].gpu_hours_utc_day - 0.75).abs() < 1e-9);
        assert!((usage[1].gpu_hours_utc_day - 0.25).abs() < 1e-9);
    }

    #[test]
    fn schedule_usage_fails_closed_when_reservation_usage_is_missing() {
        let policy = SchedulePolicy {
            name: "on-proof-complete".into(),
            active: true,
            run: PolicyRun {
                backends: vec!["mace-mp-0".into()],
                dynamic_catalog_backends: true,
            },
            budget: Some(PolicyBudget {
                daily_gpu_hours: 1.0,
                cost_basis: "z1-union-2026-07-24".into(),
                retry: "no-silent-retry".into(),
                owner_note: None,
            }),
        };
        let catalog = BTreeMap::from([("mace-mp-0".into(), "mlip-cell-mace".into())]);
        let error = build_schedule_usage(
            &[policy],
            &catalog,
            &BTreeMap::new(),
            &BTreeMap::new(),
            &ExecutionUsage::default(),
        )
        .unwrap_err();
        assert!(error.to_string().contains("reservation usage unavailable"));
    }

    #[test]
    fn billable_metric_filter_is_region_scoped_and_rejects_injection() {
        let filter = billable_instance_filter("us-central1").unwrap();
        assert!(filter.contains("resource.label.location=\"us-central1\""));
        assert!(billable_instance_filter("us-central1\" OR true").is_err());
    }

    #[test]
    fn policy_over_ten_verified_units_requires_owner_note() {
        let basis = CostBasis {
            schema: "lupine.mlip.cost_basis.v1".into(),
            id: "z1-union-2026-07-24".into(),
            status: "reconciled".into(),
            authoritative_ledger: AuthoritativeLedger {
                path: "unused-in-this-test".into(),
                sha256: "unused-in-this-test".into(),
                anchors: 129,
                cloud_equivalent_usd: 14.65,
            },
            conflicting_claim: ConflictingClaim {
                anchors: 129,
                cloud_equivalent_usd: 4.65,
                disposition: "unsupported".into(),
            },
            gpu_estimate: GpuEstimate {
                usd_per_gpu_hour: 0.65,
            },
            owner_note_gate: OwnerNoteGate {
                multiple_of_verified_unit: 10.0,
                usd: 146.5,
                require_owner_note_above: true,
                silent_retry_allowed: false,
            },
        };
        let budget = PolicyBudget {
            daily_gpu_hours: 226.0,
            cost_basis: basis.id.clone(),
            retry: "no-silent-retry".into(),
            owner_note: None,
        };
        assert!(validate_budget("too-large", &budget, &basis).is_err());
    }

    #[test]
    fn checked_in_active_policies_require_verified_ledger_hash() {
        let policy_dir =
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../gcp/mlip-cell-runner/policies");
        let policies = load_active_policies(&policy_dir).unwrap();
        let names: BTreeSet<_> = policies.iter().map(|policy| policy.name.as_str()).collect();
        assert_eq!(
            names,
            BTreeSet::from(["nightly-baseline", "on-proof-complete"])
        );
    }
}
