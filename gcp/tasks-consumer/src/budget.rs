use std::collections::BTreeSet;
use std::sync::Arc;

use anyhow::{anyhow, bail, Context};
use axum::async_trait;
use serde::{Deserialize, Serialize};
use time::{format_description::well_known::Iso8601, OffsetDateTime};
use tokio::sync::Mutex;

const POLICY_SCHEMA: &str = "lupine.mlip.run_policy.v1";
const LEDGER_SCHEMA: &str = "lupine.mlip.schedule_budget_ledger.v1";
const METADATA_TOKEN_URL: &str =
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token";

#[derive(Debug, Clone, Deserialize)]
pub struct SchedulePolicy {
    pub schema: String,
    pub name: String,
    #[serde(default)]
    pub active: bool,
    pub run: PolicyRun,
    pub budget: PolicyBudget,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PolicyRun {
    #[serde(default)]
    pub backends: Vec<String>,
    #[serde(default)]
    pub allow_dynamic_backend: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PolicyBudget {
    pub daily_gpu_hours: f64,
    pub reservation_gpu_hours: f64,
    pub retry: String,
}

impl SchedulePolicy {
    pub fn validate(&self, requested_backend: Option<&str>) -> anyhow::Result<()> {
        if self.schema != POLICY_SCHEMA || !self.active {
            bail!(
                "schedule policy {} is not an active {POLICY_SCHEMA} policy",
                self.name
            );
        }
        if !valid_schedule_name(&self.name) {
            bail!("unsafe schedule policy name: {}", self.name);
        }
        if !self.budget.daily_gpu_hours.is_finite()
            || self.budget.daily_gpu_hours <= 0.0
            || !self.budget.reservation_gpu_hours.is_finite()
            || self.budget.reservation_gpu_hours <= 0.0
            || self.budget.reservation_gpu_hours > self.budget.daily_gpu_hours
        {
            bail!(
                "schedule policy {} has invalid GPU-hour admission values",
                self.name
            );
        }
        if self.budget.retry != "no-silent-retry" {
            bail!(
                "schedule policy {} does not disable silent retry",
                self.name
            );
        }
        if let Some(backend) = requested_backend {
            if !self.run.allow_dynamic_backend
                && !self.run.backends.iter().any(|allowed| allowed == backend)
            {
                bail!(
                    "backend {backend} is not permitted by schedule {}",
                    self.name
                );
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct Admission {
    pub schedule: String,
    pub reservation_gpu_hours: f64,
    pub reserved_gpu_hours: f64,
    pub daily_gpu_hour_cap: f64,
}

#[async_trait]
pub trait BudgetLedger: Send + Sync {
    async fn reserve(&self, policy: &SchedulePolicy, task_name: &str) -> anyhow::Result<Admission>;
}

pub struct GcsBudgetLedger {
    client: reqwest::Client,
    bucket: String,
    prefix: String,
}

impl GcsBudgetLedger {
    pub fn from_url(url: &str) -> anyhow::Result<Self> {
        let rest = url
            .strip_prefix("gs://")
            .ok_or_else(|| anyhow!("budget ledger URL must use gs://"))?;
        let (bucket, prefix) = rest.split_once('/').unwrap_or((rest, ""));
        if bucket.is_empty() {
            bail!("budget ledger URL has no bucket");
        }
        Ok(Self {
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(15))
                .build()?,
            bucket: bucket.to_string(),
            prefix: prefix.trim_matches('/').to_string(),
        })
    }

    async fn token(&self) -> anyhow::Result<String> {
        #[derive(Deserialize)]
        struct TokenResponse {
            access_token: String,
        }
        Ok(self
            .client
            .get(METADATA_TOKEN_URL)
            .header("Metadata-Flavor", "Google")
            .send()
            .await
            .context("fetching metadata token for budget ledger")?
            .error_for_status()?
            .json::<TokenResponse>()
            .await?
            .access_token)
    }

    fn object_name(&self, schedule: &str, day: &str) -> String {
        let leaf = format!("{schedule}/{day}.json");
        if self.prefix.is_empty() {
            leaf
        } else {
            format!("{}/{leaf}", self.prefix)
        }
    }

    async fn read(
        &self,
        token: &str,
        object: &str,
    ) -> anyhow::Result<(Option<BudgetLedgerDocument>, u64)> {
        let mut metadata_url = reqwest::Url::parse(&format!(
            "https://storage.googleapis.com/storage/v1/b/{}/o/",
            self.bucket
        ))?;
        metadata_url
            .path_segments_mut()
            .map_err(|_| anyhow!("invalid GCS metadata base URL"))?
            .pop_if_empty()
            .push(object);
        let response = self
            .client
            .get(metadata_url)
            .bearer_auth(token)
            .send()
            .await?;
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Ok((None, 0));
        }
        let metadata: ObjectMetadata = response.error_for_status()?.json().await?;
        let generation = metadata.generation.parse::<u64>()?;

        let mut media_url = reqwest::Url::parse(&format!(
            "https://storage.googleapis.com/storage/v1/b/{}/o/",
            self.bucket
        ))?;
        media_url
            .path_segments_mut()
            .map_err(|_| anyhow!("invalid GCS media base URL"))?
            .pop_if_empty()
            .push(object);
        media_url.query_pairs_mut().append_pair("alt", "media");
        let document = self
            .client
            .get(media_url)
            .bearer_auth(token)
            .send()
            .await?
            .error_for_status()?
            .json::<BudgetLedgerDocument>()
            .await?;
        Ok((Some(document), generation))
    }

    async fn write(
        &self,
        token: &str,
        object: &str,
        expected_generation: u64,
        document: &BudgetLedgerDocument,
    ) -> anyhow::Result<bool> {
        let url = format!(
            "https://storage.googleapis.com/upload/storage/v1/b/{}/o",
            self.bucket
        );
        let response = self
            .client
            .post(url)
            .bearer_auth(token)
            .query(&[
                ("uploadType", "media".to_string()),
                ("name", object.to_string()),
                ("ifGenerationMatch", expected_generation.to_string()),
            ])
            .json(document)
            .send()
            .await?;
        if response.status() == reqwest::StatusCode::PRECONDITION_FAILED {
            return Ok(false);
        }
        response.error_for_status()?;
        Ok(true)
    }
}

#[async_trait]
impl BudgetLedger for GcsBudgetLedger {
    async fn reserve(&self, policy: &SchedulePolicy, task_name: &str) -> anyhow::Result<Admission> {
        let token = self.token().await?;
        let day = OffsetDateTime::now_utc().date().to_string();
        let object = self.object_name(&policy.name, &day);
        for _ in 0..8 {
            let (existing, generation) = self.read(&token, &object).await?;
            let mut document = existing.unwrap_or_else(|| BudgetLedgerDocument {
                schema: LEDGER_SCHEMA.into(),
                schedule: policy.name.clone(),
                utc_date: day.clone(),
                reserved_gpu_hours: 0.0,
                reservations: Vec::new(),
            });
            document.validate(&policy.name, &day)?;
            if document
                .reservations
                .iter()
                .any(|item| item.task_name == task_name)
            {
                return Ok(admission(policy, document.reserved_gpu_hours));
            }
            let next = document.reserved_gpu_hours + policy.budget.reservation_gpu_hours;
            if next > policy.budget.daily_gpu_hours + f64::EPSILON {
                bail!(
                    "schedule {} daily GPU-hour cap exhausted: {:.4} + {:.4} > {:.4}",
                    policy.name,
                    document.reserved_gpu_hours,
                    policy.budget.reservation_gpu_hours,
                    policy.budget.daily_gpu_hours
                );
            }
            document.reserved_gpu_hours = next;
            document.reservations.push(Reservation {
                task_name: task_name.to_string(),
                gpu_hours: policy.budget.reservation_gpu_hours,
                reserved_at: OffsetDateTime::now_utc()
                    .format(&Iso8601::DEFAULT)
                    .unwrap_or_else(|_| OffsetDateTime::now_utc().to_string()),
            });
            if self.write(&token, &object, generation, &document).await? {
                return Ok(admission(policy, next));
            }
        }
        bail!("budget ledger remained contended after 8 atomic CAS attempts")
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetLedgerDocument {
    pub schema: String,
    pub schedule: String,
    pub utc_date: String,
    pub reserved_gpu_hours: f64,
    pub reservations: Vec<Reservation>,
}

impl BudgetLedgerDocument {
    fn validate(&self, schedule: &str, day: &str) -> anyhow::Result<()> {
        if self.schema != LEDGER_SCHEMA || self.schedule != schedule || self.utc_date != day {
            bail!("budget ledger identity/schema mismatch");
        }
        if !self.reserved_gpu_hours.is_finite() || self.reserved_gpu_hours < 0.0 {
            bail!("budget ledger has invalid reserved GPU hours");
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reservation {
    pub task_name: String,
    pub gpu_hours: f64,
    pub reserved_at: String,
}

#[derive(Debug, Deserialize)]
struct ObjectMetadata {
    generation: String,
}

fn admission(policy: &SchedulePolicy, reserved: f64) -> Admission {
    Admission {
        schedule: policy.name.clone(),
        reservation_gpu_hours: policy.budget.reservation_gpu_hours,
        reserved_gpu_hours: reserved,
        daily_gpu_hour_cap: policy.budget.daily_gpu_hours,
    }
}

pub async fn load_policy(base: &str, schedule: &str) -> anyhow::Result<SchedulePolicy> {
    if !valid_schedule_name(schedule) {
        bail!("invalid schedule name: {schedule}");
    }
    let source = format!("{}/{}.yml", base.trim_end_matches('/'), schedule);
    let bytes = super::catalog::read_object(&source).await?;
    let policy: SchedulePolicy = serde_yaml::from_slice(&bytes)
        .with_context(|| format!("decoding schedule policy {source}"))?;
    if policy.name != schedule {
        bail!(
            "schedule policy identity mismatch: requested {schedule}, got {}",
            policy.name
        );
    }
    Ok(policy)
}

pub fn valid_schedule_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 63
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
        && !value.starts_with('-')
        && !value.ends_with('-')
}

#[derive(Default)]
pub struct MemoryBudgetLedger {
    reservations: Mutex<(f64, BTreeSet<String>)>,
}

#[async_trait]
impl BudgetLedger for MemoryBudgetLedger {
    async fn reserve(&self, policy: &SchedulePolicy, task_name: &str) -> anyhow::Result<Admission> {
        let mut state = self.reservations.lock().await;
        if state.1.contains(task_name) {
            return Ok(admission(policy, state.0));
        }
        let next = state.0 + policy.budget.reservation_gpu_hours;
        if next > policy.budget.daily_gpu_hours + f64::EPSILON {
            bail!("schedule {} daily GPU-hour cap exhausted", policy.name);
        }
        state.0 = next;
        state.1.insert(task_name.to_string());
        Ok(admission(policy, next))
    }
}

pub fn memory_ledger() -> Arc<dyn BudgetLedger> {
    Arc::new(MemoryBudgetLedger::default())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn policy(cap: f64, reservation: f64) -> SchedulePolicy {
        SchedulePolicy {
            schema: POLICY_SCHEMA.into(),
            name: "nightly-baseline".into(),
            active: true,
            run: PolicyRun {
                backends: vec!["mace-mp-0".into()],
                allow_dynamic_backend: false,
            },
            budget: PolicyBudget {
                daily_gpu_hours: cap,
                reservation_gpu_hours: reservation,
                retry: "no-silent-retry".into(),
            },
        }
    }

    #[tokio::test]
    async fn concurrent_reservations_never_exceed_cap() {
        let ledger = Arc::new(MemoryBudgetLedger::default());
        let policy = Arc::new(policy(1.0, 0.25));
        let mut tasks = Vec::new();
        for index in 0..12 {
            let ledger = ledger.clone();
            let policy = policy.clone();
            tasks.push(tokio::spawn(async move {
                ledger.reserve(&policy, &format!("task-{index}")).await
            }));
        }
        let mut accepted = 0;
        for task in tasks {
            if task.await.unwrap().is_ok() {
                accepted += 1;
            }
        }
        assert_eq!(accepted, 4);
    }

    #[tokio::test]
    async fn duplicate_task_is_idempotent() {
        let ledger = MemoryBudgetLedger::default();
        let policy = policy(1.0, 0.5);
        let first = ledger.reserve(&policy, "same").await.unwrap();
        let second = ledger.reserve(&policy, "same").await.unwrap();
        assert_eq!(first.reserved_gpu_hours, 0.5);
        assert_eq!(second.reserved_gpu_hours, 0.5);
    }
}
