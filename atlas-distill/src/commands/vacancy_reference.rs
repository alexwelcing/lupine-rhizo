//! Exact descriptive vacancy-label error components; no physical admission.
use std::collections::{BTreeMap, BTreeSet};
use std::io::{self, Read};
use std::path::PathBuf;

use anyhow::{bail, ensure, Context, Result};
use clap::Args;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Zero;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const MAX_BYTES: usize = 524_288;
const MAX_ROWS: usize = 4096;

#[derive(Debug, Clone, Args)]
pub struct VacancyReferenceArgs {
    /// Bounded JSON file, or "-" for stdin. Results go only to stdout.
    #[arg(long)]
    pub input: PathBuf,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Row {
    site_id: String,
    species: String,
    prediction: String,
    reference: String,
}

#[derive(Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "snake_case")]
enum ReferenceDefinition {
    SelfConsistentSpeciesAverage,
    ExternalReservoir,
    Unknown,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ContextIdentity {
    source_id: String,
    source_sha256: String,
    cohort_sha256: Option<String>,
    parent_id: String,
    parent_atom_count: usize,
    cohort_size: usize,
    complete_cohort: bool,
    reference_definition: ReferenceDefinition,
    prediction_id: String,
    prediction_kind: PredictionKind,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    reference_protocol: Option<ReferenceProtocol>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ParentSpecies {
    species: String,
    atoms: usize,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct CalibrationSpecies {
    species: String,
    sites: usize,
    weight: Rational,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct CalibrationCohort {
    cohort_sha256: Option<String>,
    site_count: usize,
    species: Vec<CalibrationSpecies>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
enum EnergyZeroAlignment {
    DeclaredShared,
    Unknown,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ReferenceProtocol {
    parent_species: Option<Vec<ParentSpecies>>,
    evaluation_cohort_sha256: Option<String>,
    reference_calibration: Option<CalibrationCohort>,
    prediction_calibration: Option<CalibrationCohort>,
    energy_zero_alignment: EnergyZeroAlignment,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
enum PredictionKind {
    Model,
    Reported,
    Synthetic,
}

#[derive(Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "snake_case")]
enum Score {
    Full,
    WithinSpeciesCentered,
}

#[derive(Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "snake_case")]
enum Task {
    WithinSpeciesVariation,
    FormationEnergy,
    VacancyConcentration,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    schema: String,
    unit: String,
    context: ContextIdentity,
    score: Score,
    task: Task,
    rows: Vec<Row>,
}

#[derive(Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
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
struct Group {
    species: String,
    sites: usize,
    mean_error_ev: Rational,
    reference_mean_ev: Rational,
    prediction_mean_ev: Rational,
}

#[derive(Debug, Serialize)]
struct Components {
    full_mse_ev2: Rational,
    within_species_mse_ev2: Rational,
    overall_mean_error_ev: Rational,
    overall_bias_squared_ev2: Rational,
    species_mean_imbalance_mse_ev2: Rational,
}

#[derive(Debug, Serialize)]
struct ResultDocument {
    schema: &'static str,
    input_sha256: String,
    reference_rows_sha256: String,
    arithmetic: &'static str,
    unit: &'static str,
    context: ContextIdentity,
    rows: usize,
    groups: Vec<Group>,
    components: Components,
    selected_score: Score,
    selected_mse_ev2: Rational,
    intended_task: Task,
    task_assessment: &'static str,
    issues: Vec<&'static str>,
    decomposition_identity_exact: bool,
    reference_species_means_equal_exactly: bool,
    prediction_species_means_equal_exactly: bool,
    source_verification: &'static str,
    scientific_validation: &'static str,
    limitations: Vec<&'static str>,
}

fn decimal(text: &str) -> Result<BigRational> {
    ensure!(!text.is_empty() && text.len() <= 64, "decimal length");
    let unsigned = text.strip_prefix('-').unwrap_or(text);
    let parts: Vec<_> = unsigned.split('.').collect();
    ensure!(
        parts.len() <= 2
            && parts
                .iter()
                .all(|part| { !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_digit()) }),
        "expected a bounded decimal string without exponent"
    );
    let fractional = parts.get(1).map_or(0, |part| part.len());
    let digits = parts.concat();
    let mut numerator = BigInt::parse_bytes(digits.as_bytes(), 10).context("decimal digits")?;
    if text.starts_with('-') {
        numerator = -numerator;
    }
    Ok(BigRational::new(
        numerator,
        BigInt::from(10u8).pow(fractional as u32),
    ))
}

fn identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 96
        && value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"_.:-".contains(&c))
}

fn digest(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}

fn mean(values: &[BigRational]) -> BigRational {
    values.iter().sum::<BigRational>() / BigInt::from(values.len())
}

fn square(value: &BigRational) -> BigRational {
    value * value
}

fn calibration_weight(value: &Rational) -> Result<BigRational> {
    for digits in [&value.numerator, &value.denominator] {
        ensure!(
            !digits.is_empty()
                && digits.len() <= 64
                && digits.bytes().all(|c| c.is_ascii_digit())
                && (digits == "0" || !digits.starts_with('0')),
            "calibration weight format"
        );
    }
    let n = BigInt::parse_bytes(value.numerator.as_bytes(), 10).context("weight numerator")?;
    let d = BigInt::parse_bytes(value.denominator.as_bytes(), 10).context("weight denominator")?;
    ensure!(d > BigInt::zero(), "calibration weight denominator");
    Ok(BigRational::new(n, d))
}

/// Checks declared metadata, never the source files or physical reservoir.
fn reference_protocol_issues(input: &Input) -> Result<Vec<&'static str>> {
    let Some(protocol) = &input.context.reference_protocol else {
        return Ok(vec!["reference_protocol_unknown"]);
    };
    let mut issues = Vec::new();
    if let Some(hash) = &protocol.evaluation_cohort_sha256 {
        ensure!(digest(hash), "evaluation cohort identity");
    } else {
        issues.push("evaluation_cohort_unknown");
    }
    if matches!(protocol.energy_zero_alignment, EnergyZeroAlignment::Unknown) {
        issues.push("energy_zero_alignment_unknown");
    }
    let mut parent = BTreeMap::new();
    if let Some(species) = &protocol.parent_species {
        ensure!(
            !species.is_empty() && species.len() <= 128,
            "parent species bound"
        );
        for item in species {
            ensure!(
                identifier(&item.species) && item.atoms > 0 && item.atoms <= MAX_ROWS,
                "parent species counts"
            );
            ensure!(
                parent.insert(item.species.as_str(), item.atoms).is_none(),
                "duplicate parent species"
            );
        }
        ensure!(
            parent.values().sum::<usize>() == input.context.parent_atom_count,
            "parent composition total"
        );
        let mut evaluated = BTreeMap::new();
        for row in &input.rows {
            *evaluated.entry(row.species.as_str()).or_insert(0usize) += 1;
        }
        for (species, sites) in evaluated {
            ensure!(
                parent.get(species).is_some_and(|n| sites <= *n),
                "evaluation species membership"
            );
        }
    } else {
        issues.push("parent_composition_unknown");
    }
    for (calibration, missing, mismatch, unknown_identity) in [
        (
            &protocol.reference_calibration,
            "reference_calibration_unknown",
            "reference_calibration_weights_differ",
            "reference_calibration_cohort_unknown",
        ),
        (
            &protocol.prediction_calibration,
            "prediction_calibration_unknown",
            "prediction_calibration_weights_differ",
            "prediction_calibration_cohort_unknown",
        ),
    ] {
        let Some(calibration) = calibration else {
            if input.context.reference_definition
                == ReferenceDefinition::SelfConsistentSpeciesAverage
            {
                issues.push(missing);
            }
            continue;
        };
        if let Some(hash) = &calibration.cohort_sha256 {
            ensure!(digest(hash), "calibration cohort identity");
        } else {
            issues.push(unknown_identity);
        }
        ensure!(
            calibration.site_count > 0
                && calibration.site_count <= input.context.parent_atom_count
                && !calibration.species.is_empty()
                && calibration.species.len() <= 128,
            "calibration cohort bounds"
        );
        let mut seen = BTreeSet::new();
        let mut total_sites = 0usize;
        let mut total_weight = BigRational::zero();
        let mut weights_match = true;
        for item in &calibration.species {
            ensure!(
                identifier(&item.species) && item.sites > 0 && item.sites <= MAX_ROWS,
                "calibration species counts"
            );
            ensure!(
                seen.insert(item.species.as_str()),
                "duplicate calibration species"
            );
            total_sites += item.sites;
            let weight = calibration_weight(&item.weight)?;
            let numerator =
                total_weight.numer() * weight.denom() + weight.numer() * total_weight.denom();
            let denominator = total_weight.denom() * weight.denom();
            ensure!(
                numerator.to_str_radix(10).len() <= 4096
                    && denominator.to_str_radix(10).len() <= 4096,
                "calibration arithmetic exceeds intermediate bound"
            );
            total_weight = BigRational::new(numerator, denominator);
            if !parent.is_empty() {
                let atoms = parent
                    .get(item.species.as_str())
                    .context("calibration species membership")?;
                ensure!(
                    item.sites <= *atoms,
                    "calibration site count exceeds parent species"
                );
                weights_match &= weight
                    == BigRational::new((*atoms).into(), input.context.parent_atom_count.into());
            }
        }
        ensure!(
            total_sites == calibration.site_count,
            "calibration count total"
        );
        ensure!(
            total_weight == BigRational::from_integer(1.into()),
            "calibration weights must sum to one"
        );
        if input.context.reference_definition == ReferenceDefinition::SelfConsistentSpeciesAverage {
            ensure!(
                input.rows.iter().all(|r| seen.contains(r.species.as_str())),
                "evaluation species lacks calibration"
            );
            if !parent.is_empty() && (!weights_match || seen.len() != parent.len()) {
                issues.push(mismatch);
            }
        }
    }
    Ok(issues)
}

fn assess(input: &Input) -> Result<(&'static str, Vec<&'static str>)> {
    let mut issues = reference_protocol_issues(input)?;
    if input.context.cohort_sha256.is_none() {
        issues.push("parent_cohort_identity_unknown");
    }
    let species: BTreeSet<_> = input.rows.iter().map(|r| &r.species).collect();
    if input.rows.len() == species.len() {
        issues.push("no_within_species_contrasts");
    }
    if input.score == Score::WithinSpeciesCentered && input.task != Task::WithinSpeciesVariation {
        issues.push("centered_score_discards_formation_energy_level");
    }
    if input.task == Task::VacancyConcentration {
        issues.push("concentration_requires_separate_thermodynamic_model");
    }
    if input.context.reference_definition == ReferenceDefinition::Unknown {
        issues.push("reference_definition_unknown");
    }
    if !input.context.complete_cohort {
        issues.push("selected_subset_does_not_redefine_reference_cohort");
    }
    let status = if input.score == Score::WithinSpeciesCentered
        && input.task != Task::WithinSpeciesVariation
    {
        "incompatible_score_for_task"
    } else if issues.is_empty() {
        "descriptive_components_only"
    } else {
        "scope_unresolved"
    };
    Ok((status, issues))
}

fn calculate(bytes: &[u8]) -> Result<ResultDocument> {
    ensure!(bytes.len() <= MAX_BYTES, "input exceeds byte bound");
    let input: Input = serde_json::from_slice(bytes).context("invalid vacancy input")?;
    ensure!(
        input.schema == "lupine.vacancy_reference.input.v1",
        "schema"
    );
    ensure!(input.unit == "eV_per_vacancy", "unit");
    ensure!(
        !input.rows.is_empty() && input.rows.len() <= MAX_ROWS,
        "row bound"
    );
    let context = &input.context;
    ensure!(
        identifier(&context.source_id)
            && identifier(&context.parent_id)
            && identifier(&context.prediction_id)
            && digest(&context.source_sha256)
            && context.cohort_sha256.as_ref().is_none_or(|h| digest(h)),
        "identity format"
    );
    ensure!(
        context.parent_atom_count > 0
            && context.parent_atom_count <= MAX_ROWS
            && context.cohort_size == context.parent_atom_count
            && input.rows.len() <= context.cohort_size
            && (!context.complete_cohort || input.rows.len() == context.cohort_size),
        "cohort membership/count contract"
    );
    let mut sites = BTreeSet::new();
    let mut grouped: BTreeMap<String, Vec<(BigRational, BigRational)>> = BTreeMap::new();
    for row in &input.rows {
        ensure!(
            identifier(&row.site_id) && identifier(&row.species),
            "site/species identity"
        );
        ensure!(sites.insert(&row.site_id), "duplicate site identity");
        grouped
            .entry(row.species.clone())
            .or_default()
            .push((decimal(&row.prediction)?, decimal(&row.reference)?));
    }
    ensure!(grouped.len() <= 128, "species bound");
    let mut reference_rows: Vec<_> = input
        .rows
        .iter()
        .map(|row| (&row.site_id, &row.species, &row.reference))
        .collect();
    reference_rows.sort();
    let reference_rows_sha256 =
        format!("{:x}", Sha256::digest(serde_json::to_vec(&reference_rows)?));
    let errors: Vec<_> = grouped
        .values()
        .flatten()
        .map(|(prediction, reference)| prediction - reference)
        .collect();
    let overall = mean(&errors);
    let count = BigInt::from(errors.len());
    let full = errors.iter().map(square).sum::<BigRational>() / count.clone();
    let mut within_sum = BigRational::zero();
    let mut imbalance_sum = BigRational::zero();
    let mut groups = Vec::new();
    let mut reference_means = Vec::new();
    let mut prediction_means = Vec::new();
    for (species, rows) in &grouped {
        let residuals: Vec<_> = rows.iter().map(|(p, r)| p - r).collect();
        let group_mean = mean(&residuals);
        within_sum += residuals
            .iter()
            .map(|value| square(&(value - &group_mean)))
            .sum::<BigRational>();
        imbalance_sum += square(&(&group_mean - &overall)) * BigInt::from(rows.len());
        let reference_mean = mean(&rows.iter().map(|(_, r)| r.clone()).collect::<Vec<_>>());
        let prediction_mean = mean(&rows.iter().map(|(p, _)| p.clone()).collect::<Vec<_>>());
        groups.push(Group {
            species: species.clone(),
            sites: rows.len(),
            mean_error_ev: (&group_mean).into(),
            reference_mean_ev: (&reference_mean).into(),
            prediction_mean_ev: (&prediction_mean).into(),
        });
        reference_means.push(reference_mean);
        prediction_means.push(prediction_mean);
    }
    let within = within_sum / count.clone();
    let imbalance = imbalance_sum / count.clone();
    let bias_squared = square(&overall);
    ensure!(
        full == &within + &imbalance + &bias_squared,
        "internal decomposition mismatch"
    );
    let selected = match input.score {
        Score::Full => (&full).into(),
        Score::WithinSpeciesCentered => (&within).into(),
    };
    let (task_assessment, issues) = assess(&input)?;
    Ok(ResultDocument {
        schema: "lupine.vacancy_reference.result.v1",
        input_sha256: format!("{:x}", Sha256::digest(bytes)),
        reference_rows_sha256,
        arithmetic: "exact_rational_on_supplied_decimal_strings",
        unit: "eV_per_vacancy",
        rows: errors.len(),
        groups,
        components: Components {
            full_mse_ev2: (&full).into(),
            within_species_mse_ev2: (&within).into(),
            overall_mean_error_ev: (&overall).into(),
            overall_bias_squared_ev2: (&bias_squared).into(),
            species_mean_imbalance_mse_ev2: (&imbalance).into(),
        },
        selected_score: input.score,
        selected_mse_ev2: selected,
        intended_task: input.task,
        task_assessment,
        issues,
        decomposition_identity_exact: true,
        reference_species_means_equal_exactly: reference_means
            .windows(2)
            .all(|pair| pair[0] == pair[1]),
        prediction_species_means_equal_exactly: prediction_means
            .windows(2)
            .all(|pair| pair[0] == pair[1]),
        context: input.context,
        source_verification: "not_performed",
        scientific_validation: "not_established",
        limitations: vec![
            "Equal site weights within the supplied subset; not equal structure weights.",
            "No chemical potentials are recomputed and no printed values are projected.",
            "Hashes bind supplied bytes/declarations, not source or model authenticity.",
            "Raw total energies, external reservoirs and formation labels are different observables.",
            "No physical acceptance threshold, independence claim, simulation or publication.",
        ],
    })
}

fn read_bounded(reader: impl Read) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    reader
        .take((MAX_BYTES + 1) as u64)
        .read_to_end(&mut bytes)?;
    ensure!(bytes.len() <= MAX_BYTES, "input exceeds byte bound");
    Ok(bytes)
}

pub fn run(args: VacancyReferenceArgs) -> Result<()> {
    let bytes = if args.input == std::path::Path::new("-") {
        read_bounded(io::stdin().lock())?
    } else {
        read_bounded(std::fs::File::open(&args.input)?)?
    };
    let result = calculate(&bytes)?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    if result.task_assessment == "incompatible_score_for_task" {
        bail!("centered score is incompatible with the requested task");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{json, Value};

    fn fixture() -> Value {
        json!({
            "schema": "lupine.vacancy_reference.input.v1",
            "unit": "eV_per_vacancy",
            "context": {
                "source_id": "synthetic-reference", "source_sha256": "a".repeat(64),
                "cohort_sha256": "b".repeat(64), "parent_id": "synthetic-parent",
                "parent_atom_count": 3, "cohort_size": 3, "complete_cohort": true,
                "reference_definition": "self_consistent_species_average",
                "prediction_id": "synthetic-shift", "prediction_kind": "synthetic"
            },
            "score": "within_species_centered", "task": "formation_energy",
            "rows": [
                {"site_id":"a", "species":"Cr", "prediction":"1.1", "reference":"1.0"},
                {"site_id":"b", "species":"Cr", "prediction":"2.1", "reference":"2.0"},
                {"site_id":"c", "species":"Ni", "prediction":"1.6", "reference":"1.5"}
            ]
        })
    }

    fn run_value(value: &Value) -> Result<ResultDocument> {
        calculate(&serde_json::to_vec(value)?)
    }

    fn ratio(n: i64, d: i64) -> Rational {
        (&BigRational::new(n.into(), d.into())).into()
    }

    #[test]
    fn centered_perfect_score_does_not_certify_uniform_bias() {
        let result = run_value(&fixture()).unwrap();
        assert_eq!(result.selected_mse_ev2, ratio(0, 1));
        assert_eq!(result.components.full_mse_ev2, ratio(1, 100));
        assert_eq!(result.components.overall_mean_error_ev, ratio(1, 10));
        assert_eq!(result.task_assessment, "incompatible_score_for_task");
        assert_eq!(result.scientific_validation, "not_established");
    }

    #[test]
    fn unequal_species_counts_use_site_weights() {
        let mut value = fixture();
        value["rows"][0]["prediction"] = json!("2");
        value["rows"][1]["prediction"] = json!("3");
        value["rows"][2]["prediction"] = json!("-0.5");
        let result = run_value(&value).unwrap();
        assert_eq!(result.components.full_mse_ev2, ratio(2, 1));
        assert_eq!(result.components.overall_bias_squared_ev2, ratio(0, 1));
        assert_eq!(
            result.components.species_mean_imbalance_mse_ev2,
            ratio(2, 1)
        );
    }

    #[test]
    fn within_species_variation_is_preserved() {
        let mut value = fixture();
        value["rows"][0]["prediction"] = json!("0");
        value["rows"][1]["prediction"] = json!("3");
        value["rows"][2]["prediction"] = json!("1.5");
        value["task"] = json!("within_species_variation");
        let result = run_value(&value).unwrap();
        assert_eq!(result.components.within_species_mse_ev2, ratio(2, 3));
        assert_eq!(result.components.full_mse_ev2, ratio(2, 3));
        assert_eq!(result.task_assessment, "scope_unresolved");
        assert!(result.issues.contains(&"reference_protocol_unknown"));
    }

    #[test]
    fn no_rounding_or_forced_gauge_equality() {
        let mut value = fixture();
        value["rows"][2]["reference"] = json!("1.50000000000000001");
        let result = run_value(&value).unwrap();
        assert!(!result.reference_species_means_equal_exactly);
        assert_ne!(
            result.components.species_mean_imbalance_mse_ev2,
            ratio(0, 1)
        );
    }

    #[test]
    fn ordering_does_not_change_components_but_input_hash_binds_bytes() {
        let first = run_value(&fixture()).unwrap();
        let mut reversed = fixture();
        reversed["rows"].as_array_mut().unwrap().reverse();
        let second = run_value(&reversed).unwrap();
        assert_eq!(
            serde_json::to_value(first.components).unwrap(),
            serde_json::to_value(second.components).unwrap()
        );
        assert_ne!(first.input_sha256, second.input_sha256);
    }

    #[test]
    fn full_score_still_does_not_validate_concentrations() {
        let mut value = fixture();
        value["score"] = json!("full");
        value["task"] = json!("vacancy_concentration");
        let result = run_value(&value).unwrap();
        assert_eq!(result.task_assessment, "scope_unresolved");
        assert_eq!(result.scientific_validation, "not_established");
    }

    #[test]
    fn subset_retains_original_cohort_identity() {
        let mut value = fixture();
        value["context"]["complete_cohort"] = json!(false);
        value["rows"].as_array_mut().unwrap().pop();
        let result = run_value(&value).unwrap();
        assert_eq!(result.context.cohort_size, 3);
        assert_eq!(result.rows, 2);
        assert_eq!(result.task_assessment, "incompatible_score_for_task");
        value["context"]["complete_cohort"] = json!(true);
        assert!(run_value(&value).is_err());
    }

    #[test]
    fn rejects_duplicate_missing_and_unknown_fields() {
        let mut value = fixture();
        value["rows"][1]["site_id"] = json!("a");
        assert!(run_value(&value).is_err());
        value = fixture();
        value["rows"][0]
            .as_object_mut()
            .unwrap()
            .remove("reference");
        assert!(run_value(&value).is_err());
        value = fixture();
        value["pretend_verified"] = json!(true);
        assert!(run_value(&value).is_err());
        let bytes = serde_json::to_string(&fixture()).unwrap();
        let duplicate = bytes.replacen(
            "\"unit\":\"eV_per_vacancy\"",
            "\"unit\":\"eV_per_vacancy\",\"unit\":\"eV_per_vacancy\"",
            1,
        );
        assert!(calculate(duplicate.as_bytes()).is_err());
    }

    #[test]
    fn rejects_invalid_numbers_and_limits() {
        for bad in ["NaN", "inf", "1e3", "+1", ".2", "1.", "--1", " 1", ""] {
            assert!(decimal(bad).is_err(), "{bad}");
        }
        assert!(decimal(&"1".repeat(65)).is_err());
        assert_eq!(decimal("-0.00").unwrap(), BigRational::zero());
        assert!(read_bounded(vec![b' '; MAX_BYTES + 1].as_slice()).is_err());
        let mut value = fixture();
        value["unit"] = json!("meV_per_vacancy");
        assert!(run_value(&value).is_err());
        value = fixture();
        value["rows"] = json!([]);
        assert!(run_value(&value).is_err());
    }

    fn protocol_fixture() -> Value {
        serde_json::from_str(include_str!(
            "../../tests/fixtures/vacancy_calibration.protocol.json"
        ))
        .unwrap()
    }

    #[test]
    fn separate_calibration_weights_are_checked_without_redefining_evaluation() {
        let mut value = fixture();
        value["context"]["reference_protocol"] = protocol_fixture();
        value["score"] = json!("full");
        let good = run_value(&value).unwrap();
        assert_eq!(good.task_assessment, "descriptive_components_only");
        assert!(good.issues.is_empty());
        for kind in ["reference_calibration", "prediction_calibration"] {
            for i in 0..2 {
                value["context"]["reference_protocol"][kind]["species"][i]["weight"] =
                    json!({"numerator":"1", "denominator":"2"});
            }
        }
        let mismatch = run_value(&value).unwrap();
        assert!(mismatch
            .issues
            .contains(&"reference_calibration_weights_differ"));
        assert!(mismatch
            .issues
            .contains(&"prediction_calibration_weights_differ"));
        assert_eq!(mismatch.task_assessment, "scope_unresolved");
        assert_eq!(
            mismatch.components.full_mse_ev2,
            good.components.full_mse_ev2
        );
        assert_eq!(mismatch.reference_rows_sha256, good.reference_rows_sha256);
        assert_ne!(mismatch.input_sha256, good.input_sha256);
    }

    #[test]
    fn calibration_metadata_unknowns_remain_unknown() {
        let mut value = fixture();
        value["context"]["reference_protocol"] = json!({
            "parent_species": null, "evaluation_cohort_sha256": null,
            "reference_calibration": null, "prediction_calibration": null,
            "energy_zero_alignment": "unknown"
        });
        let result = run_value(&value).unwrap();
        for issue in [
            "parent_composition_unknown",
            "evaluation_cohort_unknown",
            "reference_calibration_unknown",
            "prediction_calibration_unknown",
            "energy_zero_alignment_unknown",
        ] {
            assert!(result.issues.contains(&issue));
        }
    }

    #[test]
    fn singleton_groups_are_not_evidence_of_perfect_within_species_prediction() {
        let mut value = fixture();
        value["context"]["complete_cohort"] = json!(false);
        value["rows"].as_array_mut().unwrap().remove(0);
        value["task"] = json!("within_species_variation");
        let result = run_value(&value).unwrap();
        assert_eq!(result.components.within_species_mse_ev2, ratio(0, 1));
        assert!(result.issues.contains(&"no_within_species_contrasts"));
        assert_eq!(result.task_assessment, "scope_unresolved");
    }

    #[test]
    fn rejects_invalid_calibration_counts_weights_and_membership() {
        for mutation in 0..9 {
            let mut value = fixture();
            value["context"]["reference_protocol"] = protocol_fixture();
            let p = &mut value["context"]["reference_protocol"];
            match mutation {
                0 => p["parent_species"][0]["atoms"] = json!(3),
                1 => p["parent_species"][1]["species"] = json!("Cr"),
                2 => p["reference_calibration"]["site_count"] = json!(3),
                3 => p["reference_calibration"]["species"][0]["species"] = json!("X"),
                4 => p["reference_calibration"]["species"][0]["weight"]["numerator"] = json!("1"),
                5 => p["reference_calibration"]["species"][0]["weight"]["denominator"] = json!("0"),
                6 => p["reference_calibration"]["species"][0]["weight"]["numerator"] = json!("-1"),
                7 => p["evaluation_cohort_sha256"] = json!("unknown-hash"),
                _ => p["reference_calibration"]["species"][1]["species"] = json!("Cr"),
            }
            assert!(run_value(&value).is_err(), "mutation {mutation}");
        }
    }

    #[test]
    fn known_weights_survive_unknown_cohort_identities() {
        let mut value = fixture();
        value["context"]["reference_protocol"] = protocol_fixture();
        value["context"]["cohort_sha256"] = Value::Null;
        let p = &mut value["context"]["reference_protocol"];
        p["reference_calibration"]["cohort_sha256"] = Value::Null;
        p["prediction_calibration"]["cohort_sha256"] = Value::Null;
        value["score"] = json!("full");
        let result = run_value(&value).unwrap();
        assert!(result.issues.contains(&"parent_cohort_identity_unknown"));
        assert!(result
            .issues
            .contains(&"reference_calibration_cohort_unknown"));
        assert!(result
            .issues
            .contains(&"prediction_calibration_cohort_unknown"));
        assert!(!result
            .issues
            .contains(&"reference_calibration_weights_differ"));
        assert_eq!(result.components.full_mse_ev2, ratio(1, 100));
        assert_eq!(result.task_assessment, "scope_unresolved");
    }

    #[test]
    fn shared_result_fixture_matches_exact_checker_output() {
        let result = calculate(include_bytes!(
            "../../tests/fixtures/vacancy_uniform_bias.input.json"
        ))
        .unwrap();
        let expected: Value = serde_json::from_str(include_str!(
            "../../tests/fixtures/vacancy_uniform_bias.expected.json"
        ))
        .unwrap();
        assert_eq!(serde_json::to_value(result).unwrap(), expected);
    }
}
