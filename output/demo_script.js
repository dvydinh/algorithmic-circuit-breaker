/**
 * DEMO SCRIPT - Algorithmic Circuit Breaker v3.0
 * Paste into Chrome Console during presentation to simulate an addicted user.
 * 
 * ACTIONS:
 * 1. High-velocity Doomscrolling simulation.
 * 2. Injects extreme toxic DOM elements to trigger LocalNLPScanner.
 */

console.log("[Auto-Demo] Injecting toxic payloads and high-velocity scrolling to test PID Circuit Breaker...");

(function runDemo() {
    // 1. High Velocity Auto-Scroll (Doomscrolling Simulator)
    setInterval(() => {
        window.scrollBy(0, 150); // Scroll down 150px rapidly
    }, 50);

    // 2. Toxic Payload Injector (Trigger Local NLP)
    const TOXIC_PAYLOADS = [
        "This is an absolute murder of the truth.",
        "I want to kill this entire argument.",
        "So much hate in this racist post.",
        "You are so stupid and I hate this idiot content."
    ];

    setInterval(() => {
        const payload = TOXIC_PAYLOADS[Math.floor(Math.random() * TOXIC_PAYLOADS.length)];
        const hiddenP = document.createElement("p");
        hiddenP.textContent = payload;

        // Hide it visually but keep it in DOM for scanner
        hiddenP.style.opacity = "0.01";
        hiddenP.style.position = "absolute";
        hiddenP.style.pointerEvents = "none";
        hiddenP.style.zIndex = "-999";

        document.body.appendChild(hiddenP);
        console.log(`[Auto-Demo] Injected toxic payload: "${payload}"`);
    }, 2000);
})();
