//! Vision AI — PII / Secrets Redactor (Rust)
//! Memory-safe, high-speed, no undefined behavior.
//!
//! Usage:
//!   echo "secret text" | vision-pii-redactor
//!   echo '{"text":"..."}' | vision-pii-redactor --json

use once_cell::sync::Lazy;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::io::{self, Read, Write};

static PATTERNS: Lazy<Vec<(Regex, &'static str)>> = Lazy::new(|| {
    vec![
        (
            Regex::new(r#"(?i)\b(api[_-]?key|secret|token|password|passwd|auth)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{8,}['"]?"#)
                .expect("valid regex"),
            "$1=[REDACTED]",
        ),
        (
            Regex::new(r"(?i)\b(sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})")
                .expect("valid regex"),
            "[REDACTED_TOKEN]",
        ),
        (
            Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b").expect("valid regex"),
            "[REDACTED_EMAIL]",
        ),
        (
            Regex::new(r"(?i)\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
                .expect("valid regex"),
            "[REDACTED_PHONE]",
        ),
        (
            Regex::new(r#"(?i)(?:/home|/Users|C:\\Users)/[^\s'"]+"#).expect("valid regex"),
            "[REDACTED_PATH]",
        ),
        (
            Regex::new(r"\b(?:\d{1,3}\.){3}\d{1,3}\b").expect("valid regex"),
            "[REDACTED_IP]",
        ),
    ]
});

#[derive(Deserialize)]
struct InJson {
    text: String,
}

#[derive(Serialize)]
struct OutJson {
    text: String,
    redactions: usize,
}

fn redact(input: &str) -> (String, usize) {
    let mut out = input.to_string();
    let mut total = 0usize;
    for (re, repl) in PATTERNS.iter() {
        let count = re.find_iter(&out).count();
        if count > 0 {
            total += count;
            out = re.replace_all(&out, *repl).into_owned();
        }
    }
    (out, total)
}

fn main() {
    let json_mode = std::env::args().any(|a| a == "--json");

    let mut raw = String::new();
    if io::stdin().read_to_string(&mut raw).is_err() {
        eprintln!("vision-pii-redactor: failed to read stdin");
        std::process::exit(1);
    }

    if json_mode {
        let text = match serde_json::from_str::<InJson>(raw.trim()) {
            Ok(v) => v.text,
            Err(_) => raw,
        };
        let (text, redactions) = redact(&text);
        let out = OutJson { text, redactions };
        match serde_json::to_string(&out) {
            Ok(s) => {
                let _ = writeln!(io::stdout(), "{}", s);
            }
            Err(_) => std::process::exit(1),
        }
    } else {
        let had_newline = raw.ends_with('\n');
        let (text, _) = redact(raw.trim_end_matches('\n'));
        let _ = write!(io::stdout(), "{}", text);
        if had_newline {
            let _ = writeln!(io::stdout());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redacts_email() {
        let (out, n) = redact("mail me@example.com please");
        assert!(out.contains("[REDACTED_EMAIL]"));
        assert!(n >= 1);
    }

    #[test]
    fn redacts_api_key_style() {
        let (out, n) = redact("api_key=sk-abcdefghijklmnop");
        assert!(n >= 1);
        assert!(!out.contains("sk-abcdefghijklmnop"));
    }

    #[test]
    fn empty_input() {
        let (out, n) = redact("");
        assert_eq!(out, "");
        assert_eq!(n, 0);
    }
}
