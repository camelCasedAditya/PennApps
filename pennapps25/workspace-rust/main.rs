// Rust Sample Application
use std::time::SystemTime;
use std::collections::HashMap;

fn main() {
    println!("Hello from Rust!");
    
    // Get current time
    let now = SystemTime::now();
    println!("Current time: {:?}", now);
    
    // Simple calculation
    let a = 10;
    let b = 20;
    let sum = a + b;
    println!("Sum of {} and {} is: {}", a, b, sum);
    
    // Vector example
    let languages = vec!["Rust", "Python", "JavaScript", "Java", "Go"];
    println!("Programming languages:");
    for (i, lang) in languages.iter().enumerate() {
        println!("{}. {}", i + 1, lang);
    }
    
    // HashMap example
    let mut scores = HashMap::new();
    scores.insert("Rust", 95);
    scores.insert("Python", 90);
    scores.insert("JavaScript", 85);
    
    println!("Language scores:");
    for (lang, score) in &scores {
        println!("{}: {}", lang, score);
    }
    
    // Function call
    let result = fibonacci(10);
    println!("Fibonacci(10) = {}", result);
}

fn fibonacci(n: u32) -> u32 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}
