use std::collections::{BTreeMap, BTreeSet};

use anyhow::{anyhow, bail, Context};
use serde::Deserialize;

const CATALOG_SCHEMA: &str = "lupine.mlip.backend_catalog.v1";
const METADATA_TOKEN_URL: &str =
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token";

#[derive(Debug, Deserialize)]
struct BackendCatalog {
    schema: String,
    backends: Vec<BackendEntry>,
}

#[derive(Debug, Deserialize)]
struct BackendEntry {
    mlip_id: String,
    target_job: String,
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
}

#[derive(Debug)]
pub struct ValidatedCatalog {
    pub jobs: BTreeSet<String>,
    pub backend_by_job: BTreeMap<String, String>,
}

pub async fn load_catalog(source: &str) -> anyhow::Result<ValidatedCatalog> {
    let bytes = read_object(source).await?;
    let catalog: BackendCatalog = serde_json::from_slice(&bytes)
        .with_context(|| format!("decoding backend catalog from {source}"))?;
    validate_catalog(catalog)
}

pub async fn read_object(source: &str) -> anyhow::Result<Vec<u8>> {
    if let Some(rest) = source.strip_prefix("gs://") {
        let (bucket, object) = rest
            .split_once('/')
            .filter(|(bucket, object)| !bucket.is_empty() && !object.is_empty())
            .ok_or_else(|| anyhow!("invalid backend catalog gs:// URL: {source}"))?;
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .context("building backend catalog HTTP client")?;
        let token: TokenResponse = client
            .get(METADATA_TOKEN_URL)
            .header("Metadata-Flavor", "Google")
            .send()
            .await
            .context("fetching metadata token for backend catalog")?
            .error_for_status()
            .context("metadata token response for backend catalog")?
            .json()
            .await
            .context("decoding metadata token for backend catalog")?;
        let mut url = reqwest::Url::parse("https://storage.googleapis.com/storage/v1/b/")?;
        url.path_segments_mut()
            .map_err(|_| anyhow!("storage API base URL cannot be a base"))?
            .pop_if_empty()
            .push(bucket)
            .push("o")
            .push(object);
        url.query_pairs_mut().append_pair("alt", "media");
        return Ok(client
            .get(url)
            .bearer_auth(token.access_token)
            .send()
            .await
            .with_context(|| format!("fetching backend catalog {source}"))?
            .error_for_status()
            .with_context(|| format!("backend catalog response {source}"))?
            .bytes()
            .await
            .context("reading backend catalog response")?
            .to_vec());
    }

    if source.starts_with("https://") {
        return Ok(reqwest::Client::new()
            .get(source)
            .send()
            .await
            .with_context(|| format!("fetching backend catalog {source}"))?
            .error_for_status()
            .with_context(|| format!("backend catalog response {source}"))?
            .bytes()
            .await
            .context("reading backend catalog response")?
            .to_vec());
    }

    std::fs::read(source).with_context(|| format!("reading backend catalog {source}"))
}

fn validate_catalog(catalog: BackendCatalog) -> anyhow::Result<ValidatedCatalog> {
    if catalog.schema != CATALOG_SCHEMA {
        bail!(
            "backend catalog schema must be {CATALOG_SCHEMA}, got {}",
            catalog.schema
        );
    }
    if catalog.backends.is_empty() {
        bail!("backend catalog contains no backends");
    }

    let mut ids = BTreeSet::new();
    let mut jobs = BTreeSet::new();
    let mut backend_by_job = BTreeMap::new();
    for backend in catalog.backends {
        if !ids.insert(backend.mlip_id.clone()) {
            bail!("duplicate backend catalog mlip_id: {}", backend.mlip_id);
        }
        if !valid_cloud_run_job_name(&backend.target_job) {
            bail!(
                "invalid backend catalog target_job for {}: {}",
                backend.mlip_id,
                backend.target_job
            );
        }
        if !jobs.insert(backend.target_job.clone()) {
            bail!(
                "duplicate backend catalog target_job: {}",
                backend.target_job
            );
        }
        backend_by_job.insert(backend.target_job, backend.mlip_id);
    }
    Ok(ValidatedCatalog {
        jobs,
        backend_by_job,
    })
}

fn valid_cloud_run_job_name(value: &str) -> bool {
    value.starts_with("mlip-cell-")
        && value.len() <= 63
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
        && !value.ends_with('-')
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_duplicate_or_non_mlip_targets() {
        let duplicate = BackendCatalog {
            schema: CATALOG_SCHEMA.into(),
            backends: vec![
                BackendEntry {
                    mlip_id: "a".into(),
                    target_job: "mlip-cell-a".into(),
                },
                BackendEntry {
                    mlip_id: "b".into(),
                    target_job: "mlip-cell-a".into(),
                },
            ],
        };
        assert!(validate_catalog(duplicate).is_err());

        let unsafe_target = BackendCatalog {
            schema: CATALOG_SCHEMA.into(),
            backends: vec![BackendEntry {
                mlip_id: "a".into(),
                target_job: "other-job".into(),
            }],
        };
        assert!(validate_catalog(unsafe_target).is_err());
    }
}
