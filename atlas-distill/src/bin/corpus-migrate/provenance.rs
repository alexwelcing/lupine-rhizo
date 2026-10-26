//! Audit only declared local-file links; never infer scientific provenance closure.
use super::{checked_json, sha, valid_hash, Entry, Reader, FILE_CAP, INPUT_CAP};
use anyhow::{ensure, Result};
use serde_json::{json, Value};
use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    path::PathBuf,
};

const EDGE_CAP: usize = 20000;
const OBJECT_CAP: usize = 512;
const NODE_CAP: usize = 1000000;
const PAIRS: [(&str, &str, &str); 7] = [
    ("path", "sha256", "bytes"),
    ("local_source", "source_sha256", "source_bytes"),
    ("local_path", "sha256", "source_bytes"),
    ("file", "sha256", "bytes"),
    ("pdf_path", "pdf_sha256", "pdf_bytes"),
    ("text_path", "text_sha256", "text_bytes"),
    ("tool_text", "tool_text_sha256", "tool_text_bytes"),
];

fn pointer(parent: &str, key: &str) -> String {
    format!("{parent}/{}", key.replace('~', "~0").replace('/', "~1"))
}
#[derive(Clone)]
struct Link {
    container: String,
    pointer: String,
    path: Value,
    hash: Value,
    size: Option<Value>,
}
struct Graph {
    links: VecDeque<Link>,
    edges: Vec<Value>,
    statuses: BTreeMap<String, usize>,
    visited: BTreeMap<(PathBuf, String), (String, Option<usize>)>,
    parsed: BTreeSet<String>,
    nodes: usize,
    declared: usize,
    bytes: u64,
    truncated: bool,
}
impl Graph {
    fn link(&mut self, link: Link) {
        if self.declared == EDGE_CAP {
            self.truncated = true;
            return;
        }
        self.declared += 1;
        self.links.push_back(link);
    }
    fn result(&mut self, link: &Link, status: &str, size: Option<usize>) {
        *self.statuses.entry(status.to_owned()).or_default() += 1;
        self.edges.push(json!({
            "declaringObjectSha256":link.container,"pointer":link.pointer,
            "declaredPath":link.path,"declaredSha256":link.hash,
            "declaredBytes":link.size,"status":status,"verifiedBytes":size
        }));
    }
    fn scan(&mut self, v: &Value, container: &str, at: &str) {
        if self.nodes == NODE_CAP {
            self.truncated = true;
            return;
        }
        self.nodes += 1;
        match v {
            Value::Object(map) => {
                for (path, hash, size) in PAIRS {
                    if let Some(value) = map.get(path) {
                        self.link(Link {
                            container: container.to_owned(),
                            pointer: pointer(at, path),
                            path: value.clone(),
                            hash: map.get(hash).cloned().unwrap_or(Value::Null),
                            size: map.get(size).cloned(),
                        });
                    }
                }
                // Legacy filename -> digest maps. Relative names still resolve
                // against the explicit root; never search for a matching basename.
                if let Some(Value::Object(files)) = map.get("files") {
                    for (name, value) in files {
                        if value.is_string() {
                            self.link(Link {
                                container: container.to_owned(),
                                pointer: pointer(&pointer(at, "files"), name),
                                path: Value::String(name.clone()),
                                hash: value.clone(),
                                size: None,
                            });
                        }
                    }
                }
                for (key, value) in map {
                    // Keep non-file anchors and unfamiliar path fields visible
                    // without opening, resolving or fetching them.
                    let known = PAIRS.iter().any(|(p, _, _)| *p == key);
                    if !known
                        && (key.ends_with("_path")
                            || key.ends_with("_file")
                            || matches!(key.as_str(), "url" | "doi" | "tool_receipt" | "loader"))
                    {
                        let link = Link {
                            container: container.to_owned(),
                            pointer: pointer(at, key),
                            path: value.clone(),
                            hash: Value::Null,
                            size: None,
                        };
                        if self.declared < EDGE_CAP {
                            self.declared += 1;
                            self.result(
                                &link,
                                if matches!(key.as_str(), "url" | "doi" | "tool_receipt") {
                                    "non_file_anchor_not_resolved"
                                } else {
                                    "unsupported_reference_field"
                                },
                                None,
                            );
                        } else {
                            self.truncated = true;
                        }
                    }
                    self.scan(value, container, &pointer(at, key));
                    if self.nodes == NODE_CAP {
                        self.truncated = true;
                        break;
                    }
                }
            }
            Value::Array(items) => {
                for (i, value) in items.iter().enumerate() {
                    self.scan(value, container, &pointer(at, &i.to_string()));
                    if self.nodes == NODE_CAP {
                        self.truncated = true;
                        break;
                    }
                }
            }
            _ => {}
        }
    }
    fn follow<R: Reader>(&mut self, r: &mut R, link: Link) -> Result<()> {
        let Some(path) = link.path.as_str().filter(|p| !p.is_empty()) else {
            self.result(&link, "missing_or_invalid_path", None);
            return Ok(());
        };
        if path.contains("://") || path.starts_with("doi:") {
            self.result(&link, "non_file_anchor_not_resolved", None);
            return Ok(());
        }
        let Some(hash) = link.hash.as_str().filter(|h| valid_hash(h)) else {
            self.result(&link, "missing_or_invalid_hash", None);
            return Ok(());
        };
        let expected_size = match link.size.as_ref() {
            None | Some(Value::Null) => None,
            Some(v) => match v.as_u64() {
                Some(n) if n <= FILE_CAP => Some(n),
                _ => {
                    self.result(&link, "invalid_or_oversize_declaration", None);
                    return Ok(());
                }
            },
        };
        let key = (PathBuf::from(path), hash.to_owned());
        if let Some((status, size)) = self.visited.get(&key).cloned() {
            let status =
                if size.is_some() && expected_size.is_some_and(|n| Some(n as usize) != size) {
                    "byte_count_mismatch"
                } else {
                    &status
                };
            self.result(&link, status, size);
            return Ok(());
        }
        if self.visited.len() == OBJECT_CAP || self.bytes >= INPUT_CAP {
            self.result(&link, "audit_budget_exhausted", None);
            self.truncated = true;
            return Ok(());
        }
        let entry = Entry {
            path: key.0.clone(),
            sha256: key.1.clone(),
            bytes: None,
        };
        // Reader enforces filesystem policy before reading. Recheck returned
        // bytes independently so a test/custom Reader cannot confer verification.
        let bytes = match r.read(&entry) {
            Ok(bytes) => bytes,
            Err(error) => {
                let status = match error.to_string().as_str() {
                    "component hash mismatch" => "hash_mismatch",
                    "preflight exceeds remaining read budget"
                    | "preflight exceeds 100 MiB read budget" => {
                        self.truncated = true;
                        "read_budget_exhausted"
                    }
                    _ => "read_failed",
                };
                self.visited.insert(key, (status.to_owned(), None));
                self.result(&link, status, None);
                return Ok(());
            }
        };
        self.bytes = self.bytes.saturating_add(bytes.len() as u64);
        if bytes.len() as u64 > FILE_CAP || self.bytes > INPUT_CAP {
            self.visited
                .insert(key, ("audit_budget_exhausted".to_owned(), None));
            self.result(&link, "audit_budget_exhausted", None);
            self.truncated = true;
            return Ok(());
        }
        if sha(&bytes) != hash {
            self.visited.insert(key, ("hash_mismatch".to_owned(), None));
            self.result(&link, "hash_mismatch", None);
            return Ok(());
        }
        let size = Some(bytes.len());
        self.visited.insert(key, ("verified_file".to_owned(), size));
        let status = if expected_size.is_some_and(|n| n != bytes.len() as u64) {
            "byte_count_mismatch"
        } else {
            "verified_file"
        };
        self.result(&link, status, size);
        // Content identity, not filename, prevents repeated JSON expansion.
        // A verified opaque object remains opaque; only .json is interpreted.
        if PathBuf::from(path)
            .extension()
            .and_then(|s| s.to_str())
            .is_some_and(|s| s.eq_ignore_ascii_case("json"))
            && self.parsed.insert(hash.to_owned())
        {
            if checked_json(&bytes).is_err() {
                self.result(&link, "json_traversal_rejected", size);
            } else {
                let value: Value = serde_json::from_slice(&bytes)?;
                self.scan(&value, hash, "");
            }
        }
        Ok(())
    }
}
pub(super) fn audit<R: Reader>(
    bytes: &[u8],
    manifest_hash: &str,
    reader: &mut R,
    details: bool,
) -> Result<Value> {
    ensure!(
        bytes.len() as u64 <= FILE_CAP && valid_hash(manifest_hash) && sha(bytes) == manifest_hash,
        "manifest digest mismatch"
    );
    checked_json(bytes)?;
    let value: Value = serde_json::from_slice(bytes)?;
    ensure!(
        value["schema"] == "lupine.corpus.base_plus_deltas.v2",
        "only v2 manifests supported"
    );
    let mut graph = Graph {
        links: VecDeque::new(),
        edges: Vec::new(),
        statuses: BTreeMap::new(),
        visited: BTreeMap::new(),
        parsed: BTreeSet::from([manifest_hash.to_owned()]),
        nodes: 0,
        declared: 0,
        bytes: bytes.len() as u64,
        truncated: false,
    };
    graph.scan(&value, manifest_hash, "");
    while let Some(link) = graph.links.pop_front() {
        graph.follow(reader, link)?;
    }
    let mut report = json!({
        "state":"declared_reference_audit_not_migrated",
        "scope":"supported local file reference fields; not semantic provenance closure",
        "manifestSha256":manifest_hash,"declaredReferences":graph.declared,
        "outcomes":graph.statuses,"uniqueFileAttempts":graph.visited.len(),
        "returnedBytesIncludingManifest":graph.bytes,"jsonObjectsTraversalAttempted":graph.parsed.len(),
        "jsonNodesVisited":graph.nodes,"truncated":graph.truncated,
        "limits":{"files":OBJECT_CAP,"references":EDGE_CAP,"jsonNodes":NODE_CAP,
            "fileBytes":FILE_CAP,"inputBytes":INPUT_CAP},
        "provenanceClosure":"not_verified","scientificValidation":"not_assessed",
        "uploads":0,"networkRequests":0,
        "note":"Hashes verify retained bytes, not attribution or scientific accuracy. Non-file anchors and unknown fields are not resolved; absence of detected gaps is not proof of closure."
    });
    if details {
        report["privateReferenceDetails"] = Value::Array(graph.edges);
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Memory {
        files: BTreeMap<PathBuf, Vec<u8>>,
        reads: usize,
    }
    impl Memory {
        fn new() -> Self {
            Self {
                files: BTreeMap::new(),
                reads: 0,
            }
        }
        fn put(&mut self, path: &str, bytes: &[u8]) -> Value {
            self.files.insert(PathBuf::from(path), bytes.to_vec());
            json!({"path":path,"sha256":sha(bytes),"bytes":bytes.len()})
        }
    }
    impl Reader for Memory {
        fn read(&mut self, e: &Entry) -> Result<Vec<u8>> {
            self.reads += 1;
            self.files
                .get(&e.path)
                .cloned()
                .ok_or_else(|| anyhow::anyhow!("missing fixture"))
        }
    }
    fn run(r: &mut Memory, fields: Value) -> Value {
        let mut v = fields;
        v["schema"] = json!("lupine.corpus.base_plus_deltas.v2");
        let bytes = v.to_string().into_bytes();
        audit(&bytes, &sha(&bytes), r, true).unwrap()
    }
    #[test]
    fn all_aliases_and_filename_maps_are_followed() {
        let mut r = Memory::new();
        let descriptor = r.put("paper.pdf", b"opaque");
        let hash = descriptor["sha256"].clone();
        let mut fields = json!({"files":{"paper.pdf":hash}});
        for (p, h, n) in PAIRS {
            fields[p] = json!("paper.pdf");
            fields[h] = hash.clone();
            fields[n] = json!(6);
        }
        let out = run(&mut r, fields);
        assert_eq!(out["outcomes"]["verified_file"], 8);
        assert_eq!(r.reads, 1);
        assert_eq!(out["jsonObjectsTraversalAttempted"], 1);
    }
    #[test]
    fn nested_history_and_shared_objects_expand_once() {
        let mut r = Memory::new();
        let leaf = r.put("leaf.pdf", b"leaf");
        let packet = r.put(
            "nested.json",
            &json!({"sources":[leaf]}).to_string().into_bytes(),
        );
        let out = run(&mut r, json!({"base":packet,"previous_manifest":packet}));
        assert_eq!(r.reads, 2);
        assert_eq!(out["outcomes"]["verified_file"], 3);
        assert_eq!(out["jsonObjectsTraversalAttempted"], 2);
        assert_eq!(out["provenanceClosure"], "not_verified");
    }
    #[test]
    fn missing_pins_and_external_anchors_are_never_read() {
        let mut r = Memory::new();
        let out = run(
            &mut r,
            json!({"local_source":null,"file":"README.md",
            "url":"https://example.org/paper","doi":"10.1/example",
            "new_source_path":"unknown.pdf"}),
        );
        assert_eq!(r.reads, 0);
        assert_eq!(out["outcomes"]["missing_or_invalid_path"], 1);
        assert_eq!(out["outcomes"]["missing_or_invalid_hash"], 1);
        assert_eq!(out["outcomes"]["unsupported_reference_field"], 1);
        assert_eq!(out["outcomes"]["non_file_anchor_not_resolved"], 2);
    }
    #[test]
    fn corrupt_bytes_and_failed_reads_are_cached_without_retry() {
        let mut r = Memory::new();
        let mut corrupt = r.put("corrupt.json", b"{}");
        corrupt["sha256"] = json!(sha(b"wrong"));
        let absent = json!({"path":"absent.pdf","sha256":sha(b"absent")});
        let out = run(&mut r, json!({"sources":[corrupt,corrupt,absent,absent]}));
        assert_eq!(r.reads, 2);
        assert_eq!(out["outcomes"]["hash_mismatch"], 2);
        assert_eq!(out["outcomes"]["read_failed"], 2);
        assert_eq!(out["jsonObjectsTraversalAttempted"], 1);
    }
    #[test]
    fn per_edge_sizes_remain_distinct_for_shared_bytes() {
        let mut r = Memory::new();
        let good = r.put("a.pdf", b"abc");
        let mut bad = good.clone();
        bad["bytes"] = json!(4);
        let out = run(&mut r, json!({"sources":[bad,good]}));
        assert_eq!(r.reads, 1);
        assert_eq!(out["outcomes"]["byte_count_mismatch"], 1);
        assert_eq!(out["outcomes"]["verified_file"], 1);
    }
    #[test]
    fn duplicate_json_is_hash_verified_but_not_expanded() {
        let mut r = Memory::new();
        let bad = r.put("bad.json", br#"{"a":1,"a":2}"#);
        let out = run(&mut r, json!({"base":bad}));
        assert_eq!(out["outcomes"]["verified_file"], 1);
        assert_eq!(out["outcomes"]["json_traversal_rejected"], 1);
    }
    #[test]
    fn object_budget_stops_reads_and_keeps_unresolved_edges() {
        let mut r = Memory::new();
        let files: Vec<_> = (0..OBJECT_CAP + 1)
            .map(|i| r.put(&format!("{i}.pdf"), b"x"))
            .collect();
        let out = run(&mut r, json!({"sources":files}));
        assert_eq!(r.reads, OBJECT_CAP);
        assert_eq!(out["truncated"], true);
        assert_eq!(out["outcomes"]["audit_budget_exhausted"], 1);
    }
    #[test]
    fn pointers_are_escaped_and_default_report_has_no_paths() {
        let mut r = Memory::new();
        let entry = r.put("private.pdf", b"x");
        let m = json!({"schema":"lupine.corpus.base_plus_deltas.v2","a~/b":entry});
        let bytes = m.to_string().into_bytes();
        let private = audit(&bytes, &sha(&bytes), &mut r, true).unwrap();
        assert_eq!(
            private["privateReferenceDetails"][0]["pointer"],
            "/a~0~1b/path"
        );
        let public = audit(&bytes, &sha(&bytes), &mut r, false).unwrap();
        assert!(public.get("privateReferenceDetails").is_none());
        assert!(!public.to_string().contains("private.pdf"));
    }
    #[test]
    fn ambiguous_basenames_are_not_searched_for() {
        let mut r = Memory::new();
        let item = r.put("elsewhere/paper.pdf", b"x");
        let out = run(&mut r, json!({"files":{"paper.pdf":item["sha256"]}}));
        assert_eq!(r.reads, 1);
        assert_eq!(out["outcomes"]["read_failed"], 1);
        assert!(out["outcomes"].get("verified_file").is_none());
    }
    #[test]
    fn reader_budget_exhaustion_is_explicit_and_not_retried() {
        struct Budget(usize);
        impl Reader for Budget {
            fn read(&mut self, _: &Entry) -> Result<Vec<u8>> {
                self.0 += 1;
                anyhow::bail!("preflight exceeds remaining read budget")
            }
        }
        let item = json!({"path":"large.pdf","sha256":sha(b"x")});
        let m = json!({"schema":"lupine.corpus.base_plus_deltas.v2","sources":[item,item]});
        let bytes = m.to_string().into_bytes();
        let mut r = Budget(0);
        let out = audit(&bytes, &sha(&bytes), &mut r, false).unwrap();
        assert_eq!(r.0, 1);
        assert_eq!(out["outcomes"]["read_budget_exhausted"], 2);
        assert_eq!(out["truncated"], true);
        assert_eq!(out["uploads"], 0);
    }
}
