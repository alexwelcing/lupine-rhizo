//! Exact finite-candidate ordering; no claim of a physical ground state.
use std::collections::BTreeSet;
use std::io;
use std::path::PathBuf;

use anyhow::{ensure, Context, Result};
use clap::Args;
use num_rational::BigRational;
use num_traits::Zero;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::exact_input::{decimal, digest, identifier, read_bounded, MAX_BYTES};

#[derive(Debug, Clone, Args)]
pub struct CandidateOrderArgs {
    /// Bounded JSON file, or "-" for stdin. Output goes only to stdout.
    #[arg(long)]
    pub input: PathBuf,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Bounds {
    lower: String,
    upper: String,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Candidate {
    candidate_id: String,
    label: String,
    anchor: String,
    reference: Bounds,
    prediction: Bounds,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Scope {
    source_id: String,
    source_sha256: Option<String>,
    model_id: String,
    model_sha256: Option<String>,
    model_kind: String,
    material: String,
    composition: String,
    reference_convention: Option<String>,
    protocol: Option<String>,
    fit_exposure: Option<String>,
    candidate_set_id: String,
    candidate_set_sha256: Option<String>,
    candidate_set_scope: String,
    comparability: String,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Input {
    schema: String,
    unit: String,
    context: Scope,
    bounds_kind: String,
    rows: Vec<Candidate>,
}

#[derive(Debug, Serialize)]
struct Rational {
    numerator: String,
    denominator: String,
}

impl From<&BigRational> for Rational {
    fn from(value: &BigRational) -> Self {
        Self {
            numerator: value.numer().to_string(),
            denominator: value.denom().to_string(),
        }
    }
}

#[derive(Debug, Serialize)]
struct Gap {
    lower: Rational,
    upper: Rational,
}

#[derive(Debug, Serialize)]
struct Minima {
    possible: Vec<String>,
    guaranteed: Vec<String>,
    unique: Option<String>,
}

#[derive(Debug, Serialize)]
struct Pair {
    left: String,
    right: String,
    reference_gap_ev: Gap,
    prediction_gap_ev: Gap,
    gap_error_ev: Gap,
    reference_order: &'static str,
    prediction_order: &'static str,
    agreement: &'static str,
}

#[derive(Debug, Serialize)]
struct Assessment {
    arithmetic: &'static str,
    reference_minima: Minima,
    prediction_minima: Minima,
    choice_relation: &'static str,
    pairs: Vec<Pair>,
    issues: Vec<&'static str>,
    source_verification: &'static str,
    scientific_validation: &'static str,
    global_minimum_claim: &'static str,
    uniform_shift_changes_order: bool,
}

#[derive(Debug, Serialize)]
struct Report {
    schema: &'static str,
    input_sha256: String,
    input: Input,
    assessment: Assessment,
}

type Interval = (BigRational, BigRational);

fn bounded_text(value: &str) -> bool {
    !value.trim().is_empty() && value.len() <= 256
}

fn interval(value: &Bounds) -> Result<Interval> {
    let lower = decimal(&value.lower)?;
    let upper = decimal(&value.upper)?;
    ensure!(lower <= upper, "reversed interval");
    Ok((lower, upper))
}

fn gap(left: &Interval, right: &Interval) -> Interval {
    (&right.0 - &left.1, &right.1 - &left.0)
}

fn export_gap(value: &Interval) -> Gap {
    Gap {
        lower: Rational::from(&value.0),
        upper: Rational::from(&value.1),
    }
}

fn order(value: &Interval) -> &'static str {
    if value.0 > BigRational::zero() {
        "left_lower"
    } else if value.1 < BigRational::zero() {
        "right_lower"
    } else if value.0.is_zero() && value.1.is_zero() {
        "exact_tie"
    } else {
        "unresolved"
    }
}

/// Full Cartesian product of the supplied closed energy intervals.
fn minima(ids: &[String], values: &[Interval]) -> Minima {
    let mut possible = Vec::new();
    let mut guaranteed = Vec::new();
    let mut unique = None;
    for (i, value) in values.iter().enumerate() {
        if values
            .iter()
            .enumerate()
            .all(|(j, other)| i == j || value.0 <= other.1)
        {
            possible.push(ids[i].clone());
        }
        if values
            .iter()
            .enumerate()
            .all(|(j, other)| i == j || value.1 <= other.0)
        {
            guaranteed.push(ids[i].clone());
        }
        if values
            .iter()
            .enumerate()
            .all(|(j, other)| i == j || value.1 < other.0)
        {
            unique = Some(ids[i].clone());
        }
    }
    Minima {
        possible,
        guaranteed,
        unique,
    }
}

fn assess(input: &Input) -> Result<Assessment> {
    ensure!(input.schema == "lupine.candidate_order.input.v1", "schema");
    ensure!(input.unit == "eV", "unit");
    ensure!((2..=32).contains(&input.rows.len()), "candidate count");
    ensure!(
        [
            "exact_values",
            "assumed_printing_bounds",
            "declared_deterministic_bounds"
        ]
        .contains(&input.bounds_kind.as_str()),
        "bounds kind"
    );
    let c = &input.context;
    ensure!(
        identifier(&c.source_id) && identifier(&c.model_id) && identifier(&c.candidate_set_id),
        "identity"
    );
    for hash in [&c.source_sha256, &c.model_sha256, &c.candidate_set_sha256] {
        ensure!(hash.as_ref().is_none_or(|h| digest(h)), "digest");
    }
    for value in [&c.material, &c.composition] {
        ensure!(bounded_text(value), "scope text");
    }
    for value in [&c.reference_convention, &c.protocol, &c.fit_exposure] {
        ensure!(value.as_ref().is_none_or(|s| bounded_text(s)), "scope text");
    }
    ensure!(
        ["model", "reported", "synthetic"].contains(&c.model_kind.as_str()),
        "model kind"
    );
    ensure!(
        ["listed_only", "declared_exhaustive"].contains(&c.candidate_set_scope.as_str()),
        "candidate scope"
    );
    ensure!(
        ["declared", "unknown"].contains(&c.comparability.as_str()),
        "comparability"
    );
    let mut rows = input.rows.iter().collect::<Vec<_>>();
    rows.sort_by(|a, b| a.candidate_id.cmp(&b.candidate_id));
    let mut seen = BTreeSet::new();
    let mut ids = Vec::new();
    let mut reference = Vec::new();
    let mut prediction = Vec::new();
    for row in rows {
        ensure!(
            identifier(&row.candidate_id)
                && seen.insert(&row.candidate_id)
                && bounded_text(&row.label)
                && bounded_text(&row.anchor),
            "candidate identity"
        );
        let r = interval(&row.reference)?;
        let p = interval(&row.prediction)?;
        if input.bounds_kind == "exact_values" {
            ensure!(r.0 == r.1 && p.0 == p.1, "exact values cannot have width");
        }
        ids.push(row.candidate_id.clone());
        reference.push(r);
        prediction.push(p);
    }
    let reference_minima = minima(&ids, &reference);
    let prediction_minima = minima(&ids, &prediction);
    let choice_relation = match (&reference_minima.unique, &prediction_minima.unique) {
        (Some(a), Some(b)) if a == b => "same_unique_minimum",
        (Some(_), Some(_)) => "different_unique_minima",
        _ => "not_unique_or_unresolved",
    };
    let mut pairs = Vec::new();
    for i in 0..ids.len() {
        for j in i + 1..ids.len() {
            let r = gap(&reference[i], &reference[j]);
            let p = gap(&prediction[i], &prediction[j]);
            let ro = order(&r);
            let po = order(&p);
            let agreement = match (ro, po) {
                ("left_lower", "left_lower") | ("right_lower", "right_lower") => {
                    "same_strict_order"
                }
                ("left_lower", "right_lower") | ("right_lower", "left_lower") => {
                    "opposite_strict_order"
                }
                ("exact_tie", "exact_tie") => "exact_tie_both",
                _ => "unresolved",
            };
            let error = gap(&r, &p);
            pairs.push(Pair {
                left: ids[i].clone(),
                right: ids[j].clone(),
                reference_gap_ev: export_gap(&r),
                prediction_gap_ev: export_gap(&p),
                gap_error_ev: export_gap(&error),
                reference_order: ro,
                prediction_order: po,
                agreement,
            });
        }
    }
    let mut issues = vec!["source_and_physical_scope_unverified"];
    if c.comparability == "unknown" {
        issues.push("comparability_unknown");
    }
    if c.reference_convention.is_none() || c.protocol.is_none() {
        issues.push("reference_or_protocol_unknown");
    }
    if c.source_sha256.is_none() || c.model_sha256.is_none() || c.candidate_set_sha256.is_none() {
        issues.push("artifact_identity_unknown");
    }
    if c.fit_exposure.is_none() {
        issues.push("fitting_exposure_unknown");
    }
    if c.candidate_set_scope == "listed_only" {
        issues.push("candidate_search_not_exhaustive");
    } else {
        issues.push("exhaustiveness_declared_not_verified");
    }
    if input.bounds_kind == "assumed_printing_bounds" {
        issues.push("printing_bounds_are_assumptions");
    }
    if reference_minima.unique.is_none() {
        issues.push("no_unique_reference_minimum_over_bounds");
    }
    if prediction_minima.unique.is_none() {
        issues.push("no_unique_prediction_minimum_over_bounds");
    }
    Ok(Assessment {
        arithmetic: "exact_rational_closed_cartesian_bounds",
        reference_minima,
        prediction_minima,
        choice_relation,
        pairs,
        issues,
        source_verification: "not_performed",
        scientific_validation: "not_established",
        global_minimum_claim: "not_established",
        uniform_shift_changes_order: false,
    })
}

fn calculate(bytes: &[u8]) -> Result<Report> {
    ensure!(bytes.len() <= MAX_BYTES, "input exceeds byte bound");
    let input: Input = serde_json::from_slice(bytes).context("invalid candidate-order input")?;
    let assessment = assess(&input)?;
    let report = Report {
        schema: "lupine.candidate_order.report.v1",
        input_sha256: format!("{:x}", Sha256::digest(bytes)),
        input,
        assessment,
    };
    ensure!(
        serde_json::to_vec(&report)?.len() < MAX_BYTES,
        "report exceeds byte bound"
    );
    Ok(report)
}

pub fn run(args: CandidateOrderArgs) -> Result<()> {
    let bytes = if args.input == std::path::Path::new("-") {
        read_bounded(io::stdin().lock())?
    } else {
        read_bounded(std::fs::File::open(&args.input)?)?
    };
    // Compact JSON preserves the same byte ceiling used by the inspector.
    println!("{}", serde_json::to_string(&calculate(&bytes)?)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{json, Value};

    fn fixture() -> Value {
        serde_json::from_slice(include_bytes!(
            "../../tests/fixtures/candidate_order.input.json"
        ))
        .unwrap()
    }

    fn report(value: &Value) -> Result<Value> {
        Ok(serde_json::to_value(calculate(&serde_json::to_vec(
            value,
        )?)?)?)
    }

    #[test]
    fn shared_fixture_matches_exact_assessment() {
        let actual = report(&fixture()).unwrap();
        let expected: Value = serde_json::from_slice(include_bytes!(
            "../../tests/fixtures/candidate_order.assessment.json"
        ))
        .unwrap();
        assert_eq!(actual["assessment"], expected);
    }

    #[test]
    fn all_minima_sets_match_exhaustive_box_corners() {
        let choices = [(0, 0), (0, 1), (1, 1), (1, 2)];
        let ids = vec!["a".into(), "b".into(), "c".into()];
        for code in 0..64 {
            let values: Vec<_> = (0..3)
                .map(|i| {
                    let (l, u) = choices[(code >> (2 * i)) & 3];
                    (
                        BigRational::from_integer(l.into()),
                        BigRational::from_integer(u.into()),
                    )
                })
                .collect();
            let got = minima(&ids, &values);
            let mut possible = BTreeSet::new();
            let mut guaranteed: BTreeSet<_> = ids.iter().cloned().collect();
            let mut unique = None;
            for mask in 0..8 {
                let point: Vec<_> = values
                    .iter()
                    .enumerate()
                    .map(|(i, v)| {
                        if mask & (1 << i) == 0 {
                            v.0.clone()
                        } else {
                            v.1.clone()
                        }
                    })
                    .collect();
                let best = point.iter().min().unwrap();
                let winners: BTreeSet<_> = point
                    .iter()
                    .enumerate()
                    .filter(|(_, v)| *v == best)
                    .map(|(i, _)| ids[i].clone())
                    .collect();
                possible.extend(winners.iter().cloned());
                guaranteed = guaranteed.intersection(&winners).cloned().collect();
                let winner = if winners.len() == 1 {
                    winners.first().cloned()
                } else {
                    None
                };
                if mask == 0 {
                    unique = winner;
                } else if unique != winner {
                    unique = None;
                }
            }
            assert_eq!(got.possible, possible.into_iter().collect::<Vec<_>>());
            assert_eq!(got.guaranteed, guaranteed.into_iter().collect::<Vec<_>>());
            assert_eq!(got.unique, unique);
        }
    }

    #[test]
    fn shifts_and_input_permutation_preserve_assessment() {
        let mut input = fixture();
        let expected = report(&input).unwrap()["assessment"].clone();
        input["rows"].as_array_mut().unwrap().reverse();
        for row in input["rows"].as_array_mut().unwrap() {
            for field in ["reference", "prediction"] {
                for edge in ["lower", "upper"] {
                    let original = row[field][edge].as_str().unwrap().parse::<i64>().unwrap();
                    row[field][edge] = json!((original + 100).to_string());
                }
            }
        }
        assert_eq!(report(&input).unwrap()["assessment"], expected);
    }

    #[test]
    fn closed_endpoint_ties_are_not_unique_minima() {
        let mut input = fixture();
        input["rows"][0]["reference"] = json!({"lower":"1", "upper":"2"});
        input["rows"][1]["reference"] = json!({"lower":"2", "upper":"3"});
        input["bounds_kind"] = json!("declared_deterministic_bounds");
        let got = report(&input).unwrap();
        assert!(got["assessment"]["reference_minima"]["unique"].is_null());
        assert_eq!(
            got["assessment"]["reference_minima"]["guaranteed"],
            json!(["a"])
        );
        assert_eq!(
            got["assessment"]["reference_minima"]["possible"],
            json!(["a", "b"])
        );
    }

    #[test]
    fn tiny_signed_gaps_survive_without_float_rounding() {
        let mut input = fixture();
        input["rows"][0]["reference"] = json!({"lower":"0", "upper":"0"});
        input["rows"][1]["reference"] =
            json!({"lower":"0.00000000000000000001", "upper":"0.00000000000000000001"});
        let got = report(&input).unwrap();
        assert_eq!(
            got["assessment"]["pairs"][0]["reference_order"],
            "left_lower"
        );
        assert_eq!(
            got["assessment"]["pairs"][0]["reference_gap_ev"]["lower"]["denominator"],
            "100000000000000000000"
        );
    }

    #[test]
    fn unknowns_and_exhaustiveness_never_establish_physical_acceptance() {
        let mut input = fixture();
        input["context"]["candidate_set_scope"] = json!("declared_exhaustive");
        input["context"]["comparability"] = json!("unknown");
        let got = report(&input).unwrap();
        let issues = got["assessment"]["issues"].as_array().unwrap();
        assert!(issues.contains(&json!("exhaustiveness_declared_not_verified")));
        assert!(issues.contains(&json!("comparability_unknown")));
        assert_eq!(got["assessment"]["global_minimum_claim"], "not_established");
    }

    #[test]
    fn malformed_or_mixed_scope_inputs_fail() {
        for (pointer, bad) in [
            ("/unit", json!("eV_per_vacancy")),
            ("/bounds_kind", json!("statistical_confidence")),
            ("/rows/0/reference/lower", json!("NaN")),
            ("/rows/0/reference/lower", json!("1e-3")),
            ("/rows/0/reference/lower", json!(1)),
            ("/rows/0/reference/lower", json!("9")),
            ("/rows/1/candidate_id", json!("a")),
            ("/context/source_sha256", json!("fabricated")),
            ("/context/protocol", json!("")),
        ] {
            let mut input = fixture();
            *input.pointer_mut(pointer).unwrap() = bad;
            assert!(report(&input).is_err(), "{pointer}");
        }
        let mut input = fixture();
        input["rows"].as_array_mut().unwrap().truncate(1);
        assert!(report(&input).is_err());
        input = fixture();
        input["rows"][0]["reference"]["upper"] = json!("2");
        assert!(report(&input).is_err());
        assert!(calculate(&vec![b' '; MAX_BYTES + 1]).is_err());
    }
}
