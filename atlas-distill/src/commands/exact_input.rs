//! Bounded exact-decimal input shared by descriptive scientific commands.
use std::io::Read;

use anyhow::{ensure, Context, Result};
use num_bigint::BigInt;
use num_rational::BigRational;

pub(super) const MAX_BYTES: usize = 524_288;

pub(super) fn decimal(text: &str) -> Result<BigRational> {
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

pub(super) fn identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 96
        && value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"_.:-".contains(&c))
}

pub(super) fn digest(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}

pub(super) fn read_bounded(reader: impl Read) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    reader
        .take((MAX_BYTES + 1) as u64)
        .read_to_end(&mut bytes)?;
    ensure!(bytes.len() <= MAX_BYTES, "input exceeds byte bound");
    Ok(bytes)
}
