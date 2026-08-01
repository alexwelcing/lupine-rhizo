use std::collections::BTreeMap;

use prost::Message;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::budget::Admission;
use crate::CloudCellTelemetry;

#[axum::async_trait]
pub trait TraceEmitter: Send + Sync {
    fn is_enabled(&self) -> bool {
        true
    }

    async fn emit(&self, span: &CloudCellSpan) -> anyhow::Result<()>;
}

pub struct NoopTraceEmitter;

#[axum::async_trait]
impl TraceEmitter for NoopTraceEmitter {
    fn is_enabled(&self) -> bool {
        false
    }

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
        let (content_type, body) = otlp_request(span, &self.project);
        self.client
            .post(&self.endpoint)
            .header("x-relay-token", &self.token)
            .header("content-type", content_type)
            .header("accept", content_type)
            .body(body)
            .send()
            .await?
            .error_for_status()?;
        Ok(())
    }
}

// Phoenix Cloud's OTLP/HTTP ingest currently rejects JSON with HTTP 415 even
// though the relay accepts both standard OTLP media types. Encode at the
// producer so the relay can preserve the request media type end to end.
const OTLP_PROTOBUF_CONTENT_TYPE: &str = "application/x-protobuf";

fn otlp_request(span: &CloudCellSpan, project: &str) -> (&'static str, Vec<u8>) {
    (
        OTLP_PROTOBUF_CONTENT_TYPE,
        span.otlp_protobuf(project).encode_to_vec(),
    )
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
    pub fn dispatched(
        identity: &CloudCellTelemetry,
        target_job: &str,
        admission: Option<&Admission>,
        dispatch_status: &str,
    ) -> Self {
        Self {
            identity: identity.clone(),
            target_job: target_job.to_string(),
            schedule_name: admission
                .map(|value| value.schedule.clone())
                .unwrap_or_else(|| "unscheduled-campaign".into()),
            dispatch_status: dispatch_status.into(),
            reservation_gpu_hours: admission.map_or(0.0, |value| value.reservation_gpu_hours),
            reserved_gpu_hours: admission.map_or(0.0, |value| value.reserved_gpu_hours),
            daily_gpu_hour_cap: admission.map_or(0.0, |value| value.daily_gpu_hour_cap),
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

    fn otlp_protobuf(&self, project: &str) -> ExportTraceServiceRequest {
        let seed = format!(
            "{}\0{}\0{}",
            self.identity.correlation_id, self.identity.run_id, self.identity.cell_id
        );
        let digest = Sha256::digest(seed.as_bytes());
        let now = time::OffsetDateTime::now_utc().unix_timestamp_nanos() as u64;
        let attributes = self
            .attributes()
            .into_iter()
            .map(|(key, value)| KeyValue {
                key,
                value: Some(any_value(value)),
            })
            .collect();

        ExportTraceServiceRequest {
            resource_spans: vec![ResourceSpans {
                resource: Some(Resource {
                    attributes: vec![
                        string_key_value("service.name", "tasks-consumer"),
                        string_key_value("openinference.project.name", project),
                    ],
                    dropped_attributes_count: 0,
                }),
                scope_spans: vec![ScopeSpans {
                    scope: Some(InstrumentationScope {
                        name: "mlip.flywheel".into(),
                        version: String::new(),
                    }),
                    spans: vec![ProtoSpan {
                        trace_id: digest[..16].to_vec(),
                        span_id: digest[16..24].to_vec(),
                        name: "mlip.flywheel.cloud_cell".into(),
                        kind: 1,
                        start_time_unix_nano: now,
                        end_time_unix_nano: now,
                        attributes,
                        status: Some(Status {
                            message: String::new(),
                            code: 1,
                        }),
                    }],
                }],
            }],
        }
    }
}

#[derive(Clone, PartialEq, Message)]
struct ExportTraceServiceRequest {
    #[prost(message, repeated, tag = "1")]
    resource_spans: Vec<ResourceSpans>,
}

#[derive(Clone, PartialEq, Message)]
struct ResourceSpans {
    #[prost(message, optional, tag = "1")]
    resource: Option<Resource>,
    #[prost(message, repeated, tag = "2")]
    scope_spans: Vec<ScopeSpans>,
}

#[derive(Clone, PartialEq, Message)]
struct Resource {
    #[prost(message, repeated, tag = "1")]
    attributes: Vec<KeyValue>,
    #[prost(uint32, tag = "2")]
    dropped_attributes_count: u32,
}

#[derive(Clone, PartialEq, Message)]
struct ScopeSpans {
    #[prost(message, optional, tag = "1")]
    scope: Option<InstrumentationScope>,
    #[prost(message, repeated, tag = "2")]
    spans: Vec<ProtoSpan>,
}

#[derive(Clone, PartialEq, Message)]
struct InstrumentationScope {
    #[prost(string, tag = "1")]
    name: String,
    #[prost(string, tag = "2")]
    version: String,
}

#[derive(Clone, PartialEq, Message)]
struct ProtoSpan {
    #[prost(bytes = "vec", tag = "1")]
    trace_id: Vec<u8>,
    #[prost(bytes = "vec", tag = "2")]
    span_id: Vec<u8>,
    #[prost(string, tag = "5")]
    name: String,
    #[prost(int32, tag = "6")]
    kind: i32,
    #[prost(fixed64, tag = "7")]
    start_time_unix_nano: u64,
    #[prost(fixed64, tag = "8")]
    end_time_unix_nano: u64,
    #[prost(message, repeated, tag = "9")]
    attributes: Vec<KeyValue>,
    #[prost(message, optional, tag = "15")]
    status: Option<Status>,
}

#[derive(Clone, PartialEq, Message)]
struct Status {
    #[prost(string, tag = "2")]
    message: String,
    #[prost(int32, tag = "3")]
    code: i32,
}

#[derive(Clone, PartialEq, Message)]
struct KeyValue {
    #[prost(string, tag = "1")]
    key: String,
    #[prost(message, optional, tag = "2")]
    value: Option<AnyValue>,
}

#[derive(Clone, PartialEq, Message)]
struct AnyValue {
    #[prost(oneof = "any_value::Value", tags = "1, 2, 3, 4")]
    value: Option<any_value::Value>,
}

mod any_value {
    #[derive(Clone, PartialEq, prost::Oneof)]
    pub enum Value {
        #[prost(string, tag = "1")]
        String(String),
        #[prost(bool, tag = "2")]
        Bool(bool),
        #[prost(int64, tag = "3")]
        Int(i64),
        #[prost(double, tag = "4")]
        Double(f64),
    }
}

fn string_key_value(key: &str, value: &str) -> KeyValue {
    KeyValue {
        key: key.into(),
        value: Some(AnyValue {
            value: Some(any_value::Value::String(value.into())),
        }),
    }
}

fn any_value(value: Value) -> AnyValue {
    let value = match value {
        Value::Bool(value) => any_value::Value::Bool(value),
        Value::Number(value) => value
            .as_i64()
            .map(any_value::Value::Int)
            .unwrap_or_else(|| any_value::Value::Double(value.as_f64().unwrap_or_default())),
        Value::String(value) => any_value::Value::String(value),
        other => any_value::Value::String(other.to_string()),
    };
    AnyValue { value: Some(value) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn noop_trace_emitter_reports_disabled() {
        assert!(!TraceEmitter::is_enabled(&NoopTraceEmitter));
    }
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
        let span = CloudCellSpan::dispatched(
            &identity(),
            "mlip-cell-mace",
            Some(&Admission {
                schedule: "nightly-baseline".into(),
                reservation_gpu_hours: 0.5,
                reserved_gpu_hours: 1.0,
                daily_gpu_hour_cap: 2.0,
                duplicate: false,
            }),
            "admitted",
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
    fn cloud_trace_transport_uses_phoenix_supported_protobuf() {
        let span = CloudCellSpan::dispatched(
            &identity(),
            "mlip-cell-mace",
            Some(&Admission {
                schedule: "nightly-baseline".into(),
                reservation_gpu_hours: 0.5,
                reserved_gpu_hours: 1.0,
                daily_gpu_hour_cap: 2.0,
                duplicate: false,
            }),
            "admitted",
        );

        let (content_type, body) = otlp_request(&span, "glim-think");
        assert_eq!(content_type, "application/x-protobuf");
        assert!(!body.is_empty());
        assert_ne!(body[0], b'{', "Phoenix Cloud rejects OTLP/HTTP JSON");

        let decoded = ExportTraceServiceRequest::decode(body.as_slice()).unwrap();
        let spans = &decoded.resource_spans[0].scope_spans[0].spans;
        assert_eq!(spans.len(), 1);
        assert_eq!(spans[0].name, "mlip.flywheel.cloud_cell");
        assert_eq!(spans[0].trace_id.len(), 16);
        assert_eq!(spans[0].span_id.len(), 8);

        let (_, second_body) = otlp_request(&span, "glim-think");
        let second = ExportTraceServiceRequest::decode(second_body.as_slice()).unwrap();
        let second_span = &second.resource_spans[0].scope_spans[0].spans[0];
        assert_eq!(spans[0].trace_id, second_span.trace_id);
        assert_eq!(spans[0].span_id, second_span.span_id);
    }
}
