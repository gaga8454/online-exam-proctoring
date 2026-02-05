let cheatCount = 0;
let examSubmitted = false;

// Detect tab switch or minimize
document.addEventListener("visibilitychange", function () {
    if (document.hidden && !examSubmitted) {
        cheatCount++;
        alert(
            "Warning! Tab switching detected.\nCheating Count: " + cheatCount
        );
    }
});

// Sync cheating count just before submit and STOP tracking
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");

    form.addEventListener("submit", function () {
        examSubmitted = true; // STOP counting after this
        document.getElementById("cheatCount").value = cheatCount;
    });
});