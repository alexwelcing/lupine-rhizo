//! Read-only, bounded planning for the private corpus API. No network or writes.
//! stdout may contain private evidence; never publish it or redirect without storage admission.
use anyhow::{ensure, Context, Result};
use clap::Parser;
use serde::{de::{MapAccess, Visitor}, Deserialize, Deserializer};
use serde_json::{json, value::RawValue, Value};
use sha2::{Digest, Sha256};
use std::{collections::{BTreeMap, BTreeSet}, fmt, fs, io::{self, Read, Write}, path::{Component, Path, PathBuf}};

const FILE_CAP: u64 = 25 * 1024 * 1024;
const INPUT_CAP: u64 = 100 * 1024 * 1024;
const ROW_CAP: usize = 65536;
const BODY_CAP: usize = 1024 * 1024;
const ROW_COUNT_CAP: usize = 10000;
type RawMap = BTreeMap<String, Box<RawValue>>;

// serde_json's ordinary map deserializer silently replaces duplicate keys.
// Reject them before interpreting a manifest, record or qualification.
struct UniqueMap(RawMap);
impl<'de> Deserialize<'de> for UniqueMap {
    fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = UniqueMap;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result { f.write_str("unique object keys") }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> std::result::Result<UniqueMap, A::Error> {
                let mut m = BTreeMap::new();
                while let Some((k, v)) = a.next_entry::<String, Box<RawValue>>()? {
                    if m.insert(k, v).is_some() { return Err(serde::de::Error::custom("duplicate JSON key")); }
                }
                Ok(UniqueMap(m))
            }
        }
        d.deserialize_map(V)
    }
}
fn object(raw: &str) -> Result<RawMap> { Ok(serde_json::from_str::<UniqueMap>(raw)?.0) }
fn sha(bytes: &[u8]) -> String { format!("{:x}", Sha256::digest(bytes)) }
fn valid_hash(s: &str) -> bool { s.len() == 64 && s.bytes().all(|x| x.is_ascii_digit() || (b'a'..=b'f').contains(&x)) }
fn text(v: &Value, cap: usize) -> Option<&str> {
    v.as_str().filter(|s| !s.trim().is_empty() && s.len() <= cap && !s.chars().any(|c| c < ' '))
}
fn required<'a>(v: &'a Value, key: &str, cap: usize) -> Result<&'a str> {
    text(&v[key], cap).with_context(|| format!("invalid or missing {key}"))
}
// This is NOT a universal Python float serializer or a canonical-JSON standard.
// Preserve numeric lexemes, sort keys and compact whitespace. Use a legacy
// fingerprint only when it EXACTLY matches the retained qualification digest.
fn lexical_compact(raw: &str, depth: usize) -> Result<String> { compact(raw,depth,false) }
fn compact(raw: &str, depth: usize, padded_exponents: bool) -> Result<String> {
    ensure!(depth < 64, "JSON nesting limit");
    let r: Box<RawValue> = serde_json::from_str(raw)?;
    let s = r.get();
    match s.as_bytes()[0] {
        b'{' => {
            let mut parts = Vec::new();
            for (k, v) in object(s)? {
                parts.push(format!("{}:{}", serde_json::to_string(&k)?, compact(v.get(), depth+1,padded_exponents)?));
            }
            Ok(format!("{{{}}}", parts.join(",")))
        },
        b'[' => {
            let a: Vec<Box<RawValue>> = serde_json::from_str(s)?;
            let items: Result<Vec<_>> = a.iter().map(|v| compact(v.get(), depth+1,padded_exponents)).collect();
            Ok(format!("[{}]", items?.join(",")))
        },
        b'"' => Ok(serde_json::to_string(&serde_json::from_str::<String>(s)?)?),
        _ => {
            if padded_exponents && (s.starts_with('-') || s.as_bytes()[0].is_ascii_digit()) {
                // An exactly value-preserving spelling candidate, NOT float parsing.
                // It is accepted only if the retained legacy hash matches.
                if let Some((mantissa, exponent))=s.split_once(['e','E']) {
                    let (sign,digits)=if let Some(x)=exponent.strip_prefix('-') {("-",x)}
                        else {("+",exponent.strip_prefix('+').unwrap_or(exponent))};
                    let digits=digits.trim_start_matches('0');
                    let digits=if digits.is_empty() {"0"} else {digits};
                    return Ok(format!("{mantissa}e{sign}{digits:0>2}"));
                }
            }
            Ok(s.to_owned())
        },
    }
}
fn checked_json(bytes: &[u8]) -> Result<()> {
    lexical_compact(std::str::from_utf8(bytes)?, 0)?;
    Ok(())
}

fn timestamp(v: &str) -> Result<()> {
    let re=regex::Regex::new(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(Z|[+-]\d{2}:\d{2})$")?;
    let m=re.captures(v).context("original timestamp needs an explicit ISO timezone")?;
    let n:Vec<u32>=(1..=6).map(|i|m[i].parse::<u32>().unwrap()).collect();
    let leap=n[0]%4==0 && (n[0]%100!=0 || n[0]%400==0);
    let days=[31,if leap{29}else{28},31,30,31,30,31,31,30,31,30,31];
    ensure!((1..=12).contains(&n[1]) && n[2]>=1 && n[2]<=days[(n[1]-1) as usize]
        && n[3]<=23 && n[4]<=59 && n[5]<=59,"invalid timestamp calendar");
    let zone=&m[7];
    ensure!(zone=="Z" || (zone[1..3].parse::<u32>()?<=23 && zone[4..6].parse::<u32>()?<=59),"invalid timezone");
    Ok(())
}

#[derive(Clone, Deserialize)]
struct Entry { path: PathBuf, sha256: String, bytes: Option<u64> }
#[derive(Clone, Deserialize)]
struct Manifest {
    schema: String, base: Entry, comparison_deltas: Vec<Entry>, observation_deltas: Vec<Entry>,
    #[serde(default)] qualification_deltas: Vec<Entry>,
}
trait Reader { fn read(&mut self, entry: &Entry) -> Result<Vec<u8>>; }
struct LocalReader { root: PathBuf, consumed: u64 }
impl Reader for LocalReader {
    fn read(&mut self, e: &Entry) -> Result<Vec<u8>> {
        ensure!(valid_hash(&e.sha256), "invalid component hash");
        let p = if e.path.is_absolute() { e.path.clone() } else { self.root.join(&e.path) };
        let relative = p.strip_prefix(&self.root).context("component outside declared root")?;
        let mut walk = self.root.clone();
        for c in relative.components() {
            ensure!(matches!(c, Component::Normal(_)), "non-normal component path");
            walk.push(c.as_os_str());
            ensure!(!fs::symlink_metadata(&walk)?.file_type().is_symlink(), "symlink component denied");
        }
        let f = fs::File::open(&p)?;
        ensure!(f.metadata()?.is_file(), "component is not a regular file");
        let mut bytes = Vec::new();
        f.take(FILE_CAP+1).read_to_end(&mut bytes)?;
        ensure!(bytes.len() as u64 <= FILE_CAP, "component exceeds 25 MiB");
        self.consumed = self.consumed.checked_add(bytes.len() as u64).context("input overflow")?;
        ensure!(self.consumed <= INPUT_CAP, "preflight exceeds 100 MiB read budget");
        ensure!(e.bytes.map_or(true, |n| n == bytes.len() as u64), "component byte count mismatch");
        ensure!(sha(&bytes) == e.sha256, "component hash mismatch");
        Ok(bytes)
    }
}
#[derive(Clone)]
struct Row {
    id: String, exact: String, digest: String, lexical_hash: String,
    evidence: String, pointer: String, paired: bool,
}
#[derive(Clone)]
struct Event { value: Value, evidence: String, pointer: String, legacy: String, legacy_method: String }
struct Prepared { rows: Vec<Row>, events: BTreeMap<String, Event>, objects: BTreeSet<String>, manifest: String }
fn collect_records(raw: &str, evidence: &str, prefix: &str, paired: bool, rows: &mut Vec<Row>) -> Result<()> {
    let packet = object(raw)?;
    let records = packet.get("records").context("missing records array")?;
    let values: Vec<Box<RawValue>> = serde_json::from_str(records.get())?;
    for (i, record) in values.iter().enumerate() {
        ensure!(rows.len() < ROW_COUNT_CAP, "record count exceeds 10000");
        ensure!(record.get().len() <= ROW_CAP, "record exceeds 64 KiB");
        let v: Value = serde_json::from_str(record.get())?;
        ensure!(v.is_object() && v.get("corpus_qualification").is_none(), "expected original unannotated row");
        let id = required(&v, "id", 256)?.to_owned();
        let exact = record.get().to_owned();
        rows.push(Row { id, digest:sha(exact.as_bytes()), lexical_hash:sha(lexical_compact(&exact,0)?.as_bytes()),
            exact, evidence:evidence.to_owned(), pointer:format!("{prefix}/records/{i}"), paired });
    }
    Ok(())
}
fn read_json<R: Reader>(r: &mut R, e: &Entry, objects: &mut BTreeSet<String>) -> Result<String> {
    let bytes = r.read(e)?;
    ensure!(bytes.len() as u64 <= FILE_CAP && valid_hash(&e.sha256) && sha(&bytes)==e.sha256, "unverified reader result");
    ensure!(e.bytes.map_or(true, |n| n==bytes.len() as u64), "reader size mismatch");
    checked_json(&bytes)?;
    objects.insert(e.sha256.clone());
    Ok(String::from_utf8(bytes)?)
}
fn prepare<R: Reader>(manifest_bytes: &[u8], expected: &str, reader: &mut R) -> Result<Prepared> {
    ensure!(manifest_bytes.len() as u64 <= FILE_CAP && valid_hash(expected) && sha(manifest_bytes)==expected, "manifest digest mismatch");
    checked_json(manifest_bytes)?;
    let m: Manifest = serde_json::from_slice(manifest_bytes)?;
    ensure!(m.schema=="lupine.corpus.base_plus_deltas.v2", "only v2 manifests supported");
    ensure!(m.comparison_deltas.len()+m.observation_deltas.len()+m.qualification_deltas.len() < 512, "component count limit");
    let mut objects=BTreeSet::from([expected.to_owned()]);
    let mut rows=Vec::new();
    let base=read_json(reader,&m.base,&mut objects)?;
    let b=object(&base)?;
    if let Some(seed)=b.get("legacy_seed") { collect_records(seed.get(),&m.base.sha256,"/legacy_seed",true,&mut rows)?; }
    for (key,paired) in [("batches",true),("incomplete_observation_batches",false)] {
        if let Some(packets)=b.get(key) {
            let a:Vec<Box<RawValue>>=serde_json::from_str(packets.get())?;
            for (i,p) in a.iter().enumerate() { collect_records(p.get(),&m.base.sha256,&format!("/{key}/{i}"),paired,&mut rows)?; }
        } else { ensure!(key!="batches","base requires batches"); }
    }
    for (entries,paired) in [(&m.comparison_deltas,true),(&m.observation_deltas,false)] {
        for e in entries { collect_records(&read_json(reader,e,&mut objects)?,&e.sha256,"",paired,&mut rows)?; }
    }
    rows.sort_by(|a,b| a.id.cmp(&b.id));
    ensure!(rows.windows(2).all(|r|r[0].id!=r[1].id), "duplicate record identifier");
    let index:BTreeMap<_,_>=rows.iter().map(|r|(r.id.as_str(),r)).collect();
    let mut events=BTreeMap::new();
    let mut event_ids=BTreeSet::new();
    for e in &m.qualification_deltas {
        let raw=read_json(reader,e,&mut objects)?;
        let p:Value=serde_json::from_str(&raw)?;
        ensure!(p["schema"]=="lupine.corpus.qualifications.v1","unknown qualification schema");
        for (i,q) in p["records"].as_array().context("qualification records missing")?.iter().enumerate() {
            let target=required(q,"target_id",256)?;
            let row=index.get(target).context("unknown qualification target")?;
            let legacy=required(q,"target_sha256",64)?;
            ensure!(valid_hash(legacy), "invalid legacy target hash");
            let legacy_method=if legacy==row.lexical_hash { "sorted_compact_lexemes" }
                else if legacy==sha(compact(&row.exact,0,true)?.as_bytes()) { "sorted_compact_padded_exponents" }
                else { anyhow::bail!("legacy target digest mismatch; explicit mapping required, never guess") };
            ensure!(q["state"]=="quarantined","unsupported qualification state");
            let id=required(q,"id",256)?;
            ensure!(event_ids.insert(id.to_owned()),"duplicate qualification ID");
            let reason=required(q,"reason",2048)?;
            let evidence=q["evidence"].as_array().context("qualification evidence missing")?;
            ensure!(!evidence.is_empty(),"empty qualification evidence");
            for item in evidence {
                let a:Entry=serde_json::from_value(item.clone())?;
                ensure!(a.bytes.is_some(),"qualification evidence requires byte count");
                // Existing qualification evidence is structured JSON; pin its original bytes.
                read_json(reader,&a,&mut objects)?;
            }
            if let Some(t)=q.get("reviewed_at").filter(|v| !v.is_null()) { timestamp(text(t,64).context("invalid review time")?)?; }
            let value=json!({"eventId":id,"recordId":target,"recordSha256":row.digest,"kind":"quarantine",
                "reason":reason,"originalReviewedAt":q.get("reviewed_at").cloned().unwrap_or(Value::Null)});
            ensure!(events.insert(target.to_owned(),Event {value,evidence:e.sha256.clone(),
                pointer:format!("/records/{i}"),legacy:legacy.to_owned(),legacy_method:legacy_method.to_owned()}).is_none(),"duplicate qualification target");
        }
    }
    Ok(Prepared { rows,events,objects,manifest:expected.to_owned() })
}
fn projected(row: &Row, event: Option<&Event>) -> Result<Value> {
    // This parse is used ONLY for string-valued projections. Numeric source
    // lexemes in recordJson always come from RawValue above.
    let v:Value=serde_json::from_str(&row.exact)?;
    let source=required(&v,"source_id",256)?;
    let study=v.get("study_key").or_else(||v.get("study_group")).unwrap_or(&v["source_id"]);
    let study=text(study,256).context("invalid study identity")?;
    let mut out=json!({"recordId":row.id,"recordSha256":row.digest,"recordJson":row.exact,
        "evidenceSha256":row.evidence,"locator":format!("json-pointer:{}",row.pointer),
        "sourceId":source,"studyId":study,"originalRowSha256":event.map(|e|e.legacy.as_str()),
        "missingFields":[]});
    let mut missing=vec!["primary_source_closure_not_verified".to_owned()];
    for (key, value, cap) in [
        ("material",&v["material"],256),("observable",v.get("observable").unwrap_or(&v["property"]),256),
        ("unit",&v["unit"],128),("modelId",&v["potential"],256),
        ("referenceKind",v.get("reference_kind").unwrap_or(&v["reference"]["kind"]),128),
        ("observedAt",v.get("observed_at").unwrap_or(&v["extracted_at"]),64),
        ("reviewedAt",&v["reviewed_at"],64),
    ] {
        if value.is_null() { out[key]=Value::Null; missing.push(key.to_owned()); }
        else {
            let s=text(value,cap).with_context(||format!("invalid {key} projection"))?;
            if key=="observedAt" || key=="reviewedAt" { timestamp(s)?; }
            out[key]=json!(s);
        }
    }
    out["missingFields"]=json!(missing);
    Ok(out)
}
#[derive(Clone)]
struct Batch { payload: String, digest: String, id: String, source_objects: Vec<String>, qualification_anchors: Vec<Value> }
fn batch(rows: &[&Row], p: &Prepared) -> Result<Batch> {
    let mut observations=Vec::new();let mut events=Vec::new();let mut objects=BTreeSet::new();let mut anchors=Vec::new();
    for row in rows {
        let event=p.events.get(&row.id);
        observations.push(projected(row,event)?);objects.insert(row.evidence.clone());
        if let Some(e)=event { events.push(e.value.clone());objects.insert(e.evidence.clone());
            anchors.push(json!({"eventId":e.value["eventId"],"evidenceSha256":e.evidence,"locator":format!("json-pointer:{}",e.pointer),"legacyTargetSha256":e.legacy,"legacyDigestMethod":e.legacy_method})); }
    }
    let payload=serde_json::to_string(&json!({"schema":"lupine-private-corpus-v1","observations":observations,"qualifications":events}))?;
    let digest=sha(payload.as_bytes());
    Ok(Batch { id:format!("m{}.{}",p.manifest,digest),payload,digest,source_objects:objects.into_iter().collect(),qualification_anchors:anchors })
}
fn batches(p: &Prepared) -> Result<Vec<Batch>> {
    let mut result=Vec::new();let mut current=Vec::new();
    for row in &p.rows {
        current.push(row);
        let candidate=batch(&current,p)?;
        if current.len()>20 || candidate.payload.len()>BODY_CAP || candidate.source_objects.len()>16 {
            current.pop();
            ensure!(!current.is_empty(),"single row cannot fit import bounds");
            result.push(batch(&current,p)?);
            current=vec![row];
            let candidate=batch(&current,p)?;
            ensure!(candidate.payload.len()<=BODY_CAP && candidate.source_objects.len()<=16,"single row cannot fit");
        }
    }
    if !current.is_empty(){ result.push(batch(&current,p)?); }
    Ok(result)
}
#[derive(Parser)]
#[command(about="Read-only private corpus preflight; never uploads, retries or writes files")]
struct Args {
    /// Explicit trusted root; relative manifest entries resolve here.
    #[arg(long)] root:PathBuf,
    #[arg(long)] manifest:PathBuf,
    /// Pin original manifest bytes, not a reserialized JSON object.
    #[arg(long)] manifest_sha256:String,
    /// Emit ONE private request plan instead of the aggregate report (zero based).
    #[arg(long)] batch_index:Option<usize>,
}
fn run(args:Args)->Result<Value> {
    let root=fs::canonicalize(&args.root)?;
    ensure!(root.is_dir(),"root must be a directory");
    let mut reader=LocalReader{root,consumed:0};
    let bytes=reader.read(&Entry{path:args.manifest,sha256:args.manifest_sha256.clone(),bytes:None})?;
    let p=prepare(&bytes,&args.manifest_sha256,&mut reader)?;
    let plans=batches(&p)?;
    if let Some(i)=args.batch_index {
        let b=plans.get(i).context("batch index out of range")?;
        Ok(json!({"state":"planned_not_uploaded","manifestSha256":p.manifest,"importId":b.id,
            "payloadSha256":b.digest,"payloadBytes":b.payload.len(),"payload":b.payload,
            "sourceObjects":b.source_objects,"qualificationAnchors":b.qualification_anchors,
            "allRequiredArchiveObjects":p.objects,"provenanceClosure":"not_verified",
            "scientificValidation":"not_assessed","requiresPrivateDestination":true,
            "recovery":{"method":"GET","path":format!("/workspace/corpus/imports/{}",b.id)},
            "note":"Read back every required archive object before publication. Import target and quarantine together. Unknown outcomes require read-only recovery; this command performs no HTTP."}))
    } else {
        Ok(json!({"state":"preflight_complete_not_migrated","manifestSha256":p.manifest,
            "originalComparisons":p.rows.iter().filter(|r|r.paired).count(),
            "originalUnpaired":p.rows.iter().filter(|r|!r.paired).count(),
            "qualificationsMapped":p.events.len(),"requiredArchiveObjects":p.objects.len(),
            "plannedImports":plans.len(),"bytesRead":reader.consumed,
            "provenanceClosure":"not_verified","primarySourceDocuments":"not_traversed",
            "scientificValidation":"not_assessed","executionCount":0}))
    }
}
fn main() {
    match run(Args::parse()) {
        Ok(v)=> { if let Err(e)=writeln!(io::stdout().lock(),"{v}") { eprintln!("output failed: {e}");std::process::exit(1); } },
        Err(e)=> { eprintln!("preflight stopped; no import emitted: {e}");std::process::exit(1); }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[derive(Default)]
    struct Memory { files:BTreeMap<PathBuf,Vec<u8>> }
    impl Reader for Memory {
        fn read(&mut self,e:&Entry)->Result<Vec<u8>> {
            self.files.get(&e.path).cloned().context("missing fixture")
        }
    }
    impl Memory {
        fn put(&mut self,path:&str,raw:&str)->Value {
            self.files.insert(PathBuf::from(path),raw.as_bytes().to_vec());
            json!({"path":path,"sha256":sha(raw.as_bytes()),"bytes":raw.len()})
        }
    }
    fn fixture(raw:&str, quarantine:bool)->(Memory,Vec<u8>) {
        let mut r=Memory::default();
        let base=r.put("base.json",&format!(r#"{{"batches":[{{"records":[{raw}]}}]}}"#));
        let mut qs=vec![];
        if quarantine {
            let evidence=r.put("review.json",r#"{"status":"unresolved"}"#);
            let row:Value=serde_json::from_str(raw).unwrap();
            let packet=json!({"schema":"lupine.corpus.qualifications.v1","observed_at":"2026-01-01T12:00:00Z","records":[{
                "id":"q1","target_id":row["id"],"target_sha256":sha(lexical_compact(raw,0).unwrap().as_bytes()),
                "state":"quarantined","reason":"unresolved source assignment","evidence":[evidence]}]});
            qs.push(r.put("q.json",&packet.to_string()));
        }
        let m=json!({"schema":"lupine.corpus.base_plus_deltas.v2","base":base,
            "comparison_deltas":[],"observation_deltas":[],"qualification_deltas":qs});
        (r,m.to_string().into_bytes())
    }
    const ROW:&str=r#"{ "id": "row1", "source_id": "study1", "value": 5.80e-09, "material": "CrN", "unknowns": ["uncertainty"], "extracted_at":"2026-01-02T03:04:05.123456+00:00" }"#;
    fn ready(raw:&str,q:bool)->Prepared {
        let (mut r,m)=fixture(raw,q);
        prepare(&m,&sha(&m),&mut r).unwrap()
    }
    #[test]
    fn exact_lexemes_unicode_whitespace_and_times_survive() {
        let raw=r#"{"id":"row1", "source_id":"s", "label":"α \u03b2","x":-0.0,"y":9007199254740993,"extracted_at":"2026-01-02T03:04:05.123456789-04:00"}"#;
        let p=ready(raw,false);let b=batches(&p).unwrap();
        let payload:Value=serde_json::from_str(&b[0].payload).unwrap();
        let row=&payload["observations"][0];
        assert_eq!(row["recordJson"],raw);
        assert_eq!(row["recordSha256"],sha(raw.as_bytes()));
        assert_eq!(row["observedAt"],"2026-01-02T03:04:05.123456789-04:00");
        assert!(row["reviewedAt"].is_null());
    }
    #[test]
    fn duplicate_keys_rejected_at_every_depth() {
        for raw in [r#"{"a":1,"a":2}"#,r#"{"a":{"b":1,"b":2}}"#,r#"[{"x":1,"x":2}]"#] {
            assert!(lexical_compact(raw,0).is_err());
        }
    }
    #[test]
    fn number_lexemes_do_not_silently_normalize() {
        assert_eq!(lexical_compact(r#"{"b": 1e-06, "a": 1.00}"#,0).unwrap(),r#"{"a":1.00,"b":1e-06}"#);
        assert_ne!(sha(lexical_compact(r#"{"v":1e-06}"#,0).unwrap().as_bytes()),sha(br#"{"v":1e-6}"#));
    }
    #[test]
    fn target_and_quarantine_share_one_import() {
        let p=ready(ROW,true);let b=batches(&p).unwrap();assert_eq!(b.len(),1);
        let v:Value=serde_json::from_str(&b[0].payload).unwrap();
        assert_eq!(v["observations"][0]["recordSha256"],v["qualifications"][0]["recordSha256"]);
        assert_eq!(v["observations"][0]["originalRowSha256"],p.events["row1"].legacy);
        assert!(v["qualifications"][0]["originalReviewedAt"].is_null());
        assert_eq!(b[0].qualification_anchors[0]["locator"],"json-pointer:/records/0");
        assert!(b[0].id.starts_with(&format!("m{}.",p.manifest)));
    }
    #[test]
    fn mismatched_legacy_target_cannot_drop_quarantine() {
        let (mut r,m)=fixture(ROW,true);
        let mut manifest:Value=serde_json::from_slice(&m).unwrap();
        let mut packet:Value=serde_json::from_slice(&r.files[&PathBuf::from("q.json")]).unwrap();
        packet["records"][0]["target_sha256"]=json!("0".repeat(64));
        manifest["qualification_deltas"][0]=r.put("q.json",&packet.to_string());
        let m=manifest.to_string().into_bytes();
        assert!(prepare(&m,&sha(&m),&mut r).unwrap_err_text().contains("legacy target"));
    }
    // Avoid Debug implementations that could accidentally dump private records in errors.
    trait ErrorText { fn unwrap_err_text(self)->String; }
    impl<T> ErrorText for Result<T> {
        fn unwrap_err_text(self)->String { match self { Err(e)=>e.to_string(),Ok(_)=>panic!("expected rejection") } }
    }

    #[test]
    fn padded_exponent_candidate_requires_original_hash_match() {
        let raw=ROW.replace("5.80e-09","5.8e-9");
        let (mut r,m)=fixture(&raw,true);
        let mut manifest:Value=serde_json::from_slice(&m).unwrap();
        let mut packet:Value=serde_json::from_slice(&r.files[&PathBuf::from("q.json")]).unwrap();
        packet["records"][0]["target_sha256"]=json!(sha(compact(&raw,0,true).unwrap().as_bytes()));
        manifest["qualification_deltas"][0]=r.put("q.json",&packet.to_string());
        let m=manifest.to_string().into_bytes();
        let p=prepare(&m,&sha(&m),&mut r).unwrap();
        assert_eq!(p.events["row1"].legacy_method,"sorted_compact_padded_exponents");
        assert_eq!(p.rows[0].exact,raw);
        assert_eq!(p.rows[0].digest,sha(raw.as_bytes()));
        assert_ne!(p.rows[0].lexical_hash,p.events["row1"].legacy);
    }

    #[test]
    fn component_and_qualification_evidence_hashes_are_checked() {
        for name in ["base.json","review.json"] {
            let (mut r,m)=fixture(ROW,true);r.files.insert(PathBuf::from(name),b"{}".to_vec());
            assert!(prepare(&m,&sha(&m),&mut r).is_err());
        }
    }
    #[test]
    fn original_missingness_is_not_replaced_by_zero() {
        let p=ready(ROW,false);let v=projected(&p.rows[0],None).unwrap();
        assert!(v["unit"].is_null() && v["modelId"].is_null() && v["referenceKind"].is_null());
        assert!(v["recordJson"].as_str().unwrap().contains("uncertainty"));
        assert!(v["originalRowSha256"].is_null());
    }
    #[test]
    fn twenty_row_limit_and_determinism() {
        let mut p=ready(ROW,true);
        for i in 2..=43 {
            let raw=ROW.replace("row1",&format!("row{i:02}"));
            let q=ready(&raw,false);p.rows.extend(q.rows);
        }
        p.rows.sort_by(|a,b|a.id.cmp(&b.id));
        let a=batches(&p).unwrap();let b=batches(&p).unwrap();
        assert_eq!(a.len(),3);
        assert_eq!(a.iter().map(|x|&x.payload).collect::<Vec<_>>(),b.iter().map(|x|&x.payload).collect::<Vec<_>>());
        for plan in a {let v:Value=serde_json::from_str(&plan.payload).unwrap();
            assert!(v["observations"].as_array().unwrap().len()<=20);
            assert!(plan.payload.len()<=BODY_CAP && plan.source_objects.len()<=16);
            assert_eq!(plan.digest,sha(plan.payload.as_bytes()));
        }
    }
    #[test]
    fn object_limit_splits_batches_without_losing_events() {
        let mut p=ready(ROW,true);
        for i in 2..=18 {
            let raw=ROW.replace("row1",&format!("row{i}"));
            let mut q=ready(&raw,false);q.rows[0].evidence=sha(format!("source{i}").as_bytes());p.rows.extend(q.rows);
        }
        let plans=batches(&p).unwrap();assert_eq!(plans.len(),2);
        assert!(plans.iter().all(|b|b.source_objects.len()<=16));
        assert_eq!(plans.iter().map(|b|b.qualification_anchors.len()).sum::<usize>(),1);
    }
    #[test]
    fn body_limit_accounts_for_json_string_escaping() {
        let mut p=ready(ROW,false);p.rows.clear();
        for i in 0..20 {
            let raw=json!({"id":format!("r{i}"),"source_id":"s","text":"\"".repeat(20000)}).to_string();
            p.rows.extend(ready(&raw,false).rows);
        }
        let plans=batches(&p).unwrap();assert!(plans.len()>1);
        assert!(plans.iter().all(|b|b.payload.len()<=BODY_CAP));
    }
    #[test]
    fn invalid_metadata_and_calendar_stop_before_emission() {
        for raw in [
            ROW.replace("CrN",&"x".repeat(257)),
            ROW.replace("2026-01-02","2026-02-30"),
            ROW.replace("2026-01-02T03:04:05.123456+00:00","today"),
        ] { assert!(batches(&ready(&raw,false)).is_err()); }
        assert!(timestamp("2024-02-29T23:59:59.123456789Z").is_ok());
        assert!(timestamp("2026-01-02T03:04:05+24:00").is_err());
    }
    #[test]
    fn duplicate_row_ids_and_preannotated_rows_stop() {
        let duplicate=format!(r#"{{"batches":[{{"records":[{ROW},{ROW}]}}]}}"#);
        let (mut r,m)=fixture(ROW,false);let mut v:Value=serde_json::from_slice(&m).unwrap();
        v["base"]=r.put("base.json",&duplicate);let m=v.to_string().into_bytes();
        assert!(prepare(&m,&sha(&m),&mut r).is_err());
        let annotated=ROW.replacen("{",r#"{"corpus_qualification":{},"#,1);
        let (mut r,m)=fixture(&annotated,false);assert!(prepare(&m,&sha(&m),&mut r).is_err());
    }

    #[test]
    fn local_reader_checks_root_type_hash_and_size() {
        let root=std::env::temp_dir().join(format!("corpus-planner-test-{}",uuid::Uuid::new_v4()));
        fs::create_dir(&root).unwrap();
        struct Cleanup(PathBuf);
        impl Drop for Cleanup {fn drop(&mut self){let _=fs::remove_dir_all(&self.0);}}
        let _cleanup=Cleanup(root.clone());
        fs::write(root.join("good.json"),b"{}").unwrap();
        let root=fs::canonicalize(root).unwrap();
        let mut r=LocalReader{root:root.clone(),consumed:0};
        let e=Entry{path:PathBuf::from("good.json"),sha256:sha(b"{}"),bytes:Some(2)};
        assert_eq!(r.read(&e).unwrap(),b"{}");
        let mut bad=e.clone();bad.bytes=Some(3);assert!(r.read(&bad).is_err());
        bad=e.clone();bad.sha256="0".repeat(64);assert!(r.read(&bad).is_err());
        bad=e.clone();bad.path=PathBuf::from("../outside");assert!(r.read(&bad).is_err());
        bad=e.clone();bad.path=root.clone();assert!(r.read(&bad).is_err());
        #[cfg(unix)] {
            std::os::unix::fs::symlink(root.join("good.json"),root.join("link")).unwrap();
            bad=e.clone();bad.path=PathBuf::from("link");assert!(r.read(&bad).is_err());
        }
        r.consumed=INPUT_CAP;assert!(r.read(&e).is_err());
    }

    #[test]
    fn invalid_manifest_hash_and_oversized_rows_stop() {
        let (mut r,m)=fixture(ROW,false);assert!(prepare(&m,&"0".repeat(64),&mut r).is_err());
        let raw=json!({"id":"large","source_id":"s","text":"x".repeat(ROW_CAP)}).to_string();
        let (mut r,m)=fixture(&raw,false);assert!(prepare(&m,&sha(&m),&mut r).is_err());
    }
}
