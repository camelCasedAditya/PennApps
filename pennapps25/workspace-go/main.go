// Go Sample Application
package main

import (
    "fmt"
    "time"
    "math/rand"
)

func main() {
    fmt.Println("Hello from Go!")
    fmt.Println("Current time:", time.Now().Format("2006-01-02 15:04:05"))
    
    // Simple calculation
    a, b := 10, 20
    sum := a + b
    fmt.Printf("Sum of %d and %d is: %d\n", a, b, sum)
    
    // Array example
    languages := []string{"Go", "Python", "JavaScript", "Java", "Rust"}
    fmt.Println("Programming languages:")
    for i, lang := range languages {
        fmt.Printf("%d. %s\n", i+1, lang)
    }
    
    // Random number
    rand.Seed(time.Now().UnixNano())
    randomNum := rand.Intn(100)
    fmt.Printf("Random number: %d\n", randomNum)
}
