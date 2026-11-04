use std::io::Write;
use std::process::{Command, Stdio};

fn invoke(bytes: &[u8]) -> std::process::Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_atlas-distill"))
        .args(["candidate-order", "--input", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child.stdin.take().unwrap().write_all(bytes).unwrap();
    child.wait_with_output().unwrap()
}

#[test]
fn conflicting_order_is_a_descriptive_report_not_execution_failure() {
    let bytes = include_bytes!("fixtures/candidate_order.input.json");
    let output = invoke(bytes);
    assert!(output.status.success());
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    let input: serde_json::Value = serde_json::from_slice(bytes).unwrap();
    assert_eq!(report["input"], input);
    assert_eq!(report["assessment"]["choice_relation"], "different_unique_minima");
    assert_eq!(report["assessment"]["scientific_validation"], "not_established");
    assert!(output.stdout.len() <= 524_288);
}

#[test]
fn invalid_or_duplicate_fields_emit_no_report() {
    for bytes in [
        b"{}".as_slice(),
        br#"{"schema":"a","schema":"b"}"#.as_slice(),
        &vec![b' '; 524_289],
    ] {
        let output = invoke(bytes);
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
    }
}
