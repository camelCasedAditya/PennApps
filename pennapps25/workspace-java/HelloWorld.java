// Java Sample Application
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
        System.out.println("Java version: " + System.getProperty("java.version"));
        System.out.println("OS: " + System.getProperty("os.name"));
        
        // Simple calculation
        int a = 10;
        int b = 20;
        int sum = a + b;
        System.out.println("Sum of " + a + " and " + b + " is: " + sum);
        
        // Array example
        String[] languages = {"Java", "Python", "JavaScript", "Go", "Rust"};
        System.out.println("Programming languages:");
        for (String lang : languages) {
            System.out.println("- " + lang);
        }
    }
}
