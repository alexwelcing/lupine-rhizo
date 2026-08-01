use std::collections::BTreeMap;

use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::budget::Admission;
use crate::CloudCellTelemetry;

#[axum::async_trait]
pub trait TraceEmitter: Send + Sync {
    async fn emit(&self, span: &CloudCellSpan) -> anyhow::Result<()>;
}

pub struct NoopTraceEmitter;

#[axum::async_trait]
impl TraceEmitter for NoopTraceEmitter {
    async fn emit(&self, _span: &CloudCellSpan) -> anyhow::Result<()> {
        Ok(())
    }
}

pub struct HttpTraceEmitter {
    client: reqwest::Client,
    endpoint: String,
    token: String,
    project: String,
}

impl HttpTraceEmitter {
    pub fn new(endpoint: String, token: String, project: String) -> anyhow::Result<Self> {
        let endpoint = endpoint.trim_end_matches('/');
        let endpoint = if endpoint.ends_with("/v1/traces") {
            endpoint.to_string()
        } else {
            format!("{endpoint}/v1/traces")
        };
        Ok(Self {
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(10))
                .build()?,
            endpoint,
            token,
            project,
        })
    }
}

#[axum::async_trait]
impl TraceEmitter for HttpTraceEmitter {
    async fn emit(&self, span: &CloudCellSpan) -> anyhow::Result<()> {
        self.client
            .post(&self.endpoint)
            .header("x-relay-token", &self.token)
            .header("content-type", "application/json")
            .json(&span.otlp_json(&self.project))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
    }
}

pub struct CloudCellSpan {
    identity: CloudCellTelemetry,
    target_job: String,
    schedule_name: String,
    dispatch_status: String,
    reservation_gpu_hours: f64,
    reserved_gpu_hours: f64,
    daily_gpu_hour_cap: f64,
}

impl CloudCellSpan {
    pub fn admitted(
        identity: &CloudCellTelemetry,
        target_job: &str,
        admission: &Admission,
    ) -> Self {
        Self {
            identity: identity.clone(),
            target_job: target_job.to_string(),
            schedule_name: admission.schedule.clone(),
            dispatch_status: "admitted".into(),
            reservation_gpu_hours: admission.reservation_gpu_hours,
            reserved_gpu_hours: admission.reserved_gpu_hours,
            daily_gpu_hour_cap: admission.daily_gpu_hour_cap,
        }
    }

    pub fn attributes(&self) -> BTreeMap<String, Value> {
        BTreeMap::from([
            ("mlip.schema".into(), json!(self.identity.schema)),
            ("mlip.origin".into(), json!(self.identity.origin)),
            (
                "mlip.correlation_id".into(),
                json!(self.identity.correlation_id),
            ),
            ("mlip.cloud_run_id".into(), json!(self.identity.run_id)),
            ("mlip.cell_id".into(), json!(self.identity.cell_id)),
            ("mlip.triplet.row_id".into(), json!(self.identity.row_id)),
            ("mlip.triplet.mlip_id".into(), json!(self.identity.mlip_id)),
            ("mlip.schedule.name".into(), json!(self.schedule_name)),
            ("mlip.dispatch.status".into(), json!(self.dispatch_status)),
            ("mlip.dispatch.target_job".into(), json!(self.target_job)),
            (
                "mlip.cost.reserved_gpu_hours".into(),
                json!(self.reserved_gpu_hours),
            ),
            (
                "mlip.cost.reservation_gpu_hours".into(),
                json!(self.reservation_gpu_hours),
            ),
            (
                "mlip.cost.daily_gpu_hour_cap".into(),
                json!(self.daily_gpu_hour_cap),
            ),
        ])
    }

    pub fn otlp_json(&self, project: &str) -> Value {
        let seed = format!(
            "{}\0{}\0{}",
            self.identity.correlation_id, self.identity.run_id, self.identity.cell_id
        );
        let digest = Sha256::digest(seed.as_bytes());
        let trace_id = hex(&digest[..16]);
        let span_id = hex(&digest[16..24]);
        let now = time::OffsetDateTime::now_utc()
            .unix_timestamp_nanos()
            .to_string();
        let attributes = self
            .attributes()
            .into_iter()
            .map(|(key, value)| json!({"key": key, "value": otlp_value(value)}))
            .collect::<Vec<_>>();
        json!({
            "resourceSpans": [{
                "resource": {"attributes": [
                    {"key": "service.name", "value": {"stringValue": "tasks-consumer"}},
                    {"key": "openinference.project.name", "value": {"stringValue": project}}
                ]},
                "scopeSpans": [{
                    "scope": {"name": "mlip.flywheel"},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": "mlip.flywheel.cloud_cell",
                        "kind": 1,
                        "startTimeUnixNano": now,
                        "endTimeUnixNano": now,
                        "attributes": attributes,
                        "status": {"code": 1}
                    }]
                }]
            }]
        })
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn otlp_value(value: Value) -> Value {
    match value {
        Value::Bool(value) => json!({"boolValue": value}),
        Value::Number(value) => json!({"doubleValue": value.as_f64().unwrap_or_default()}),
        Value::String(value) => json!({"stringValue": value}),
        other => json!({"stringValue": other.to_string()}),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::budget::Admission;
    use crate::CloudCellTelemetry;

    fn identity() -> CloudCellTelemetry {
        CloudCellTelemetry {
            schema: "lupine.mlip.cloud_cell_span.v1".into(),
            origin: "cloud".into(),
            correlation_id: "workflow-nightly-1".into(),
            run_id: "nightly-run-1".into(),
            cell_id: "nightly-run-1:baseline:energy_volume:mace-mp-0".into(),
            row_id: "energy_volume".into(),
            mlip_id: "mace-mp-0".into(),
        }
    }

    #[test]
    fn cloud_span_matches_python_local_parity_contract() {
        let span = CloudCellSpan::admitted(
            &identity(),
            "mlip-cell-mace",
            &Admission {
                schedule: "nightly-baseline".into(),
                reservation_gpu_hours: 0.5,
                reserved_gpu_hours: 1.0,
                daily_gpu_hour_cap: 2.0,
                duplicate: false,
            },
        );
        let attrs = span.attributes();
        assert_eq!(attrs["mlip.schema"], "lupine.mlip.cloud_cell_span.v1");
        assert_eq!(attrs["mlip.origin"], "cloud");
        assert_eq!(attrs["mlip.correlation_id"], "workflow-nightly-1");
        assert_eq!(attrs["mlip.cloud_run_id"], "nightly-run-1");
        assert_eq!(
            attrs["mlip.cell_id"],
            "nightly-run-1:baseline:energy_volume:mace-mp-0"
        );
        assert_eq!(attrs["mlip.triplet.row_id"], "energy_volume");
        assert_eq!(attrs["mlip.triplet.mlip_id"], "mace-mp-0");
        assert_eq!(attrs["mlip.cost.reserved_gpu_hours"], 1.0);
        assert_eq!(attrs["mlip.cost.daily_gpu_hour_cap"], 2.0);
    }

    #[test]
    fn otlp_json_contains_exactly_one_cloud_cell_span_with_stable_ids() {
        let span = CloudCellSpan::admitted(
            &identity(),
            "mlip-cell-mace",
            &Admission {
                schedule: "nightly-baseline".into(),
                reservation_gpu_hours: 0.5,
                reserved_gpu_hours: 1.0,
                daily_gpu_hour_cap: 2.0,
                duplicate: false,
            },
        );
        let first = span.otlp_json("glim-think");
        let second = span.otlp_json("glim-think");
        let spans = first["resourceSpans"][0]["scopeSpans"][0]["spans"]
            .as_array()
            .unwrap();
        assert_eq!(spans.len(), 1);
        assert_eq!(spans[0]["name"], "mlip.flywheel.cloud_cell");
        assert_eq!(spans[0]["traceId"].as_str().unwrap().len(), 32);
        assert_eq!(spans[0]["spanId"].as_str().unwrap().len(), 16);
        assert_eq!(
            spans[0]["traceId"],
            second["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["traceId"]
        );
        assert_eq!(
            spans[0]["spanId"],
            second["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["spanId"]
        );
    }
}
