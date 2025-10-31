// Simple JS file for the FastAPI Template Demo
document.addEventListener("DOMContentLoaded", function () {
  console.log("FastAPI Template Demo loaded!");

  // Add a simple animation to the cards
  const cards = document.querySelectorAll(".card");
  cards.forEach((card, index) => {
    card.style.transitionDelay = index * 0.1 + "s";
    card.style.opacity = "1";
  });

  // Get current time and update it every second
  function updateTime() {
    const timeElement = document.querySelector(".card p");
    if (timeElement && timeElement.textContent.includes("Current time:")) {
      const now = new Date();
      const timeString = now.toLocaleTimeString();
      timeElement.textContent = `Current time: ${timeString}`;
    }
  }

  // Update time immediately and then every second
  updateTime();
  setInterval(updateTime, 1000);
});
