use std::io::Write;
use std::process::{Command, Stdio};

fn invoke(bytes: &[u8]) -> std::process::Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_atlas-distill"))
        .args(["vacancy-reference", "--input", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child.stdin.take().unwrap().write_all(bytes).unwrap();
    child.wait_with_output().unwrap()
}

#[test]
fn incompatible_task_emits_report_and_fails_process() {
    let output = invoke(include_bytes!("fixtures/vacancy_uniform_bias.input.json"));
    assert!(!output.status.success());
    let result: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(result["task_assessment"], "incompatible_score_for_task");
    assert_eq!(result["components"]["full_mse_ev2"]["numerator"], "1");
    assert_eq!(result["selected_mse_ev2"]["numerator"], "0");
}

#[test]
fn full_score_is_descriptive_and_invalid_input_emits_no_report() {
    let mut input: serde_json::Value =
        serde_json::from_slice(include_bytes!("fixtures/vacancy_uniform_bias.input.json")).unwrap();
    input["score"] = serde_json::json!("full");
    let output = invoke(&serde_json::to_vec(&input).unwrap());
    assert!(output.status.success());
    let result: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(result["task_assessment"], "descriptive_components_only");
    assert_eq!(result["scientific_validation"], "not_established");
    input["rows"][0]["prediction"] = serde_json::json!("NaN");
    let invalid = invoke(&serde_json::to_vec(&input).unwrap());
    assert!(!invalid.status.success());
    assert!(invalid.stdout.is_empty());
}
